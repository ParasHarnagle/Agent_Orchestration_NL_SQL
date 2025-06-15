import asyncio
import collections
import json
import os
import re
import time
from typing import Dict, Optional
import boto3
import pymysql
import requests
import yaml
import io
from prophet import Prophet
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse,JSONResponse
from agent_squad.utils.tool import AgentTools, AgentTool
from agent_squad.retrievers import AmazonKnowledgeBasesRetriever, AmazonKnowledgeBasesRetrieverOptions
from pydantic import BaseModel
from agent_squad.orchestrator import AgentSquad, AgentSquadConfig
from agent_squad.agents import (
    AgentStreamResponse,
     BedrockLLMAgent, 
     BedrockLLMAgentOptions,
     AgentCallbacks,
     SupervisorAgent,
    SupervisorAgentOptions
)
from botocore.exceptions import ClientError
import pandas as pd
from agent_squad.storage import InMemoryChatStorage
from agent_squad.classifiers import BedrockClassifier, BedrockClassifierOptions
import tiktoken
import boto3
import json

s3 = boto3.client('s3')

def load_json_from_s3(bucket: str, key: str) -> dict:
    response = s3.get_object(Bucket=bucket, Key=key)
    return json.loads(response['Body'].read())

def load_text_from_s3(bucket: str, key: str) -> str:
    response = s3.get_object(Bucket=bucket, Key=key)
    return response['Body'].read().decode('utf-8')

BUCKET = "test-timeoptim"


#NS_Examples = load_text_from_s3(BUCKET, "NS_Examples.txt")

yaml_text = load_text_from_s3(BUCKET, "agent_config.yaml")
config = yaml.safe_load(io.StringIO(yaml_text))

orchestrator = None
SESSION_METADATA: Dict[str, dict] = {}
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
model_id = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
#model_id = "us.anthropic.claude-sonnet-4-20250514-v1:0"
classifier = BedrockClassifier(BedrockClassifierOptions(model_id=model_id, region="us-east-1"))

class Body(BaseModel):
    input: str
    client_id: str  
    client_type: str
    session_id: str
    #chat_transaction_id: str

class LLMAgentCallbacks(AgentCallbacks):
    def __init__(self):
        self.token_count = 0
        self.tokens = []
        self.full_response = ""
        self.agent_token_usage = {}  # ✅ Add this line

    async def on_llm_new_token(self, token: str, agent_tracking_info: Optional[dict] = None) -> None:
        self.token_count += 1
        self.tokens.append(token)
        self.full_response += token
        if agent_tracking_info:
            agent_name = agent_tracking_info.get("agent_name", "unknown")
            self.agent_token_usage.setdefault(agent_name, 0)
            self.agent_token_usage[agent_name] += 1
        print(token, end='', flush=True)

    async def on_llm_response(self, response: str, agent_tracking_info: Optional[dict] = None) -> None:
        tokens = response.split()
        self.token_count += len(tokens)
        self.tokens.extend(tokens)
        self.full_response = response
        if agent_tracking_info:
            agent_name = agent_tracking_info.get("agent_name", "unknown")
            self.agent_token_usage.setdefault(agent_name, 0)
            self.agent_token_usage[agent_name] += len(tokens)
        print(f"\n\n[Non-Streaming LLM Response Received]:\n{response}")



retriever=AmazonKnowledgeBasesRetriever(AmazonKnowledgeBasesRetrieverOptions(
            knowledge_base_id="G6NAFKNJ1Q",
            retrievalConfiguration={
                "vectorSearchConfiguration": {
                    "numberOfResults": 3,
                    "overrideSearchType": "SEMANTIC",
                },
                
            }
            ))

memory_storage = InMemoryChatStorage()
orchestrator = AgentSquad(options=AgentSquadConfig(
        LOG_AGENT_CHAT=True,
        LOG_CLASSIFIER_CHAT=True,
        LOG_CLASSIFIER_RAW_OUTPUT=True,
        LOG_CLASSIFIER_OUTPUT=True,
        LOG_EXECUTION_TIMES=True,
        MAX_RETRIES=3,
        USE_DEFAULT_AGENT_IF_NONE_IDENTIFIED=True,
        NO_SELECTED_AGENT_MESSAGE="Please rephrase",
        MAX_MESSAGE_PAIRS_PER_AGENT=10
        ),
        classifier = classifier,
        storage=memory_storage
    )


fin_agent_callbacks = LLMAgentCallbacks()


fd = """
You are the FinancialProjectionAgent, specialized in financial forecasting and scenario modeling.
         ## CONTEXT:
         You fetch the raw  data from the using data retrieval tool  (e.g., a table, list of records, or JSON blob). This data may look like:
         - A list of dictionaries with `date`, `revenue`, `expense`
         - A tabular CSV-like dump
         - A JSON block with inconsistent keys
         - Format the data appropriately
         - If the user says "next month", "next quarter", or "next 90 days", convert that into a `forecast_days` integer:
            - "next month" → 30
            - "next quarter" → 90
            - "next year" → 365
            Then include this as `forecast_days` in the input to the forecasting tool.
         
         Your job is to:
         1. **Parse and extract structured time-series data**:
            - Identify the `date` field (e.g., `txn_date`, `month`, `period`)
            - Extract corresponding numeric metrics like `revenue`, `expense`, `profit`

         2. **Transform** this into the following format:
         ```json
         {
           "date": ["2024-01-01", "2024-01-02", ...],
           "revenue": [1000, 1200, ...],
           "expense": [700, 800, ...],
           "forecast_days": 30
         }
         3. Once structured, pass it to the prophet_forecast_tool for prediction.
         
         TOOL:
         Use prophet_forecast_tool only after verifying that data is valid and complete.
         ## PRIMARY RESPONSIBILITIES:
            1. **Forecasting**:
               You must construct a JSON object in this structure before calling the forecasting tool:
               ```json
               {
                 "date": ["2024-01-01", "2024-01-02", ...],
                 "revenue": [1000, 1200, ...],
                 "forecast_days": 30
               }
               Only one target field (revenue, expense, etc.) should be passed at a time 
               - After retrieving or receiving valid historical data, invoke the `prophet_forecast_tool`:
                 - Input must match the format above
                 - This tool returns forecasted values for revenue, expense, and derived profit (if both are present)
               - Use the forecast data to predict future trends, seasonality, and financial projections for the requested horizon (e.g., 30 days)
   
            2. **Scenario Planning**:
               - When the user provides assumptions (e.g., “10% increase in revenue”, “15% cost reduction”), switch to scenario modeling mode.
               - Simulate one or more forecast scenarios using those assumptions.
               - Present projected revenue, expense, and profit under each scenario in a comparative format.
   
            3. **Fallback / Clarification**:
               - If Prophet tool cannot be used (due to insufficient data, missing values, or unclear format):
                 - Fallback to simpler methods such as moving averages or linear regression.
                 - If no valid data can be used at all, return a helpful message requesting clarification or structured input.
   
            ## OUTPUT:
            - After receiving the forecast JSON, summarize the expected trends in plain language. Highlight growth/decline patterns.
            - A structured JSON object containing:
              ```json
              {
                "forecast_summary": "...",
                "forecast_data": {
                  "revenue": [...],
                  "profit": [...]
                },
                "visualization": {
                  "type": "line",
                  "xAxis": "ds",
                  "yAxis": ["revenue.yhat", "expense.yhat", "profit"]
                },
              }
   
"""

def setup_core_agent():
    # Initialize the orchestrator
    
    FIN_AGENT_PROMPT = load_text_from_s3(BUCKET, "FIN_AGENT_PROMPT.txt")
    NS_TABLE_INFO = load_json_from_s3(BUCKET, "NS_TABLE_INFO.json")
    fin_agent = BedrockLLMAgent(BedrockLLMAgentOptions(
            name="finance_translation",
            description="Translates user requests into SQL query and returns structured results",
            model_id=model_id,
            streaming=True,
            callbacks=fin_agent_callbacks,
            inference_config={
                "maxTokens": 3500,
                "temperature": 0.2  
            },
            tool_config={
                "tool": data_retrieval_tool,
                "toolMaxRecursions": 7
            },
            retriever=retriever,  # keep using few-shot example retriever
            save_chat=True,
            custom_system_prompt={
                "template": FIN_AGENT_PROMPT,
                "variables": {
                    "TABLEINFO": stringify_table_info(NS_TABLE_INFO),
                    "HISTORY":""
                }
            }
        ))
    

    
    safe_add_agent(fin_agent, orchestrator)

    forecast_tool = AgentTools(tools=[
                    AgentTool(
                    name="prophet_forecast_tool",
                    description=(
                        "Forecasts future revenue using Prophet. "
                        "Input JSON: {\"date\": [\"2024-01-01\", ...], \"revenue\": [100, ...], \"forecast_days\": 30}"
                    ),
                    func=forecast_with_prophet
                )])
    combined_tools = AgentTools(tools=[
    *data_retrieval_tool.tools,
    *forecast_tool.tools
])

    fd_agent = BedrockLLMAgent(BedrockLLMAgentOptions(
                name="finance_projection",
                description="Forecasts future trends and models hypothetical financial scenarios using historical data and assumptions.",
                model_id=model_id,
                callbacks=financialprojectionagent_callbacks,
                streaming=True,
                save_chat=True, 
                tool_config={
                    "tool": combined_tools, 
                    "toolMaxRecursions": 7
                },
                custom_system_prompt={
                    "template": fd,
                    "variables": {}
                },
                inference_config={
                    'maxTokens': 3500}
                ))

    safe_add_agent(fd_agent, orchestrator)

GLOBAL_DB_CREDS = {...}  # Your credentials
GLOBAL_MYSQL_CONNECTION = None
SCHEMA_CACHE_TTL = 3600 

def get_serper_key(app,environment,serper_config):

    secret_name = f"{app}-{environment}-{serper_config}"
    region_name = "us-east-1"

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        # For a list of exceptions thrown, see
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        raise e

    serper_key = get_secret_value_response['SecretString']
    serper_key_dict = json.loads(serper_key)

    # Return only the specific key value
    return serper_key_dict


def create_serper_search_tool():
    # Fetch environment variables
    app = os.environ.get("app")
    environment = os.environ.get("environment")
    
    # Fetch the Serper API key
    serper_key_dict = get_serper_key(app, environment, "google-serper-key")
    serper_api_key = serper_key_dict["google-serper-key"]

    # Allowed sites
    allowed_sites = [
        "statista.com",
        "mckinsey.com",
        "forbes.com",
        "hbr.org",
        "pwc.com",
        "investopedia.com",
        "aicpa-cima.com",
        "ibisworld.com",
        "corporatefinanceinstitute.com",
        "bls.gov",
        "benchmarkintl.com",
        "userpilot.com",
        "stripe.com",
        "paddle.com",
        "sec.gov"
    ]

    # Internal search function
    def search_serper(query: str) -> str:
        endpoint = "https://google.serper.dev/search"
        headers = {
            "Accept": "application/json",
            "x-api-key": serper_api_key
        }
        params = {
            "q": query,
            "num": 10
        }
        response = requests.get(endpoint, headers=headers, params=params)
        
        # Debug info
        print("Final URL:", response.request.url)
        print("Request Headers:", response.request.headers)
        print("Status Code:", response.status_code)
        print("Response Text:", response.text)
        
        response.raise_for_status()
        data = response.json()
        
        # Filter results to allowed sites
        filtered_results = [
            r["link"] for r in data.get("results", [])
            if any(site in r["link"] for site in allowed_sites)
        ]
        return "\n".join(filtered_results) or "No relevant results."

    # Return as AgentTool
    return AgentTool(
        name="internet_search",
        description="Searches the internet for insights using the Serper API",
        properties={
            "query": {
                "type": "string",
                "description": "The search query."
            }
        },
        required=["query"],
        func=search_serper
    )

ALLOWED_TASK_AGENTS = {'financialcomparisonagent','sentimentanalysisagent'}


import traceback

import json
import pandas as pd
from prophet import Prophet
import traceback

def forecast_with_prophet(input_data: str) -> str:
    print("\U0001F4CA Starting Prophet forecast...")
    try:
        data = json.loads(input_data)

        # Validate input
        if "date" not in data or "revenue" not in data:
            return json.dumps({"error": "Missing 'date' or 'revenue' fields in input."})

        # Prepare DataFrame for Prophet
        df = pd.DataFrame({
            "ds": pd.to_datetime(data["date"]),
            "y": data["revenue"]
        })

        # Dynamically determine forecast window
        forecast_days = data.get("forecast_days")
        if not forecast_days:
            history_length = len(data["date"])
            forecast_days = max(7, int(history_length / 3))  # fallback if user didn't specify

        # Fit model
        model = Prophet(
            daily_seasonality=False,
            weekly_seasonality=False,
            yearly_seasonality=True,
            n_changepoints=min(20, max(1, len(df) - 1))  # safety for short datasets
        )
        model.fit(df)

        # Forecast
        future = model.make_future_dataframe(periods=forecast_days)
        forecast = model.predict(future)

        result_df = forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail(forecast_days)

        # Convert result to JSON-safe format
        result_dicts = []
        for row in result_df.itertuples(index=False):
            result_dicts.append({
                "ds": row.ds.isoformat(),
                "yhat": round(row.yhat, 2),
                "yhat_lower": round(row.yhat_lower, 2),
                "yhat_upper": round(row.yhat_upper, 2)
            })

        output = {
            "forecast_summary": f"Predicted average for next {forecast_days} days: {round(result_df['yhat'].mean(), 2)}",
            "forecast_data": result_dicts,
            "visualization": {
                "chart_type": "Line Chart",
                "xAxis": [row["ds"] for row in result_dicts],
                "yAxis": [{
                    "name": "Forecasted Value",
                    "data": [row["yhat"] for row in result_dicts]
                }]
            }
        }

        print("\u2705 Forecast complete. Returning output.")
        print("output",json.dumps(output))
        return json.dumps(output)

    except Exception as e:
        print(f"\u274C Forecast error: {e}")
        return json.dumps({"error": f"Error in Prophet forecast: {str(e)}"})
    
def forecast_with_prophet_(input_data: str) -> str:
    """
    input_data: JSON string containing:
      {
        "date": ["2024-01-01", ...],
        "revenue": [100, 150, ...],
        "forecast_days": 30
      }
    """
    print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    try:
        data = json.loads(input_data)
        df = pd.DataFrame({
            "ds": pd.to_datetime(data["date"]),
            "y": data["revenue"]
        })

        model = Prophet()
        model.fit(df)
        print(">>>>>>>>>>>>>>>>>>>>>>AAAAAAAAAAAAAAAAAAAAAAAAA>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
        future = model.make_future_dataframe(periods=data.get("forecast_days", 30))
        forecast = model.predict(future)

        result_df = forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail(data.get("forecast_days", 30))
        output = result_df.to_dict(orient="records")
        print(">>>>>>>>>>>>>>>>>>>>>RRRRRRRRRRRRRRRRRRRRRRRRR>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
        print("Returned JSON:", json.dumps(output))
        return json.dumps(output)

    except Exception as e:
        return f"Error in Prophet forecast: {e}"


def safe_add_agent(agent, orchestrator):
    """
    Adds an agent to the orchestrator only if it doesn't already exist.
    Prevents ValueError on repeated invocations in Lambda or server mode.
    """
    try:
        if agent.id not in orchestrator.agents:
            orchestrator.add_agent(agent)
        else:
            print(f" Agent '{agent.id}' already exists. Skipping re-addition.")
    except ValueError as e:
        print(f"⚠️ Could not add agent '{agent.id}': {e}")

def stringify_table_info(table_info):
    if isinstance(table_info, list) and all(isinstance(d, dict) for d in table_info):
        return "\n".join(json.dumps(row, indent=2) for row in table_info)
    return str(table_info)

financialcomparisonagent_callbacks = LLMAgentCallbacks()
financialprojectionagent_callbacks = LLMAgentCallbacks()
llm_callbacks = LLMAgentCallbacks()
def add_task_agents_to_orchestrator(config,orchestrator):
    global GLOBAL_DB_CREDS
    serper_tool = AgentTools(tools=[create_serper_search_tool()])

    task_agents = {}
    for key, agent_data in config.get("task_agents", {}).items():


        if key in ALLOWED_TASK_AGENTS:
            if key == "financialcomparisonagent":
            
                agent = BedrockLLMAgent(BedrockLLMAgentOptions(
                name=agent_data["name"],
                description=agent_data["description"],
                model_id=model_id,
                callbacks=financialcomparisonagent_callbacks,
                streaming=True,
                #save_chat=True, 
                tool_config={
                    "tool":  serper_tool, 
                    "toolMaxRecursions": 3
                },
                custom_system_prompt={
                    "template": agent_data["prompt_template"],
                    "variables": {
                         "Company_Name":  GLOBAL_DB_CREDS["Company_Name"],
                         "Company_Domain": GLOBAL_DB_CREDS["Company_Domain"],
                    }
                },
                inference_config={
                    'maxTokens': 3500}
                ))

                #safe_add_agent(agent, orchestrator)
                task_agents[key] = agent

            else:
                agent = BedrockLLMAgent(BedrockLLMAgentOptions(
                name=agent_data["name"],
                description=agent_data["description"],
                model_id=model_id,
                callbacks=llm_callbacks,
                streaming=True,
                #save_chat=True, 
                #tool_config={
                #    "tool":  AgentTools([serper_search_tool]), 
                #    "toolMaxRecursions": 3
                #},
                custom_system_prompt={
                    "template": agent_data["prompt_template"],
                    "variables": {}
                },
                inference_config={
                    'maxTokens': 3500}
                ))

                #safe_add_agent(agent, orchestrator)
                task_agents[key] = agent


    return task_agents


def connect_to_mysql():
    """Establish and return a connection to MySQL database"""
    global GLOBAL_DB_CREDS, GLOBAL_MYSQL_CONNECTION

    # Check if connection exists and is still alive
    if GLOBAL_MYSQL_CONNECTION:
        try:
            with GLOBAL_MYSQL_CONNECTION.cursor() as cursor:
                cursor.execute("SELECT 1")  # Lightweight test query
                return GLOBAL_MYSQL_CONNECTION
        except:
            # Connection is stale or broken, close if possible
            try:
                if GLOBAL_MYSQL_CONNECTION.open:
                    GLOBAL_MYSQL_CONNECTION.close()
            except:
                pass
    
    # Create a new connection
    try:    
        print("Creating new MySQL connection...", GLOBAL_DB_CREDS)
        GLOBAL_MYSQL_CONNECTION = pymysql.connect(
            host=GLOBAL_DB_CREDS['DB_HOST'],
            user=GLOBAL_DB_CREDS['DB_USER'],
            password=GLOBAL_DB_CREDS['DB_PASSWORD'],
            db=GLOBAL_DB_CREDS['DB_NAME'],
            port=int(GLOBAL_DB_CREDS['DB_PORT']),
            autocommit=True,
            connect_timeout=5,  # Short connection timeout
            read_timeout=30,    # Query timeout
            cursorclass=pymysql.cursors.DictCursor  # Return results as dictionaries
        )
        print("[✅ New DB connection established]")
        return GLOBAL_MYSQL_CONNECTION
    except Exception as connect_err:
        print(f"[❌ Failed to connect to MySQL]: {connect_err}")
        raise

def get_full_schema():
    """Get schema information for all tables in the database"""
    try:
        with connect_to_mysql() as conn:
            with conn.cursor() as cursor:
                # Get list of tables
                cursor.execute("""
                    SELECT 
                        TABLE_NAME 
                    FROM 
                        information_schema.TABLES 
                    WHERE 
                        TABLE_SCHEMA = %s
                """, (GLOBAL_DB_CREDS['DB_NAME'],))
                
                table_results = cursor.fetchall()
                tables = [row['TABLE_NAME'] for row in table_results]
                
                # Get column information for all tables at once
                cursor.execute("""
                    SELECT 
                        TABLE_NAME, 
                        COLUMN_NAME, 
                        DATA_TYPE, 
                        COLUMN_KEY,
                        IS_NULLABLE, 
                        COLUMN_COMMENT
                    FROM 
                        information_schema.COLUMNS 
                    WHERE 
                        TABLE_SCHEMA = %s
                    ORDER BY 
                        TABLE_NAME, ORDINAL_POSITION
                """, (GLOBAL_DB_CREDS['DB_NAME'],))
                
                column_results = cursor.fetchall()
                
                # Organize schema by table
                schema = {}
                for table in tables:
                    schema[table] = []
                    
                for col in column_results:
                    table = col['TABLE_NAME']
                    if table in schema:
                        schema[table].append({
                            'name': col['COLUMN_NAME'],
                            'type': col['DATA_TYPE'],
                            'key': col['COLUMN_KEY'],
                            'nullable': col['IS_NULLABLE'],
                            'comment': col['COLUMN_COMMENT']
                        })
                
                return schema
    except Exception as e:
        print(f" ERROR fetching schema: {e}")
        return {"error": str(e)}


def run_query_tool_with_fallback(**kwargs):
    """Enhanced SQL executor that handles both queries and schema requests"""
    sql = kwargs.get("sql_query")
    fetch_schema_only = kwargs.get("fetch_schema_only", False)
    
    start_time = time.time()
    
    # For schema-only requests
    if fetch_schema_only:
        schema = get_full_schema()
        return json.dumps({
            "schema": schema,
            "execution_time_ms": int((time.time() - start_time) * 1000)
        }, indent=2)
    
    # For regular query execution
    try:
        with connect_to_mysql() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                rows = cursor.fetchall()
                execution_time = time.time() - start_time
                
                return json.dumps({
                    "success": True,
                    "rows": rows,
                    "row_count": len(rows),
                    "execution_time_ms": int(execution_time * 1000)
                }, indent=2)
    except Exception as e:
        schema_info = get_full_schema()
        return json.dumps({
            "success": False,
            "error": str(e),
            "schema": schema_info,
            "execution_time_ms": int((time.time() - start_time) * 1000),
            "suggestion": "SQL execution failed. Schema returned to regenerate query."
        }, indent=2)

def get_db_credentials(app, environment, client_type, client_id):
    #riveron-ai-dev-ns-honeycombs-hc
    print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    secret_name = f"{app}-{environment}-{client_type}-{client_id}"
    print(f"Fetching secret for: app={app}, environment={environment}, client_type={client_type}, client_id={client_id}")
    print(f"Built SecretId: {secret_name}")
    print(f"Fetching DB credentials for {secret_name}")
    region_name = "us-east-1"
    print(secret_name)

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except client.exceptions.ResourceNotFoundException:
        print(f"❌ Secret not found: {secret_name}")
        raise Exception(f"Secret not found: {secret_name}")
    except Exception as e:
        print(f"❌ Other error: {str(e)}")
        raise e

    credentials = get_secret_value_response['SecretString']
    credentials = json.loads(credentials)
    return credentials

data_retrieval_tool = AgentTools(tools=[
    AgentTool(
        name="run_query",
        description="Primary database tool: executes SQL queries or retrieves schema information in a single call",
        func=run_query_tool_with_fallback,
        properties={
            "sql_query": {
                "type": "string",
                "description": "The SQL query to be executed."
            },
            "fetch_schema_only": {
                "type": "boolean",
                "description": "If true, only returns schema without executing query. Default: false."
            }
        },
        required=["sql_query"]
    )
])

def extract_sql_query(text: str) -> str:
    
    pattern = r"```sql\s*(.*?)```"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""

sa_callbacks = LLMAgentCallbacks()
def build_supervisor(user_input, task_agents,NS_TABLE_INFO):

    SA_prompt = load_text_from_s3(BUCKET, "SA_prompt.txt")
    if hasattr(SupervisorAgent, "_configure_prompt"):
        SupervisorAgent._configure_prompt = lambda self: None

    formatted_prompt = SA_prompt.format(user_input=user_input)
    supervisor_lead_agent = BedrockLLMAgent(BedrockLLMAgentOptions(
        name="SupervisorLeadAgent",
        description="Coordinates all financial task agents and generates final user response using user input and chain output response",
        model_id=model_id,
        custom_system_prompt={
            "template": formatted_prompt,
            "variables": {"ns_table_info": NS_TABLE_INFO}
        },
        inference_config={'maxTokens': 7000},
        callbacks=sa_callbacks,
        streaming=True
    ))

    supervisor_agent = SupervisorAgent(SupervisorAgentOptions(
        lead_agent=supervisor_lead_agent,
        name="SupervisorLeadAgent",
        description="Coordinates all financial task agents and generates final user response using user input and chain output response",
        team=list(task_agents.values()),
     #   extra_tools=[serper_tool],
        storage=memory_storage,
        trace=True
    ))

    supervisor_agent.prompt_template = formatted_prompt

    return supervisor_agent



def count_prompt_tokens(prompt: str) -> int:
    """
    Count tokens in a given prompt string using the specified tokenizer encoding.

    Args:
        prompt (str): The prompt text to tokenize.
        model_encoding (str): The tokenizer encoding to use (default: "cl100k_base").

    Returns:
        int: The number of tokens in the prompt.
    """
    model_encoding: str = "cl100k_base"
    encoding = tiktoken.get_encoding(model_encoding)
    tokens = encoding.encode(prompt)
    return len(tokens)

def format_chat_history(session_id: str) -> str:
    history = SESSION_METADATA.get(session_id, {}).get("chat_history", [])
    if not history:
        return ""

    formatted = []
    for turn in history:
        user_input = turn.get("user_input", "")
        agent_response = turn.get("agent_response", "")
        formatted.append(f"User: {user_input}\nAgent: {agent_response}")

    return "\n".join(formatted)

MAX_RETRIES = 3
RETRY_DELAY = 2
HEARTBEAT_INTERVAL = 25

async def response_generator(query, user_id, client_type, session_id):
    global GLOBAL_DB_CREDS
    start_time = time.time()
    agent_output_chunks = []
    final_response = ""
    chat_history = []
    chain_response = ""

    environment = os.environ.get("environment")
    app = os.environ.get("app")
    GLOBAL_DB_CREDS = get_db_credentials(app, environment, client_type, user_id)
    FIN_AGENT_PROMPT = load_text_from_s3(BUCKET, "FIN_AGENT_PROMPT.txt")
    NS_TABLE_INFO = load_json_from_s3(BUCKET, "NS_TABLE_INFO.json")
    keep_alive_running = True
    setup_core_agent()
    task_agents = add_task_agents_to_orchestrator(config=config,orchestrator=orchestrator)
    formatted_history = format_chat_history(session_id)
    if len(formatted_history) > 5:
        formatted_history = formatted_history[-5:]
    print("=======")
    print(f"Histroy {formatted_history}")
    print("========")#

    agent = orchestrator.agents.get("finance_translation")
    print("Agent",agent)
    if agent:
        agent.set_system_prompt(
            FIN_AGENT_PROMPT,  # this should be the full prompt string with {{history}}, {{table_info}}, etc.
            {
                "TABLEINFO": stringify_table_info(NS_TABLE_INFO),
                "HISTORY": formatted_history
            }
        )

    response = await orchestrator.route_request(query, user_id, session_id, {}, True)
    
    if response.streaming:
        attempt = 0
        last_hb = time.time()
        while True:
            try:
                async for chunk in response.output:
                    now = time.time()
                    if now - last_hb > HEARTBEAT_INTERVAL:
                        yield f"event: heartbeat\ndata: {json.dumps({'time': now})}\n\n"
                        last_hb = now
                    if isinstance(chunk, AgentStreamResponse):
                        chain_response += chunk.text
                        agent_output_chunks.append(chunk.text)
                        chat_history.append({"role": "agent", "text": chunk.text})
                        #yield chunk.text
                        yield f"event: delta\ndata: {json.dumps({'output': chunk.text})}\n\n"
                break
            except Exception as e:
                attempt += 1
                yield f"event: notice\ndata: {json.dumps({'notice': 'Network glitch, retrying streaming...'})}\n\n"
                if attempt >= MAX_RETRIES:
                    yield f"event: error\ndata: {json.dumps({'error': 'Failed after retries'})}\n\n"
                    fallback = await orchestrator.route_request(query, user_id, session_id, {}, False)
                    final_text = (
                        fallback.output
                        if not getattr(fallback, "streaming", False)
                        else "".join(c.text for c in fallback.output)
                    )
                    yield f"event: delta\ndata: {json.dumps({'output': final_text})}\n\n"
                    return
                await asyncio.sleep(RETRY_DELAY)
    #chain_response = "".join(agent_output_chunks)
    #sql_query = extract_sql_query("".join(agent_output_chunks))
    existing_history = SESSION_METADATA.get(session_id, {}).get("chat_history", [])
    current_turn = {
    "user_input": query,
    "agent_response": chain_response
    }

    # Append new turn to history
    updated_history = existing_history + [current_turn]

    # Store only relevant metadata
    SESSION_METADATA[session_id] = {
        "input": query,
        "chat_history": updated_history[-5:]
    }
    print("======")
    print(f"SESSION_METADATA for {session_id}: {SESSION_METADATA.get(session_id)}")
    print("======")
    #print("chain_response:", chain_response)
    #print("SQL Query:", sql_query)
    user_input_to_task = f"""
    User Request: {query}

    --- SQL Executed ---
    {chain_response}
    Use only the provided data and insights to complete the financial task.
    """
    
    if "SupervisorLeadAgent" not in orchestrator.agents:
        supervisor_agent = build_supervisor(
            user_input=user_input_to_task,
            task_agents=task_agents,
            NS_TABLE_INFO=NS_TABLE_INFO
            )
        safe_add_agent(supervisor_agent, orchestrator)
    
    response_sa = await supervisor_agent.process_request(
        input_text=user_input_to_task,
        user_id="USER_ID",
        session_id="session_id",
        chat_history=[],
        additional_params={"ns_table_info": NS_TABLE_INFO},
    )
    response_time = round(time.time() - start_time, 2)
    if isinstance(response_sa, collections.abc.AsyncIterable):
        print("\n** STREAMING SA RESPONSE **")
        attempt = 0
        while True:
            try:
                async for chunk in response_sa:
                    now = time.time()
                    if now - last_hb > HEARTBEAT_INTERVAL:
                        yield f"event: heartbeat\ndata: {json.dumps({'time': now})}\n\n"
                        last_hb = now
                    final_response += chunk.text
                    chat_history.append({"role": "supervisor", "text": chunk.text})
                    yield f"event: delta\ndata: {json.dumps({'output': chunk.text})}\n\n"
                break
            except Exception as e:
                attempt += 1
                yield f"event: notice\ndata: {json.dumps({'notice': 'Supervisor stream interrupted, retrying...'})}\n\n"
                if attempt >= MAX_RETRIES:
                    yield f"event: error\ndata: {json.dumps({'error': 'Supervisor failed after retries'})}\n\n"
                    # non-streaming fallback
                    fb_sa = await supervisor_agent.process_request(
                        input_text=user_input_to_task,
                        user_id="USER_ID",
                        session_id=session_id,
                        chat_history=[],
                        additional_params={"ns_table_info": NS_TABLE_INFO},
                        stream=False
                    )
                    text = fb_sa.text if hasattr(fb_sa, "text") else "".join(c.text for c in fb_sa)
                    yield f"event: delta\ndata: {json.dumps({'output': text})}\n\n"
                    return
                await asyncio.sleep(RETRY_DELAY)


    #if isinstance(response_sa, collections.abc.AsyncIterable):
    #    print("\n** STREAMING RESPONSE **")
    #    async for chunk in response_sa:
    #        print(chunk.text, end='', flush=True)
    #        final_response += chunk.text
    #        chat_history.append({"role": "supervisor", "text": chunk.text})
    #        #yield chunk.text
    #        yield f"event: delta\ndata: {json.dumps({'output': chunk.text})}\n\n"
    print("--------------------")
    
    

    sql_query = extract_sql_query(user_input_to_task)
    input_token = count_prompt_tokens(query)
    total_tokens = sa_callbacks.token_count + llm_callbacks.token_count + financialprojectionagent_callbacks.token_count + financialcomparisonagent_callbacks.token_count
    completion_tokens = total_tokens - input_token
    pricing = (input_token * 0.003
                     + completion_tokens * 0.015)/1000
    response_serialized = {
        "input": query,
        #"chat_transaction_id": chat_transaction_id,
        "chat_history": chain_response,
        "output": final_response.strip(),
        "usage": {
            "tokens_used": total_tokens,  # Total tokens used
            "prompt_tokens": input_token,  # Tokens used for prompts
            "completion_tokens": completion_tokens,  # Tokens used for completions
            "successful_requests": 0,  # Total successful requests
            "total_cost_usd": pricing,
        },      
        "SQL Query": sql_query,
        "user_input_to_task": user_input_to_task,
        "response_time": response_time
    }

    print("=============")
    
    print(f"total_tokens {total_tokens}")
    print(f"input_token {input_token}")
    print("Final response:", response_serialized)

    current_turn = {
    "user_input": query,
    "agent_response": chain_response
    }

    # Get existing chat history, if any
    
    yield f"event: final_response\ndata: {json.dumps(response_serialized)}\n\n"


@app.post("/chat")
async def stream_chat(body: Body):
    return StreamingResponse(response_generator(body.input, body.client_id,body.client_type, body.session_id), media_type="text/event-stream")

@app.get("/chat_metadata/{session_id}")
async def get_metadata(session_id: str):
    if session_id not in SESSION_METADATA:
        return JSONResponse({"message": "Metadata not ready"}, status_code=404)
    return JSONResponse(SESSION_METADATA[session_id])

@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "ok"}


from functools import partial
import json
import os
import re
import time
from typing import Any, AsyncIterable, List, Optional, Union
import boto3
#import faiss
import numpy as np
import openai
import pymysql
import requests
import asyncio, uuid, yaml
# agent_squad
from agent_squad.storage import InMemoryChatStorage
from constants import NS_TABLE_INFO, NS_Examples, NS_prompt_template, SA_prompt
#from mcp_client import run_mcp_sql_tool
from agent_squad.orchestrator import AgentSquad, AgentSquadConfig
from agent_squad.classifiers import BedrockClassifier, BedrockClassifierOptions
from agent_squad.utils.tool import AgentTools, AgentTool
from agent_squad.agents import (
    BedrockLLMAgent,
    BedrockLLMAgentOptions,
    SupervisorAgent,
    SupervisorAgentOptions,
    ChainAgent,
    ChainAgentOptions,
    AgentCallbacks,
    AgentResponse
)

from agent_squad.types import  ConversationMessage
import boto3
#from retriever import AmazonKnowledgeBasesRetriever, AmazonKnowledgeBasesRetrieverOptions
from botocore.exceptions import ClientError
from agent_squad.retrievers import AmazonKnowledgeBasesRetriever, AmazonKnowledgeBasesRetrieverOptions
#   from agent_squad.agents import AgentStreamResponse
from agent_squad.agents.chain_agent import ChainAgent
from agent_squad.types import ConversationMessage
from agent_squad.utils.logger import Logger


GLOBAL_DB_CREDS = None


from decimal import Decimal

def convert_decimal(obj):
    if isinstance(obj, list):
        return [convert_decimal(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: convert_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj)
    else:
        return obj
    
## - Multi Agent Orchestrator

#model_id = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
model_id = "us.anthropic.claude-sonnet-4-20250514-v1:0"
region = "us-east-1"
ALLOWED_AGENTS = {"business_function"}
ALLOWED_TASK_AGENTS = { 'financialcomparisonagent','financialprojectionagent','sentimentanalysisagent'}

classifier = BedrockClassifier(BedrockClassifierOptions(model_id=model_id, region=region))
memory_storage = InMemoryChatStorage()

#orchestrator = AgentSquad(
#        classifier=classifier, options=AgentSquadConfig(
#                        LOG_AGENT_CHAT=True,
#                        LOG_CLASSIFIER_CHAT=True,
#                        LOG_CLASSIFIER_RAW_OUTPUT=False,
#                        LOG_CLASSIFIER_OUTPUT=True,
#                        LOG_EXECUTION_TIMES=True,
#                    ),
#        storage=memory_storage)

with open("agent_config.yaml") as f:
    config = yaml.safe_load(f)

##--embedding


def build_prompt_block( user_input, retrieved_content):
    return f"""
## {NS_prompt_template}
## Table Info:
{NS_TABLE_INFO}

## Example Matches:
{retrieved_content}

Now generate SQL for the user input:
{user_input}

"""

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

## -- embedding
## DB TOOL ------------------
GLOBAL_MYSQL_CONNECTION = None

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

def connect_to_mysql():
    global GLOBAL_DB_CREDS, GLOBAL_MYSQL_CONNECTION
    print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    if GLOBAL_MYSQL_CONNECTION and GLOBAL_MYSQL_CONNECTION.open:
        # Reuse existing connection if it's alive
        return GLOBAL_MYSQL_CONNECTION
    else:
        GLOBAL_MYSQL_CONNECTION =  pymysql.connect(
            host=GLOBAL_DB_CREDS['DB_HOST'],
            user=GLOBAL_DB_CREDS['DB_USER'],
            password=GLOBAL_DB_CREDS['DB_PASSWORD'],
            db=GLOBAL_DB_CREDS['DB_NAME'],
            port=int(GLOBAL_DB_CREDS['DB_PORT']),
            autocommit=True,
        )
        return GLOBAL_MYSQL_CONNECTION
    


def run__query_tool_with_fallback(**kwargs):
    sql = kwargs.get("sql_query")
    try:
        with connect_to_mysql() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                rows = cursor.fetchall()
                return json.dumps({"rows": rows}, indent=2)
    except Exception as e:
        schema_info = get_full_schema()
        return json.dumps({
            "error": str(e),
            "schema": schema_info,
            "suggestion": "SQL execution failed. Schema returned to regenerate query."
        }, indent=2)
# -------------------------------
# Tool 2: Get Full Schema
# -------------------------------
def get_full_schema():
    try:
        with connect_to_mysql() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SHOW TABLES;")
                result = cursor.fetchall()
                key = list(result[0].keys())[0] if result else "table"
                tables = [row[key] for row in result]
                full_schema = {}
                for tbl in tables:
                    cursor.execute(f"DESCRIBE `{tbl}`;")
                    full_schema[tbl] = cursor.fetchall()
                return full_schema
    except Exception as e:
        print(f" ERROR while fetching schema: {e}")  # ✅ LOG the error
        return {"error": str(e)}

def get_full_schema_tool(args):
    schema = get_full_schema()
    print(f"📘 Schema returned to agent:\n{schema}")
    return json.dumps({"schema": schema}, indent=2)
    


class LLMAgentCallbacks(AgentCallbacks):
    def __init__(self):
        self.token_count = 0
        self.tokens = []
        self.full_response = ""

    async def on_llm_new_token(self, token: str, agent_tracking_info: Optional[dict] = None) -> None:
        """Streaming mode — collect tokens manually."""
        self.token_count += 1
        self.tokens.append(token)
        self.full_response += token
        print(token, end='', flush=True)

    async def on_llm_response(self, response: str, agent_tracking_info: Optional[dict] = None) -> None:
        """Non-streaming mode."""
        tokens = response.split()
        self.token_count += len(tokens)
        self.tokens.extend(tokens)
        self.full_response = response
        print(f"\n\n[Non-Streaming LLM Response Received]:\n{response}")

llm_callbacks = LLMAgentCallbacks()
sa_callbacks = LLMAgentCallbacks()


data_retrieval__toolset = AgentTools(tools=[
    AgentTool(
        name="run_query",
        description="Executes SQL queries on AWS RDS. If fails, returns schema to financetranslation agent for fallback handling.",
        func=run__query_tool_with_fallback,
        properties={
            "sql_query": {
                "type": "string",
                "description": "The SQL query to be executed."
            }
        },
        required=["sql_query"]
    ),
       AgentTool(
           name="get_full_schema",
           description="Returns schema of all tables to help regenerate correct SQL queries.",
           func=get_full_schema_tool
       )
])


from functools import lru_cache

# Global variables
GLOBAL_DB_CREDS = {...}  # Your credentials
GLOBAL_MYSQL_CONNECTION = None
SCHEMA_CACHE_TTL = 3600  # Cache schema for 1 hour

def get_connection():
    global GLOBAL_DB_CREDS, GLOBAL_MYSQL_CONNECTION
    
    try:
        # Test if connection is actually working
        if GLOBAL_MYSQL_CONNECTION is not None:
            try:
                with GLOBAL_MYSQL_CONNECTION.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    return GLOBAL_MYSQL_CONNECTION
            except:
                # Connection failed, create new one
                if GLOBAL_MYSQL_CONNECTION and GLOBAL_MYSQL_CONNECTION.open:
                    GLOBAL_MYSQL_CONNECTION.close()
    except:
        pass
        
    # Create new connection
    GLOBAL_MYSQL_CONNECTION = pymysql.connect(
        host=GLOBAL_DB_CREDS['DB_HOST'],
        user=GLOBAL_DB_CREDS['DB_USER'],
        password=GLOBAL_DB_CREDS['DB_PASSWORD'],
        db=GLOBAL_DB_CREDS['DB_NAME'],
        port=int(GLOBAL_DB_CREDS['DB_PORT']),
        autocommit=True,
        connect_timeout=5,  # Shorter connect timeout
        read_timeout=30,    # Query timeout
    )
    return GLOBAL_MYSQL_CONNECTION

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
    return GLOBAL_MYSQL_CONNECTION

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

# Configure the AgentTools
from agent_squad.utils.tool import AgentTool, AgentTools

DATA_RETRIEVEL_TOOL = AgentTools(tools=[
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

retriever=AmazonKnowledgeBasesRetriever(AmazonKnowledgeBasesRetrieverOptions(
            knowledge_base_id="G6NAFKNJ1Q",
            retrievalConfiguration={
                "vectorSearchConfiguration": {
                    "numberOfResults": 3,
                    "overrideSearchType": "SEMANTIC",
                },
                
            }
            ))

def stringify_table_info(table_info):
    if isinstance(table_info, list) and all(isinstance(d, dict) for d in table_info):
        return "\n".join(json.dumps(row, indent=2) for row in table_info)
    return str(table_info)


llm_callbacks_map = {}

unified_prompt_template = """
<system>
You are the FinanceDataAgent, an expert financial assistant.
Your job is to:
- Translate user financial requests into **accurate, optimized SQL** using the schema and retrieved examples.
- Validate the generated query for syntax, schema correctness, and performance.
- Execute the query (simulate execution).
- Return results and a concise summary.
</system>

<context>
<table_info>
{{table_info}}
</table_info>

<examples>
{{#each knowledge_base_results}}
<example>
{{this.content}}
</example>
{{/each}}
</examples>
</context>

<instructions>
1. Read the user request carefully.
2. Generate one precise, valid SQL query using only the tables and columns from <table_info>.
3. Validate:
   - All columns and tables exist.
   - Joins and filters are correct.
4. Execute the query (assumed simulation).
5. Return:
   - Final SQL query in a ```sql block.
   - Results (formatted cleanly, max 1000 rows).
   - Summary of key insights.
6. If you detect a query failure, include a clear diagnosis and suggest one fix.
7. Never make assumptions about company names like Honeycomb Holdings etc or external data, refer the only the retrieved data 
</instructions>

<output_format>
SQL Query:
```sql
[FINAL EXECUTED QUERY]

Query Result:
[Formatted table results]

Summary:
[Concise analysis]
</output_format>

"""

import logging
import io



def add_core_agents_to_orchestrator(config):
    
    core_agents = {}
    
    for key, agent_data in config.get("core_agents", {}).items():   

        if key == "finance_translation":
            agent = BedrockLLMAgent(BedrockLLMAgentOptions(
            name="finance_translation",
            description="Translates financial requests, generates SQL, validates, and returns structured results",
            model_id=model_id,
            streaming=True,
            callbacks=LLMAgentCallbacks(),
            inference_config={
                "maxTokens": 2000,
                "temperature": 0.1  # low = more deterministic, accurate
            },
            tool_config={
                "tool": DATA_RETRIEVEL_TOOL,
                "toolMaxRecursions": 7
            },
            retriever=retriever,  # keep using few-shot example retriever
            save_chat=True,
            custom_system_prompt={
                "template": unified_prompt_template,
                "variables": {
                    "table_info": stringify_table_info(NS_TABLE_INFO)
                }
            }
        ))

            
            #agent = BedrockLLMAgent(BedrockLLMAgentOptions(
            #name=agent_data["name"],
            #description=agent_data["description"],
            #model_id=model_id,
            ##callbacks=cb,
            #streaming=True,
            #inference_config={
            #    "maxTokens": 1000,
            #    "temperature": 0.05,
            #    },
            #custom_system_prompt={
            #    "template": agent_data["prompt_template"],
            #    "variables": {
            #        "table_info": stringify_table_info(NS_TABLE_INFO),
            #       # "examples": few_shot_block
            #        }
            #},
            #retriever = retriever,
            #save_chat=True
            #))
            safe_add_agent(agent, orchestrator)
            core_agents[key] = agent
            

        #if key ==  "business_function":
        #    
        #    agent = BedrockLLMAgent(BedrockLLMAgentOptions(
        #    name=agent_data["name"],
        #    description=agent_data["description"],
        #    model_id=model_id,
        #    callbacks=llm_callbacks,
        #    streaming=True,
        #    inference_config={
        #        "maxTokens": 1500,
        #        "temperature": 0.1,
        #        },
        #    save_chat=True, 
        #    custom_system_prompt={
        #        "template": agent_data["prompt_template"],
        #        "variables": {}
        #    }
        #    ))
        #    safe_add_agent(agent, orchestrator)
        #    core_agents[key] = agent
        #    #llm_callbacks_map[key] = cb
    return core_agents


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

from agent_squad.utils import AgentTool
from prophet import Prophet
import pandas as pd
import json

def forecast_with_prophet(input_data: str) -> str:
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
        return json.dumps(output)

    except Exception as e:
        return f"Error in Prophet forecast: {e}"

# Create AgentTool instance

def add_task_agents_to_orchestrator(config,orchestrator):
    print("Loaded config keys:", list(config.get("task_agents", {}).keys()))
    
    # 💡 Create the tool and add it to the Supervisor
    serper_tool = AgentTools(tools=[create_serper_search_tool()])

    task_agents = {}
    for key, agent_data in config.get("task_agents", {}).items():


        if key in ALLOWED_TASK_AGENTS:
            if key == "financialcomparisonagent":
            
                agent = BedrockLLMAgent(BedrockLLMAgentOptions(
                name=agent_data["name"],
                description=agent_data["description"],
                model_id=model_id,
                callbacks=llm_callbacks,
                streaming=True,
                save_chat=True, 
                tool_config={
                    "tool":  serper_tool, 
                    "toolMaxRecursions": 3
                },
                custom_system_prompt={
                    "template": agent_data["prompt_template"],
                    "variables": {}
                },
                inference_config={
                    'maxTokens': 3500}
                ))

                safe_add_agent(agent, orchestrator)
                task_agents[key] = agent

            elif key == "financialprojectionagent":

                forecast_tool = AgentTools(tools=[
                    AgentTool(
                    name="prophet_forecast_tool",
                    description=(
                        "Forecasts future revenue using Prophet. "
                        "Input JSON: {\"date\": [\"2024-01-01\", ...], \"revenue\": [100, ...], \"forecast_days\": 30}"
                    ),
                    func=forecast_with_prophet
                )])

                agent = BedrockLLMAgent(BedrockLLMAgentOptions(
                name=agent_data["name"],
                description=agent_data["description"],
                model_id=model_id,
                callbacks=llm_callbacks,
                streaming=True,
                save_chat=True, 
                tool_config={
                    "tool": forecast_tool, 
                    "toolMaxRecursions": 3
                },
                custom_system_prompt={
                    "template": agent_data["prompt_template"],
                    "variables": {}
                },
                inference_config={
                    'maxTokens': 3500}
                ))

                safe_add_agent(agent, orchestrator)
                task_agents[key] = agent
            else:
                agent = BedrockLLMAgent(BedrockLLMAgentOptions(
                name=agent_data["name"],
                description=agent_data["description"],
                model_id=model_id,
                callbacks=llm_callbacks,
                streaming=True,
                save_chat=True, 
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

                safe_add_agent(agent, orchestrator)
                task_agents[key] = agent


    return task_agents


def add_chain_agent_to_orchestrator(config,core_agents):
    
    for key, chain_data in config.get("chain_agents", {}).items():

        print("chain_data steps =", chain_data["steps"])
        step_agents = [core_agents[step["agent_id"]] for step in chain_data["steps"]]
        chain_agent = ChainAgent(ChainAgentOptions(
            name=chain_data["name"],
            description=chain_data["description"],
            agents=step_agents,
            #streaming=True,
            callbacks=llm_callbacks,
        ))
        #orchestrator.add_agent(chain_agent)
        safe_add_agent(chain_agent, orchestrator)
        
    return chain_agent
'''
def build_supervisor(user_input, task_agents):
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
        inference_config={
                'maxTokens': 7000},
        callbacks=LLMAgentCallbacks(),
        streaming=True  
    ))

    supervisor_agent =  SupervisorAgent(SupervisorAgentOptions(
        lead_agent=supervisor_lead_agent,
        name="SupervisorLeadAgent",
        description="Coordinates all financial task agents and generates final user response using user input and chain output response",
        team=list(task_agents.values()),
        storage=memory_storage,
        trace=True
        
        
    ))

    supervisor_agent.prompt_template = formatted_prompt

    return supervisor_agent

def extract_sql_from_response(response_text: str) -> str:
    match = re.search(r"```sql(.*?)```", response_text, re.DOTALL)
    if match:
        return match.group(1).strip()

    return ""
'''

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

def build_supervisor(user_input, task_agents):
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
        callbacks=LLMAgentCallbacks(),
        streaming=True
    ))

    #  Fetch Serper key from Secrets Manager
    
    # 💡 Create the tool and add it to the Supervisor
    #serper_tool = create_serper_search_tool()

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



def extract_few_shot_pairs(retrieval_results, top_k=3):
    few_shot_pairs = []

    for result in retrieval_results:
        # Safely extract content text (SQL query)
        query_text = result.get("content", {}).get("text", "").strip()
        
        # Try to get the input/query pair
        input_text = result.get("input") or "Unknown input"
        query_raw = result.get("query") or query_text

        if input_text and query_raw:
            few_shot_pairs.append({
                "input": input_text,
                "query": query_raw.strip()
            })

        if len(few_shot_pairs) == top_k:
            break

    return few_shot_pairs


async def run_mao(params):
    
    #formatted_schema = format_table_info(schema_data)
    
    user_input = params.get("user_input", "")
    user_id = params.get("user_id", "")
    session_id = params.get("user_session_id", str(time.time()))
    
    core_agents = add_core_agents_to_orchestrator(config=config)
    
    # Add chain agent to orchestrator
    task_agents = add_task_agents_to_orchestrator(config=config)
    print("task_agents", list(task_agents.keys()))
    chain_agent = add_chain_agent_to_orchestrator(config=config,core_agents=core_agents)

    response = await chain_agent.process_request(
        input_text=user_input,
        user_id=user_id,
        session_id=session_id,
        chat_history=[],
        additional_params={"ns_table_info": NS_TABLE_INFO}
    )
    print("-------------------")
    #print("\nGenerated SQL:Response", response.content[0]["text"].strip())
    
    sql_query = extract_sql_from_response(response.content[0]["text"])
    print("\n-------------------")
    print("\nGenerated SQL:", sql_query) 
    params['sql_query'] = sql_query
    user_input_to_task = f"""
    User Request: {user_input}

    --- SQL Executed ---
    {response.content[0]["text"].strip()}

    Use only the provided data and insights to complete the financial task.
    """

    print("user_input_to_task", user_input_to_task)
    print("\n--------------")       
    if "SupervisorLeadAgent" not in orchestrator.agents:
        supervisor_agent = build_supervisor(
            user_input=user_input_to_task,
            task_agents=task_agents
            )
        safe_add_agent(supervisor_agent, orchestrator)
    print("\n------------------------------")
    print("\n------------------------------")
    response_sa = await supervisor_agent.process_request(
        input_text=user_input_to_task,
        user_id="USER_ID",
        session_id="session_id",
        chat_history=[],
        additional_params={"ns_table_info": NS_TABLE_INFO},
        
    )
   
    print(response_sa.content[0]["text"])
    #all_chats = await orchestrator.storage.fetch_all_chats(user_id, session_id)
    chat_history={
        "user": user_input,
        "chain_assistant":response.content[0]["text"].strip(),
        "supervisor_assistant":response_sa.content[0]["text"],#data_file,#doc_list,
        "modelID":model_id,
        "time":str(time.time()),
        }
    params['chat_history'] = chat_history
    params['output'] = response_sa.content[0]["text"]
    

import json
import time
import os
import collections.abc

async def run_mao_streaming(params):
    global GLOBAL_DB_CREDS
    start_time = round(time.time(), 3)
    user_input = params.get("user_input", "")
    user_id = params.get("user_id", "")
    session_id = params.get("user_session_id", str(time.time()))

    log_buffer = io.StringIO()
    handler = logging.StreamHandler(log_buffer)
    handler.setLevel(logging.INFO)

    # Get your specific logger
    logger = logging.getLogger("agent_squad.utils.logger")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.propagate = False
    
    # Get ENV
    environment = os.environ.get("environment")
    app = os.environ.get("app")
    client_type = params.get("client_type")
    client_id = params.get("client_id")

    print(f"app={app}, environment={environment}, client_type={client_type}, client_id={client_id}")

    # Fetch DB credentials
    secret_name = f"{app}-{environment}-{client_type}-{client_id}"
    print(f"Fetching secret: {secret_name}")
    GLOBAL_DB_CREDS = get_db_credentials(app, environment, client_type, client_id)

    # Initialize agents
    core_agents = add_core_agents_to_orchestrator(config=config)
    task_agents = add_task_agents_to_orchestrator(config=config)

    print("✅ Task agents loaded:", list(task_agents.keys()))

    # === CHAIN AGENT STREAMING ===
    response = await orchestrator.route_request(
        user_input=user_input,
        user_id=user_id,
        session_id=session_id,
        additional_params={"ns_table_info": NS_TABLE_INFO}
    )

    # Extract SQL
    sql_query = extract_sql_from_response(
        response.output.content[0]["text"] if hasattr(response.output, "content") else ""
    )
    params['sql_query'] = sql_query

    # Stream chain agent output
    if response.streaming and isinstance(response.output, collections.abc.AsyncIterable):
        async for chunk in response.output:
            if hasattr(chunk, "text"):
                yield json.dumps({"type": "financial_agent", "output": chunk.text})
    else:
        yield json.dumps({
            "type": "chain_chunk",
            "output": response.output.content[0]["text"] if hasattr(response.output, "content") else ""
        })

    # Prepare input for Supervisor
    user_input_to_task = f"""
    User Request: {user_input}

    --- SQL Executed ---
    {response.output.content[0]["text"].strip() if hasattr(response.output, "content") else ""}

    Use only the provided data and insights to complete the financial task.
    """

    # === SUPERVISOR AGENT STREAMING ===
    if "SupervisorLeadAgent" not in orchestrator.agents:
        supervisor_agent = build_supervisor(
            user_input=user_input_to_task,
            task_agents=task_agents
        )
        safe_add_agent(supervisor_agent, orchestrator)

    response_sa = await supervisor_agent.process_request(
        input_text=user_input_to_task,
        user_id="USER_ID",
        session_id="session_id",
        chat_history=[],
        additional_params={"ns_table_info": NS_TABLE_INFO},
    )

    output_collected = ""
    if getattr(response_sa, "streaming", False):
        if response_sa.output and isinstance(response_sa, collections.abc.AsyncIterable):
            async for chunk in response_sa.output:
                if hasattr(chunk, "text"):
                    yield json.dumps({"type": "supervisor_agent", "output": chunk.text})
                    output_collected += chunk.text
    #else:
    #    yield json.dumps({
    #        "type": "supervisor_chunk",
    #        "output": response_sa.content[0]["text"] if response_sa.content else ""
    #    })
    #    output_collected = response_sa.content[0]["text"] if response_sa.content else ""

    end_time = round(time.time(), 3)
    response_time_secs = end_time - start_time
    # Final response object
    chat_history = {
        "user": user_input,
        "chain_assistant": response.output.content[0]["text"].strip() if hasattr(response.output, "content") else "",
        "supervisor_assistant": output_collected.strip(),
        "modelID": model_id,
        "time": response_time_secs,
    }
    params['chat_history'] = chat_history
    params['output'] = output_collected.strip()
    end_time = round(time.time(), 3)
    response_time_secs = end_time - start_time
    response_serialized = {
        "input": user_input,
        "chat_history": chat_history,
        "output": output_collected.strip(),
        "usage": {},
        "SQL Query": sql_query,
        "response_time": response_time_secs
    }

    yield json.dumps({"type": "final_summary", "output": response_serialized})
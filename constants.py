SA_prompt = """

<system>
You are the SupervisorAgent.

Your mission is to coordinate specialized financial task agents and synthesize their outputs into a final, actionable response for the user.

Key principles:
- Never assume any company, user, or data context not explicitly provided.
- Only use the provided context and data.
- Never ask the user for more data; suppress any fallback prompts.
</system>

<context>
<user_input>
{user_input}
</user_input>
</context>

<instructions>
1. Analyze the original user input which is the combination of the intermediate outputs (SQL query + data) provided by the upstream agents.
2. Dynamically select the most appropriate task agent(s) from the following list:

- financialprojectionagent → Predicts/forecasts future financial trends .
- financialcomparisonagent → Compares financial metrics across time periods, entities, or categories using internet search tool.
- SentimentAnalysisAgent → Analyzes sentiment in financial content.

4. Route only the necessary context and data to the selected agent(s).
5. Aggregate the outputs into a clean, well-structured, and concise user-facing response.

Response length limit: ≤1000 words.

</instructions>


<format_guidelines>
- Structure the final response using:
  - Text summaries for explanations.
  - Tables for structured data.
  - JSON blocks for visualizations (line charts, bar charts, pie charts, heat maps, bubble charts).
- Include a “Summary of Key Insights” section.
- Provide 3 contextually relevant follow-up questions.
- Omit fields or sections if no data is available (no placeholders like “N/A” or “None”).

 ## Response Format Templates:

      1. **Text Response Format**:
      ```
      [Concise answer to the query]

      [Detailed explanation with key metrics and insights]

      [Contextual information or additional relevant details]

      ### Next probable questions you might ask:
      1. [Question 1]
      2. [Question 2]
      3. [Question 3]
      ```

      2. **Tabular Response Format**:
      ```
      [Brief introduction to the data presented]

      [Table with properly formatted columns and rows]

      [Summary of key insights from the table]

      ### Next probable questions you might ask:
      1. [Question 1]
      2. [Question 2]
      3. [Question 3]
      ```

      3. **Visualization Response Format**:
      ```
      [Brief description of what the visualization shows]

      [JSON specification for the visualization]

      [Interpretation of key trends or patterns visible in the visualization]

      ### Next probable questions you might ask:
      1. [Question 1]
      2. [Question 2]
      3. [Question 3]
      ```

Example visualization JSON format:
```json
{{
  "chart_type": "Line Chart",
  "xAxis": [{{"name": "Months", "data": ["Jan", "Feb", "Mar"]}}],
  "yAxis": [{{"name": "Revenue", "data": [10000, 15000, 17000]}}, {{"name": "Expenses", "data": [8000, 9000, 9500]}}]
}}

 For a Pie Chart:  
         Since a Pie Chart represents proportions rather than an X-Y axis, structure the output as follows:  
         Example Query:
         User_input: Can you show the revenue by location in a pie chart for 2023?  
         Output: 
         ```json
         {{"chart_type": "Pie Chart",
         "xAxis": [{{"name": "Location", "data": ["Location_1", "Location_2", "Location_3", "Location_4"]}}],
         "yAxis": [{{"name": "Revenue", "data": [Revenue_1, Revenue_2, Revenue_3, Revenue_4]}}]}}
         ```

      **2. Format for Heat Map and Bubble Chart**
        For a Heat Map:  
        Each series should have **x** and **y** values.  
        Example Query: 
        User_input: Can you show the weekly temperature trends using a heat map?  
        Output:
         ```json
         {{"chart_type": "Heat Map",
         "data_points": [{{"name": "Series 1", "data": [{{ "x": "W1", "y": 29 }},{{ "x": "W2", "y": 33 }}]}},
                           {{"name": "Series 2", "data": [{{ "x": "W1", "y": 61 }},{{ "x": "W2", "y": 18 }}]}}]}}
         ```
         
         For a Bubble Chart:
         Each data point should include **x, y,** and **z** (bubble size).  
         Example Query:  
         User_input: Can you visualize market share vs. revenue vs. growth rate using a Bubble chart?  
         Output:  
         ```json
         {{"chart_type": "Bubble Chart",
         "data_points": [{{"name": "(A)", "data": [{{ "x": 5.8, "y": 5, "z": 2 }},{{ "x": 3.4, "y": 1.5, "z": 1 }}]}},
                           {{"name": "(A1)", "data": [{{ "x": 3.9, "y": 1.4, "z": 4 }},{{ "x": 1.7, "y": 3.2, "z": 5 }}]}}]}}
         ```

      ## Financial Report Formatting Guidelines:

      1. **Income Statement**:
         - Header: Company Name, "Income Statement", Period
         - Sections: Revenue, Cost of Goods Sold, Gross Profit, Operating Expenses, Operating Income, Other Income/Expenses, Net Income
         - Include subtotals and totals for each section
         - Calculate and display important margins (Gross Margin, Operating Margin, Net Margin)

      2. **Balance Sheet**:
         - Header: Company Name, "Balance Sheet", As of Date
         - Sections: Assets (Current, Non-current), Liabilities (Current, Non-current), Equity
         - Include subtotals for each section
         - Verify that Total Assets = Total Liabilities + Total Equity

      3. **Cash Flow Statement**:
         - Header: Company Name, "Cash Flow Statement", Period
         - Sections: Operating Activities, Investing Activities, Financing Activities
         - Include Starting Cash Balance, Net Cash Flow, and Ending Cash Balance
         - Calculate and display Free Cash Flow
""" 

FIN_AGENT_PROMPT = """
<system>
You are the FinanceDataAgent, an expert financial assistant.
Your job is to:
- Translate user financial requests into **accurate, optimized SQL** using the schema and retrieved examples.
- Validate the generated query for syntax, schema correctness, and performance.
- Execute the query (simulate execution).
- Return results and a concise summary.

  IMPORTANT CONSTRAINTS:
- Never ask the user for more input.
- Do not defer the response.
- Do not say "insufficient information".
- Always attempt to answer based on the provided schema, history, and examples.
- If the exact filter (like year) is not given, make a **reasonable assumption** (e.g., default to latest year).
- If the data cannot be exactly segmented, attempt an approximate but valid SQL query from available data.
</system>

<context>
<table_info>
{{table_info}}
</table_info>

Here is the conversation history:
{{history}}

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
   - Make safe assumptions if filters are missing.
4. Execute the query (assumed simulation).
5. Return:
   - Final SQL query in a ```sql block.
   - Results (formatted cleanly, max 1000 rows).
   - Summary of key insights.
6. If you detect a query failure, include a clear diagnosis and suggest one fix.
7. Never ask the user for more input or say information is missing — always try to answer from available context.
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

SA_OLD = """
You are the SupervisorAgent responsible for coordinating financial task agents based on user input which contains the user query, its sql translation and relevant data of the executed query.
You are responsible for compiling and formatting the final responses to user input. 
Your role is to synthesize outputs from various task agents into comprehensive, well-structured responses that effectively communicate financial insights.
All task agents are instructed to only use the provided context and should NEVER ask the user for more data. If a task agent attempts to do so, suppress that fallback and format the best possible response with what's available.
Never Assume anything about the user or the company unless explicitly mentioned in the user input.

## Primary Responsibilities:

1. Analyze the **original user input** and the **intermediate output** (such as SQL query results or summarized data) produced by the Chain Agent.
2. Determine which task agent is most appropriate to handle the next step of the request.
3. Route the data and query context to the selected task agent.
4. Aggregate and finalize the response to be returned to the user in a clean and professional format.


## Available Task Agents:
- **ReportGenerationAgent** - Formats structured data into standardized reports.
- **ForecastAgent** - Predicts future trends from historical financial data.
- **SearchAgent** - Retrieves external market/industry data from the internet.
- **SentimentAnalysisAgent** - Evaluates tone and sentiment of financial content.
- **ComparativeAnalysisAgent** - Compares across time periods/entities/categories.
- **VarianceAnalysisAgent** - Explains differences from expected/budgeted results.
- **ScenarioPlanningAgent** - Models and contrasts alternative financial scenarios.
- **FinancialTerminologyAgent** - Explains finance jargon and abbreviations.

## Input Provided: A combination of user input and chain agent:
 {user_input}


## Decision Making:

Carefully analyze both the user input and chain agent output, then:

1. Select the most relevant task agent from the list.
2. Pass only the necessary information to that agent.
3. Do not include values like "N/A", "NA", or "None" in your output. Omit such fields entirely if data is not available.
4. Return the final result with clear, actionable financial insight.

## Response Format:
     ## Primary Responsibilities:

      1. **Response Composition**:
         - Integrate outputs from multiple task agents into a cohesive response.
         - Structure information logically and hierarchically for clarity.
         - Ensure consistency in terminology and metrics across the response.
         - Tailor the response style to match the complexity and formality of the query.

      2. **Format Selection and Implementation**:
         - Determine the most appropriate format for presenting information:
           - Textual responses for simple queries and explanations
           - Tabular format for structured data and comparisons
           - Graphical representation for trends and patterns
           - Mixed format for complex analyses
         - Implement the chosen format with proper styling and organization.

      3. **Visualization Guidance**:
         - Specify the most appropriate visualization type for data:
           - Line charts for time series and trends
           - Bar charts for comparisons across categories
           - Pie charts for composition and distribution
           - Heat maps for correlation and patterns
           - Scatter plots for relationship analysis
           - Bubble Chart to visualize relationships between three or more numeric variables
         - Structure data in the correct JSON format for visualization rendering.

      4. **Insight Extraction and Presentation**:
         - Identify key insights from the data and analysis.
         - Highlight significant trends, anomalies, and patterns.
         - Provide contextual interpretation of financial metrics.
         - Balance detail with clarity in presenting complex financial information.

      5. **Next Question Suggestion**:
         - Generate 3 relevant follow-up questions based on the current query and results.
         - Ensure suggested questions are contextually appropriate and insightful.
         - Prioritize questions that would lead to deeper financial understanding.

      ## Response Format Templates:

      1. **Text Response Format**:
      ```
      [Concise answer to the query]

      [Detailed explanation with key metrics and insights]

      [Contextual information or additional relevant details]

      ### Next probable questions you might ask:
      1. [Question 1]
      2. [Question 2]
      3. [Question 3]
      ```

      2. **Tabular Response Format**:
      ```
      [Brief introduction to the data presented]

      [Table with properly formatted columns and rows]

      [Summary of key insights from the table]

      ### Next probable questions you might ask:
      1. [Question 1]
      2. [Question 2]
      3. [Question 3]
      ```

      3. **Visualization Response Format**:
      ```
      [Brief description of what the visualization shows]

      [JSON specification for the visualization]

      [Interpretation of key trends or patterns visible in the visualization]

      ### Next probable questions you might ask:
      1. [Question 1]
      2. [Question 2]
      3. [Question 3]
      ```

      ## JSON Schema for Visualizations:

      Ensure that your response should include below JSON format for visualizing different charts. 
      The JSON structure should use **xAxis** and **yAxis** components for applicable chart types to ensure clarity and consistency.

      **1. Format for Line Chart, Bar Chart, and Pie Chart.** 
         Ensure the output follows this structure:  
         Example Query: 
         User_input: Can you show the month-on-month revenue vs. expense comparison for 2023 using a Line chart?  
         Output:
         ```json
         {{"chart_type": "Line Chart",
         "xAxis": [{{"name": "Months", "data": ["Month_1", "Month_2", "Month_3"]}}],
         "yAxis": [{{"name": "Revenue", "data": [Revenue_1, Revenue_2, Revenue_3]}},
         {{"name": "Expenses", "data": [Expense_1, Expense_2, Expense_3]}}]}}
         ```

         For a Pie Chart:  
         Since a Pie Chart represents proportions rather than an X-Y axis, structure the output as follows:  
         Example Query:
         User_input: Can you show the revenue by location in a pie chart for 2023?  
         Output: 
         ```json
         {{"chart_type": "Pie Chart",
         "xAxis": [{{"name": "Location", "data": ["Location_1", "Location_2", "Location_3", "Location_4"]}}],
         "yAxis": [{{"name": "Revenue", "data": [Revenue_1, Revenue_2, Revenue_3, Revenue_4]}}]}}
         ```

      **2. Format for Heat Map and Bubble Chart**
        For a Heat Map:  
        Each series should have **x** and **y** values.  
        Example Query: 
        User_input: Can you show the weekly temperature trends using a heat map?  
        Output:
         ```json
         {{"chart_type": "Heat Map",
         "data_points": [{{"name": "Series 1", "data": [{{ "x": "W1", "y": 29 }},{{ "x": "W2", "y": 33 }}]}},
                           {{"name": "Series 2", "data": [{{ "x": "W1", "y": 61 }},{{ "x": "W2", "y": 18 }}]}}]}}
         ```
         
         For a Bubble Chart:
         Each data point should include **x, y,** and **z** (bubble size).  
         Example Query:  
         User_input: Can you visualize market share vs. revenue vs. growth rate using a Bubble chart?  
         Output:  
         ```json
         {{"chart_type": "Bubble Chart",
         "data_points": [{{"name": "(A)", "data": [{{ "x": 5.8, "y": 5, "z": 2 }},{{ "x": 3.4, "y": 1.5, "z": 1 }}]}},
                           {{"name": "(A1)", "data": [{{ "x": 3.9, "y": 1.4, "z": 4 }},{{ "x": 1.7, "y": 3.2, "z": 5 }}]}}]}}
         ```

      ## Financial Report Formatting Guidelines:

      1. **Income Statement**:
         - Header: Company Name, "Income Statement", Period
         - Sections: Revenue, Cost of Goods Sold, Gross Profit, Operating Expenses, Operating Income, Other Income/Expenses, Net Income
         - Include subtotals and totals for each section
         - Calculate and display important margins (Gross Margin, Operating Margin, Net Margin)

      2. **Balance Sheet**:
         - Header: Company Name, "Balance Sheet", As of Date
         - Sections: Assets (Current, Non-current), Liabilities (Current, Non-current), Equity
         - Include subtotals for each section
         - Verify that Total Assets = Total Liabilities + Total Equity

      3. **Cash Flow Statement**:
         - Header: Company Name, "Cash Flow Statement", Period
         - Sections: Operating Activities, Investing Activities, Financing Activities
         - Include Starting Cash Balance, Net Cash Flow, and Ending Cash Balance
         - Calculate and display Free Cash Flow

      ## Process Flow:

      1. Receive compiled data and analyses from the SupervisorAgent
      2. Determine the most appropriate response format based on the query type and data
      3. Structure the response according to the chosen format
      4. Extract and highlight key insights from the data
      5. Generate relevant follow-up questions
      6. Format the final response with proper styling and organization
      7. Return the complete response to the SupervisorAgent

      You are the final communication layer between the system and the user, responsible for presenting complex financial information in a clear, insightful, and actionable manner.
 
"""

NS_Examples = [
    {
        "input": "Can you provide revenue by location for the last quarter?",
        "query": "WITH QuarterDates AS (SELECT DATE_ADD( MAKEDATE(YEAR(CURDATE()), 1),\n                    INTERVAL QUARTER(DATE_SUB(CURDATE(), INTERVAL 1 QUARTER)) * 3 - 3 MONTH)\n                    AS last_quarter_start_date, LAST_DAY(DATE_ADD(MAKEDATE(YEAR(CURDATE()), 1),\n                    INTERVAL QUARTER(DATE_SUB(CURDATE(), INTERVAL 1 QUARTER)) * 3 - 1 MONTH)) AS last_quarter_end_date\n                    ) SELECT Location, SUM(Amount) Revenue FROM Transactions T\n                    INNER JOIN QuarterDates Q ON T.Transaction_Date BETWEEN Q.last_quarter_start_date\n                    AND Q.last_quarter_end_date WHERE T.Account_Type IN ('Income','Other Income')\n                    AND T.Posting = 'Yes' GROUP BY Location;"
    },
    {
        "input": "Can you provide overall profit trends for last six months?",
        "query": "WITH Last6MonthsDates AS (SELECT DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 6 MONTH), '%Y-%m-01')\n                    AS start_date, LAST_DAY(DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 1 MONTH), '%Y-%m-01')) end_date\n                    ), Revenue AS( SELECT DATE_FORMAT(Transaction_Date, '%M %Y') MonthName, SUM(Amount) Revenue\n                    FROM Transactions T INNER JOIN Last6MonthsDates Q ON T.Transaction_Date\n                    BETWEEN Q.start_date AND Q.end_date WHERE T.Account_Type IN ('Income','Other Income')\n                    AND T.Posting = 'Yes' GROUP BY MonthName), Expenses AS(SELECT DATE_FORMAT(Transaction_Date, '%M %Y') MonthName,\n                    SUM(Amount) Expenses FROM Transactions T INNER JOIN Last6MonthsDates Q ON T.Transaction_Date\n                    BETWEEN Q.start_date AND Q.end_date WHERE T.Account_Type IN ('Expense','Cost of Goods Sold',\n                    'Other Current Liability','Credit Card','Other Expense')AND T.Posting = 'Yes' GROUP BY MonthName\n                    )SELECT R.MonthName,IFNULL(R.Revenue,0) - IFNULL(E.Expenses,0) FROM Revenue R\n                    LEFT OUTER JOIN Expenses E ON R.MonthName = E.MonthName UNION SELECT E.MonthName,\n                    IFNULL(R.Revenue,0) - IFNULL(E.Expenses,0) FROM Expenses E LEFT OUTER JOIN Revenue R\n                    ON R.MonthName = E.MonthName;"
    },
    {
        "input": "Can you provide percentage increase in revenue for this quarter versus last quarter?",
        "query": "WITH LastQuarterDates AS(SELECT DATE_ADD(MAKEDATE(YEAR(CURDATE()), 1), INTERVAL QUARTER\n                    (DATE_SUB(CURDATE(), INTERVAL 1 QUARTER)) * 3 - 3 MONTH) AS last_quarter_start_date,\n                    LAST_DAY(DATE_ADD(MAKEDATE(YEAR(CURDATE()), 1), INTERVAL QUARTER(DATE_SUB(CURDATE(),\n                    INTERVAL 1 QUARTER)) * 3 - 1 MONTH)) AS last_quarter_end_date), CurrentQuarterDates AS\n                    (SELECT CASE WHEN QUARTER(CURDATE()) = 1 THEN DATE_FORMAT(CURDATE(), '%Y-01-01')\n                    WHEN QUARTER(CURDATE()) = 2 THEN DATE_FORMAT(CURDATE(), '%Y-04-01') WHEN QUARTER(CURDATE())\n                    = 3 THEN DATE_FORMAT(CURDATE(), '%Y-07-01') WHEN QUARTER(CURDATE()) = 4 THEN DATE_FORMAT\n                    (CURDATE(), '%Y-10-01') END AS start_of_current_quarter, current_date() end_of_current_quarter\n                    ), LastQuarterRevenue AS(SELECT 'LastQuarter' QName, SUM(Amount) Revenue FROM Transactions T\n                    INNER JOIN LastQuarterDates Q ON T.Transaction_Date BETWEEN Q.last_quarter_start_date AND\n                    Q.last_quarter_end_date WHERE T.Account_Type IN ('Income','Other Income') AND T.Posting = 'Yes'\n                    ),CurrentQuarterRevenue AS(SELECT'CurrentQuarter' QName,SUM(Amount) Revenue FROM Transactions T\n                    INNER JOIN CurrentQuarterDates Q ON T.Transaction_Date BETWEEN Q.start_of_current_quarter AND\n                    Q.end_of_current_quarter WHERE T.Account_Type IN ('Income','Other Income') AND T.Posting = 'Yes'\n                    )SELECT L.QName, L.Revenue OldRevenue, C.QName, C.Revenue LatestRevenue,\n                    (C.Revenue - L.Revenue)/L.Revenue * 100 Percentage_Increase FROM LastQuarterRevenue L,\n                    CurrentQuarterRevenue C;"
    },
    {
        "input": "Can you provide top 5 best selling items for the last quarter?",
        "query": "WITH QuarterDates AS(SELECT DATE_ADD( MAKEDATE(YEAR(CURDATE()), 1), INTERVAL QUARTER\n                    (DATE_SUB(CURDATE(), INTERVAL 1 QUARTER)) * 3 - 3 MONTH) AS last_quarter_start_date,\n                    LAST_DAY(DATE_ADD(MAKEDATE(YEAR(CURDATE()), 1), INTERVAL QUARTER(DATE_SUB(CURDATE(),\n                    INTERVAL 1 QUARTER)) * 3 - 1 MONTH)) AS last_quarter_end_date) SELECT T.Item, SUM(Amount) Revenue\n                    FROM Transactions T INNER JOIN QuarterDates Q ON T.Transaction_Date BETWEEN\n                    Q.last_quarter_start_date AND Q.last_quarter_end_date WHERE T.Account_Type IN\n                    ('Income','Other Income') AND T.Posting = 'Yes' GROUP BY Item ORDER BY Revenue DESC;"
    },
    {
        "input": "What was the profit margin for the top 5 best selling products / items for the last quarter?",
        "query": "WITH QuarterDates AS(SELECT DATE_ADD(MAKEDATE(YEAR(CURDATE()), 1),INTERVAL QUARTER\n                    (DATE_SUB(CURDATE(), INTERVAL 1 QUARTER)) * 3 - 3 MONTH) AS last_quarter_start_date,\n                    LAST_DAY(DATE_ADD(MAKEDATE(YEAR(CURDATE()), 1), INTERVAL QUARTER(DATE_SUB(CURDATE(),\n                    INTERVAL 1 QUARTER)) * 3 - 1 MONTH)) AS last_quarter_end_date),Items AS (SELECT Item FROM(SELECT\n                    T.Item, SUM(Amount) Revenue FROM Transactions T INNER JOIN QuarterDates Q ON T.Transaction_Date\n                    BETWEEN Q.last_quarter_start_date AND Q.last_quarter_end_date WHERE T.Account_Type IN\n                    ('Income','Other Income') AND T.Posting = 'Yes'GROUP BY Item ORDER BY Revenue DESC)A) SELECT I.Item,\n                    Avg(T.Est_Gross_Profit_Percent_Line) Profit_Margin FROM Transactions T INNER JOIN Items I\n                    ON T.Item = I.Item INNER JOIN QuarterDates Q ON T.Transaction_Date BETWEEN Q.last_quarter_start_date\n                    AND Q.last_quarter_end_date AND T.Type = 'Customer Invoice' AND T.Posting = 'Yes'GROUP BY I.Item;"
    },
    {
        "input": "Generate the detailed Cash flow statement of the company for the year 2023?",
        "query": "WITH CashFlowOperating AS (\n                    SELECT 'Operating Activity' AS Activity, Account, SUM(Amount) AS TotalAmount\n                    FROM Transactions\n                    WHERE Account_Type IN ('Income', 'Expense', 'Cost of Goods Sold', 'Other Expense') AND YEAR(Transaction_Date) = 2023\n                    AND Posting = 'Yes'\n                    GROUP BY Account\n                    UNION ALL \n                    SELECT 'Total Operating Activity' AS Activity, '' AS Account, SUM(Amount) AS TotalAmount\n                    FROM Transactions\n                    WHERE Account_Type IN ('Income', 'Expense', 'Cost of Goods Sold', 'Other Expense') AND YEAR(Transaction_Date) = 2023\n                    AND Posting = 'Yes'\n                    ),\n                    CashFlowInvesting AS (\n                    SELECT 'Investing Activity' AS Activity, Account, SUM(Amount) AS TotalAmount\n                    FROM Transactions\n                    WHERE Account_Type IN ('Other Current Asset', 'Fixed Asset','Other Asset') AND YEAR(Transaction_Date) = 2023\n                    AND Posting = 'Yes'\n                    GROUP BY Account\n                    UNION ALL \n                    SELECT 'Total Investing Activity' AS Activity, '' AS Account, SUM(Amount) AS TotalAmount\n                    FROM Transactions\n                    WHERE Account_Type IN ('Other Current Asset', 'Fixed Asset','Other Asset') AND YEAR(Transaction_Date) = 2023\n                    AND Posting = 'Yes'\n                    ),\n                    CashFlowFinancing AS (\n                    SELECT 'Financing Activity' AS Activity, Account, SUM(Amount) AS TotalAmount\n                    FROM Transactions\n                    WHERE Account_Type IN ('Equity', 'Long Term Liability', 'Other Current Liability') AND YEAR(Transaction_Date) = 2023\n                    AND Posting = 'Yes'\n                    GROUP BY Account\n                    UNION ALL \n                    SELECT 'Total Financing Activity' AS Activity, '' AS Account, SUM(Amount) AS TotalAmount\n                    FROM Transactions\n                    WHERE Account_Type IN ('Equity', 'Long Term Liability', 'Other Current Liability') AND YEAR(Transaction_Date) = 2023\n                    AND Posting = 'Yes'\n                    ),\n                    NetCashFlow AS (\n                    SELECT 'Net Cash Flow' AS Activity, '' AS Account, \n                    (SELECT SUM(TotalAmount) FROM CashFlowOperating WHERE Activity = 'Total Operating Activity') +\n                    (SELECT SUM(TotalAmount) FROM CashFlowInvesting WHERE Activity = 'Total Investing Activity') +\n                    (SELECT SUM(TotalAmount) FROM CashFlowFinancing WHERE Activity = 'Total Financing Activity') AS TotalAmount\n                    )\n                    SELECT * FROM CashFlowOperating\n                    UNION ALL\n                    SELECT * FROM CashFlowInvesting\n                    UNION ALL\n                    SELECT * FROM CashFlowFinancing\n                    UNION ALL\n                    SELECT * FROM NetCashFlow;"
    },
    {
        "input": "Generate the detailed Income statement of the company for the year 2023?",
        "query": "WITH Revenue AS (\n                    SELECT 'Revenue' AS Category, Account, SUM(Amount) AS Total \n                    FROM Transactions  \n                    WHERE Account_Type IN ('Income', 'Other Income') \n                    AND YEAR(Transaction_Date) = 2023 AND Posting = 'Yes' \n                    GROUP BY Account\n                    UNION ALL \n                    SELECT 'Total Revenue' AS Category , '' AS Account , SUM(Amount) AS Total \n                    FROM Transactions \n                    WHERE Account_Type IN ('Income', 'Other Income') \n                    AND YEAR(Transaction_Date) = 2023 AND Posting = 'Yes' \n                    ),\n                    CostOfGoodsSold AS (\n                    SELECT 'Cost of Goods Sold' AS Category, Account, SUM(Amount) AS Total \n                    FROM Transactions \n                    WHERE Account_Type = 'Cost of Goods Sold' \n                    AND YEAR(Transaction_Date) = 2023 AND Posting = 'Yes'\n                    GROUP BY Account\n                    UNION ALL \n                    SELECT 'Total Cost of Goods Sold' AS Category , '' AS Account , SUM(Amount) AS Total \n                    FROM Transactions \n                    WHERE Account_Type = 'Cost of Goods Sold'\n                    AND YEAR(Transaction_Date) = 2023 AND Posting = 'Yes' \n                    ),\n                    GrossProfit AS (\n                    SELECT 'Gross Profit' AS Category, '' AS Account , \n                    ((SELECT Total FROM Revenue WHERE Category = 'Total Revenue') - \n                    (SELECT Total FROM CostOfGoodsSold WHERE Category = 'Total Cost of Goods Sold')) AS Total\n                    ),\n                    Expenses AS (\n                    SELECT 'Expenses' AS Category, Account, SUM(Amount) AS Total \n                    FROM Transactions \n                    WHERE Account_Type IN ('Expense', 'Other Expense') \n                    AND YEAR(Transaction_Date) = 2023 AND Posting = 'Yes' \n                    GROUP BY Account\n                    UNION ALL \n                    SELECT 'Total Expenses' AS Category , '' AS Account , SUM(Amount) AS Total \n                    FROM Transactions \n                    WHERE Account_Type IN ('Expense', 'Other Expense') \n                    AND YEAR(Transaction_Date) = 2023 AND Posting = 'Yes' \n                    ) ,\n                    NetIncome AS (\n                    SELECT 'Net Income' AS Category , '' AS Account , \n                    ((SELECT Total FROM GrossProfit WHERE Category = 'Gross Profit') - \n                    (SELECT Total FROM Expenses WHERE Category = 'Total Expenses')) AS Total\n                    )\n                    SELECT * FROM Revenue\n                    UNION ALL\n                    SELECT * FROM CostOfGoodsSold\n                    UNION ALL \n                    SELECT * FROM GrossProfit\n                    UNION ALL\n                    SELECT * FROM Expenses\n                    UNION ALL\n                    SELECT * FROM NetIncome;"
    },
    {
        "input": "Generate the detailed Balance Sheet Report of the company for the year 2023?",
        "query": "WITH Assets AS (\n                    SELECT A.Account, SUM(A.Balance) AS Total \n                    FROM ChartofAccounts A\n                    INNER JOIN Transactions T\n                    ON A.Internal_ID = T.Account_ID\n                    WHERE A.Type IN ('Accounts Receivable', 'Bank', 'Credit Card', 'Fixed Asset', 'Other Asset', 'Other Current Asset') \n                    AND YEAR(T.Transaction_Date) = 2023 AND T.Posting = 'Yes'\n                    GROUP BY A.Account),\n                    Liabilities AS (\n                    SELECT A.Account, SUM(A.Balance) AS Total \n                    FROM ChartofAccounts A\n                    INNER JOIN Transactions T\n                    ON A.Internal_ID = T.Account_ID\n                    WHERE A.Type IN ('Accounts Payable', 'Long term Liability', 'Other Current Liability') \n                    AND YEAR(T.Transaction_Date) = 2023 AND T.Posting = 'Yes'\n                    GROUP BY A.Account),\n                    Equity AS (\n                    SELECT A.Account, SUM(A.Balance) AS Total \n                    FROM ChartofAccounts A\n                    INNER JOIN Transactions T\n                    ON A.Internal_ID = T.Account_ID\n                    WHERE A.Type IN ('Equity')\n                    AND YEAR(T.Transaction_Date) = 2023 AND T.Posting = 'Yes'\n                    GROUP BY A.Account)\n                    SELECT 'Assets' AS Category, Account, Assets.Total FROM Assets \n                    UNION ALL \n                    SELECT 'Total Assets' AS Category, '' AS Account , SUM(A.Balance) AS Total \n                    FROM ChartofAccounts A\n                    INNER JOIN Transactions T\n                    ON A.Internal_ID = T.Account_ID\n                    WHERE A.Type IN ('Accounts Receivable', 'Bank', 'Credit Card', 'Fixed Asset', 'Other Asset', 'Other Current Asset')\n                    AND YEAR(T.Transaction_Date) = 2023  AND T.Posting = 'Yes'\n                    UNION ALL \n                    SELECT 'Liabilities' AS Category, Account, Liabilities.Total FROM Liabilities\n                    UNION ALL\n                    SELECT 'Total Liabilities' AS Category, 'Account' AS Account , SUM(A.Balance) AS Total \n                    FROM ChartofAccounts A\n                    INNER JOIN Transactions T\n                    ON A.Internal_ID = T.Account_ID\n                    WHERE A.Type IN ('Accounts Payable', 'Long term Liability', 'Other Current Liability')\n                    AND YEAR(T.Transaction_Date) = 2023 AND T.Posting = 'Yes'\n                    UNION ALL\n                    SELECT 'Equity' AS Category, Account, Equity.Total FROM Equity\n                    UNION ALL\n                    SELECT 'Total Equity' AS Category, 'Account' AS Account , SUM(A.Balance) AS Total \n                    FROM ChartofAccounts A\n                    INNER JOIN Transactions T\n                    ON A.Internal_ID = T.Account_ID\n                    WHERE A.Type IN ('Equity')\n                    AND YEAR(T.Transaction_Date) = 2023 AND T.Posting = 'Yes'\n                    UNION ALL \n                    SELECT 'Total Liability + Total Equity' AS Category, 'Account' AS Account , SUM(A.Balance) AS Total \n                    FROM ChartofAccounts A\n                    INNER JOIN Transactions T\n                    ON A.Internal_ID = T.Account_ID\n                    WHERE A.Type IN ('Accounts Payable', 'Long term Liability', 'Other Current Liability','Equity')\n                    AND YEAR(Transaction_Date) = 2023 AND T.Posting = 'Yes';"
    },
    {
        "input": "Calculate the Total Assets of the company for the year 2023?",
        "query": "WITH Assets AS (\n                    SELECT A.Account, SUM(A.Balance) AS Total \n                    FROM ChartofAccounts A\n                    INNER JOIN Transactions T\n                    ON A.Internal_ID = T.Account_ID\n                    WHERE A.Type IN ('Accounts Receivable', 'Bank', 'Credit Card', 'Fixed Asset', 'Other Asset', 'Other Current Asset') \n                    AND YEAR(T.Transaction_Date) = 2023 AND T.Posting = 'Yes'\n                    GROUP BY A.Account), \n                    Total_Assets AS (\n                    SELECT 'Total Assets' AS Category, '' AS Account , SUM(A.Balance) AS Total \n                    FROM ChartofAccounts A\n                    INNER JOIN Transactions T\n                    ON A.Internal_ID = T.Account_ID\n                    WHERE A.Type IN ('Accounts Receivable', 'Bank', 'Credit Card', 'Fixed Asset', 'Other Asset', 'Other Current Asset')\n                    AND YEAR(T.Transaction_Date) = 2023 AND T.Posting = 'Yes')\n                    SELECT 'Assets' AS Category, Account, Assets.Total FROM Assets \n                    UNION ALL\n                    SELECT * FROM Total_Assets;"
    },
    {
        "input": "Calculate the Total Current Assets of the company for the year 2023?",
        "query": "WITH Current_Assets AS (\n                    SELECT A.Account, SUM(A.Balance) AS Total \n                    FROM ChartofAccounts A\n                    INNER JOIN Transactions T\n                    ON A.Internal_ID = T.Account_ID\n                    WHERE A.Type IN ('Accounts Receivable', 'Bank', 'Credit Card','Other Current Asset') \n                    AND YEAR(T.Transaction_Date) = 2023 AND T.Posting = 'Yes'\n                    GROUP BY A.Account),\n                    Total_Current_Assets AS (\n                    SELECT 'Total_Current_Assets' AS Category, '' AS Account , SUM(A.Balance) AS Total \n                    FROM ChartofAccounts A\n                    INNER JOIN Transactions T\n                    ON A.Internal_ID = T.Account_ID\n                    WHERE A.Type IN ('Accounts Receivable', 'Bank', 'Credit Card','Other Current Asset')\n                    AND YEAR(T.Transaction_Date) = 2023 AND T.Posting = 'Yes')\n                    SELECT 'Current_Assets' AS Category, Current_Assets.Account, Current_Assets.Total FROM Current_Assets\n                    UNION ALL\n                    SELECT * FROM Total_Current_Assets;"
    },
    {
        "input": "Calculate the Total Non-Current Assets of the company for the year 2023?",
        "query": "WITH Non_current_Asset AS (\n                    SELECT A.Account, SUM(A.Balance) AS Total \n                    FROM ChartofAccounts A\n                    INNER JOIN Transactions T\n                    ON A.Internal_ID = T.Account_ID\n                    WHERE A.Type IN ('Fixed Asset', 'Other Asset') \n                    AND YEAR(T.Transaction_Date) = 2023 AND T.Posting = 'Yes'\n                    GROUP BY A.Account),\n                    Total_Non_current_Assets AS (\n                    SELECT 'Total_Non_current_Assets' AS Category, '' AS Account , SUM(A.Balance) AS Total \n                    FROM ChartofAccounts A\n                    INNER JOIN Transactions T\n                    ON A.Internal_ID = T.Account_ID\n                    WHERE A.Type IN ('Fixed Asset', 'Other Asset')\n                    AND YEAR(T.Transaction_Date) = 2023 AND T.Posting = 'Yes')\n                    SELECT 'Non_current_Assets' AS Category, Non_current_Asset.Account, Non_current_Asset.Total FROM Non_current_Asset\n                    UNION ALL\n                    SELECT * FROM Total_Non_current_Assets;"
    },
    {
        "input": "Calculate the Total Liabilities of the company for the year 2023?",
        "query": "WITH Liabilities AS (\n                    SELECT A.Account, SUM(A.Balance) AS Total \n                    FROM ChartofAccounts A\n                    INNER JOIN Transactions T\n                    ON A.Internal_ID = T.Account_ID\n                    WHERE A.Type IN ('Accounts Payable', 'Long term Liability', 'Other Current Liability') \n                    AND YEAR(T.Transaction_Date) = 2023 AND T.Posting = 'Yes'\n                    GROUP BY A.Account), \n                    Total_Liabilities AS (\n                    SELECT 'Total_Liabilities' AS Category, '' AS Account , SUM(A.Balance) AS Total \n                    FROM ChartofAccounts A\n                    INNER JOIN Transactions T\n                    ON A.Internal_ID = T.Account_ID\n                    WHERE A.Type IN ('Accounts Payable', 'Long term Liability', 'Other Current Liability')\n                    AND YEAR(T.Transaction_Date) = 2023 AND T.Posting = 'Yes')\n                    SELECT 'Liabilities' AS Category, Liabilities.Account, Liabilities.Total FROM Liabilities\n                    UNION ALL\n                    SELECT * FROM Total_Liabilities;"
    },
    {
        "input": "Calculate the Total Current-Liabilities of the company for the year 2023?",
        "query": "WITH Current_Liability AS (\n                    SELECT A.Account, SUM(A.Balance) AS Total \n                    FROM ChartofAccounts A\n                    INNER JOIN Transactions T\n                    ON A.Internal_ID = T.Account_ID\n                    WHERE A.Type IN ('Accounts Payable', 'Other Current Liability') \n                    AND YEAR(T.Transaction_Date) = 2023 AND T.Posting = 'Yes'\n                    GROUP BY A.Account), \n                    Total_Current_Liability AS (\n                    SELECT 'Total_Current_Liability' AS Category, '' AS Account , SUM(A.Balance) AS Total \n                    FROM ChartofAccounts A\n                    INNER JOIN Transactions T\n                    ON A.Internal_ID = T.Account_ID\n                    WHERE A.Type IN ('Accounts Payable', 'Other Current Liability')\n                    AND YEAR(T.Transaction_Date) = 2023 AND T.Posting = 'Yes')\n                    SELECT 'Current_Liability' AS Category, Current_Liability.Account, Current_Liability.Total FROM Current_Liability\n                    UNION ALL\n                    SELECT * FROM Total_Current_Liability;"
    },
    {
        "input": "Calculate the Non Current Liability of the company for the year 2023?",
        "query": "WITH Non_Current_Liability AS (SELECT 'Non Current Liability' AS Category, A.Account as Account, \n                    COALESCE(SUM(A.Balance), 0) AS Total\n                    FROM ChartofAccounts A\n                    LEFT JOIN Transactions T\n                    ON A.Internal_ID = T.Account_ID \n                    AND YEAR(T.Transaction_Date) = 2023 AND T.Posting = 'Yes'\n                    WHERE A.Type IN ('Long term Liability') \n                    GROUP BY A.Account),\n                    Total_Non_Current_Liability AS(\n                    SELECT 'Total_Non Current Liability' AS Category, '' as Account, COALESCE(SUM(A.Balance), 0) AS Total\n                    FROM ChartofAccounts A\n                    LEFT JOIN Transactions T\n                    ON A.Internal_ID = T.Account_ID \n                    AND YEAR(T.Transaction_Date) = 2023  AND T.Posting = 'Yes'\n                    WHERE A.Type IN ('Long term Liability'))\n                    Select * from Non_Current_Liability\n                    UNION ALL\n                    Select * from Total_Non_Current_Liability;"
    },
    {
        "input": "Calculate the Total Equities of the company for the year 2023?",
        "query": "WITH Equity AS (\n                    SELECT A.Account, SUM(A.Balance) AS Total \n                    FROM ChartofAccounts A\n                    INNER JOIN Transactions T\n                    ON A.Internal_ID = T.Account_ID\n                    WHERE A.Type IN ('Equity') \n                    AND YEAR(T.Transaction_Date) = 2023 AND T.Posting = 'Yes'\n                    GROUP BY A.Account), \n                    Total_Equity AS (\n                    SELECT 'Total_Equity' AS Category, '' AS Account , SUM(A.Balance) AS Total \n                    FROM ChartofAccounts A\n                    INNER JOIN Transactions T\n                    ON A.Internal_ID = T.Account_ID\n                    WHERE A.Type IN ('Equity')\n                    AND YEAR(T.Transaction_Date) = 2023 AND T.Posting = 'Yes')\n                    SELECT 'Equity' AS Category, Equity.Account, Equity.Total FROM Equity\n                    UNION ALL\n                    SELECT * FROM Total_Equity;"
    },
    {
        "input": "Generate the Trial Balance report of  *ABC Organization* : **XYZ Mfg**. for the Financial Year 2023.",
        "query": "WITH A AS (SELECT A.ACCOUNTSEARCHDISPLAYNAME AS ACCOUNTSEARCHDISPLAYNAME, P.STARTDATE, P.ENDDATE,\n                    P.Name, coalesce(ROUND(coalesce(T.Amount * -1), 2), 0) AS AMT FROM Transactions T\n                    INNER JOIN ChartofAccounts A ON A.Number = T.Number\n                    LEFT JOIN Class CL ON CL.internal_id = T.Class\n                    LEFT JOIN Departments D ON D.Internal_ID = T.Department\n                    LEFT JOIN Customers C ON C.Name = T.Company_Name\n                    INNER JOIN Subsidiaries S ON S.Name = T.Subsidiary\n                    INNER JOIN accountingperiod P ON P.Name = T.Period\n                    LEFT JOIN location L ON L.name = T.Location\n                    WHERE T.Posting = 'Yes'\n                    AND S.Name = 'Honeycomb Holdings Inc. : Honeycomb Mfg.'),\n                    B AS\n                    (SELECT DISTINCT ACCOUNTSEARCHDISPLAYNAME FROM A),\n                    C AS (\n                    SELECT DISTINCT STARTDATE, ENDDATE, Name FROM accountingperiod\n                    where Name like 'Q%' OR Name like 'FY%'),\n                    D AS (\n                    SELECT ACCOUNTSEARCHDISPLAYNAME, STARTDATE,\n                    ENDDATE, Name FROM B CROSS JOIN C),\n                    main_table as (\n                    SELECT D.ACCOUNTSEARCHDISPLAYNAME, D.STARTDATE,\n                    D.ENDDATE, D.Name, coalesce(A.AMT, 0) AS AMT FROM D LEFT JOIN A ON\n                    A.ACCOUNTSEARCHDISPLAYNAME = D.ACCOUNTSEARCHDISPLAYNAME AND A.STARTDATE = D.STARTDATE),\n                    E as (SELECT\n                    ACCOUNTSEARCHDISPLAYNAME, STARTDATE, ENDDATE, Name, SUM(SUM(AMT)) OVER\n                    (PARTITION BY ACCOUNTSEARCHDISPLAYNAME ORDER BY STARTDATE ROWS BETWEEN UNBOUNDED\n                    PRECEDING AND 1 PRECEDING) AS OPENINGAMOUNT, SUM(AMT) AS AMOUNT, SUM(SUM(AMT)) OVER\n                    (PARTITION BY ACCOUNTSEARCHDISPLAYNAME ORDER BY STARTDATE) AS CLOSINGAMOUNT FROM main_table\n                    GROUP BY ACCOUNTSEARCHDISPLAYNAME, STARTDATE, ENDDATE, Name)\n                    SELECT ACCOUNTSEARCHDISPLAYNAME,\n                    Name, OPENINGAMOUNT, CASE WHEN AMOUNT > 0 THEN AMOUNT END AS DEBIT,\n                    CASE WHEN AMOUNT < 0 THEN AMOUNT * -1 END AS CREDIT, CLOSINGAMOUNT FROM E\n                    WHERE (OPENINGAMOUNT != 0\n                    OR AMOUNT != 0 OR CLOSINGAMOUNT != 0)\n                    AND Name = 'FY 2023'\n\t\t\t        ORDER BY ACCOUNTSEARCHDISPLAYNAME;"
    }]


    # Adding the Table_Info/Database Schema as the context to the model.(NS_Agent)

NS_TABLE_INFO = [
  {
  "Table Name": "accounting_periods",
  "Table Description": "Core NetSuite configuration table that defines the fiscal and reporting periods for the organization's financial calendar. This table establishes the fundamental time boundaries for transaction posting, financial statement preparation, revenue recognition, expense accruals, and period-end close processes. It supports hierarchical period structures (year, quarter, month) and enforces NetSuite's period-based accounting controls, ensuring compliance with GAAP/IFRS requirements for consistent financial reporting across the enterprise.",
  "Columns": [
    {
      "Column Name": "internal_id",
      "Column Description": "NetSuite's system-generated unique identifier for each accounting period that serves as the primary key and maintains referential integrity across all financial transactions",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "accounting_period_name",
      "Column Description": "The standardized designation for the fiscal period (e.g., 'Jan 2023', 'Q1 FY2023') used in NetSuite financial reports, consolidated statements, and audit documentation",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "start_date",
      "Column Description": "The first calendar day of the fiscal period when transactions begin posting to this period in the general ledger, establishing the opening balance date",
      "Type": "DATE"
    },
    {
      "Column Name": "end_date",
      "Column Description": "The final calendar day of the fiscal period marking the cutoff for transaction posting before period close, determining the closing balance date",
      "Type": "DATE"
    },
    {
      "Column Name": "is_year",
      "Column Description": "Boolean indicator denoting whether the period represents a fiscal year for annual financial statement preparation and statutory reporting requirements",
      "Type": "VARCHAR(5)"
    },
    {
      "Column Name": "date_closed_on",
      "Column Description": "The timestamp when the NetSuite period lock was executed, preventing further transaction posting and finalizing the period's financial results for reporting",
      "Type": "DATE"
    },
    {
      "Column Name": "fiscal_calendar",
      "Column Description": "Reference to the specific NetSuite fiscal calendar definition that governs this period, supporting organizations with multiple accounting calendars or subsidiaries",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "is_quarter",
      "Column Description": "Boolean indicator denoting a quarterly fiscal period for SEC reporting requirements, quarterly close processes, and interim financial statement preparation",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "parent_year",
      "Column Description": "Reference to the fiscal year period that contains this sub-period, establishing the hierarchical relationship for consolidation and year-to-date reporting",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "last_modified_date",
      "Column Description": "System timestamp of the most recent update to the period configuration, supporting audit trails, SOX compliance documentation, and change management controls",
      "Type": "TIMESTAMP"
    }
  ],
  "Primary Key": "internal_id"
  },
  {
  "Table Name": "chart_of_accounts",
  "Table Description": "NetSuite's foundational financial master record that defines the complete hierarchical structure of accounts in the organization's general ledger. This table serves as the backbone of the financial reporting system, categorizing all transactions into standardized accounts that map directly to financial statements (balance sheet, income statement, cash flow statement). It enforces account standardization across subsidiaries, supports multi-book accounting, enables dimensional reporting, and ensures compliance with accounting standards (GAAP/IFRS) while facilitating statutory reporting, financial consolidation, and audit trails.",
  "Columns": [
    {
      "Column Name": "internal_id",
      "Column Description": "NetSuite's system-generated unique identifier for each general ledger account that serves as the primary key and maintains referential integrity across all financial transactions",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "is_summary",
      "Column Description": "Boolean indicator designating whether the account functions as a parent account that aggregates balances from child accounts for hierarchical financial reporting without directly receiving transaction postings",
      "Type": "VARCHAR(5)"
    },
    {
      "Column Name": "account_number",
      "Column Description": "Standardized alphanumeric code that uniquely identifies each financial account within NetSuite's hierarchical structure, typically following a segmented numbering convention (Assets: 1000-1999, Liabilities: 2000-2999, Equity: 3000-3999, Revenue: 4000-4999, Expenses: 5000-5999)",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "account_name",
      "Column Description": "The standardized financial account title that appears in trial balances, journal entries, financial statements, and audit reports (e.g., Cash, Accounts Receivable, Revenue, COGS)",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "account_type",
      "Column Description": "NetSuite's classification category that determines the account's behavior in financial statements, tax reporting, and period-end close processes (e.g., Bank, Accounts Receivable, Fixed Asset, Equity, Revenue, COGS, Expense)",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "description",
      "Column Description": "Detailed explanation of the account's purpose, accounting policies, allowed transactions, and relationship to financial statement line items for documentation and compliance purposes",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "balance",
      "Column Description": "Current monetary value representing the net of all debits and credits posted to this account through the current accounting period, directly impacting financial statement calculations",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "is_inactive",
      "Column Description": "Boolean flag indicating whether the account has been deactivated to prevent further transaction posting while preserving historical data for financial reporting and audit requirements",
      "Type": "VARCHAR(5)"
    },
    {
      "Column Name": "last_modified_date",
      "Column Description": "System timestamp of the most recent update to the account configuration, supporting SOX compliance documentation, audit trails, and change management controls",
      "Type": "TIMESTAMP"
    }
  ],
  "Primary Key": "internal_id"
  },
  {
  "Table Name": "classes",
  "Table Description": "A strategic NetSuite dimensional reporting segment that provides a critical financial classification layer beyond the standard chart of accounts. This table defines business units, departments, programs, or initiatives for enhanced revenue and expense tracking across the organization. Classes function as a key financial segmentation mechanism, enabling targeted profitability analysis, departmental accountability, budgetary control, and segment reporting compliance with ASC 280 or IFRS 8 requirements. Within NetSuite, classes can be assigned to transactions for multidimensional reporting and serve as a cornerstone for management accounting and financial performance evaluation.",
  "Columns": [
    {
      "Column Name": "internal_id",
      "Column Description": "NetSuite's system-generated unique identifier for each class segment that serves as the primary key and maintains referential integrity across all financial transactions tagged with this classification",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "class_name",
      "Column Description": "The standardized designation of the financial reporting segment used in segmented P&L statements, contribution margin analysis, departmental budgeting, and cost allocation workflows within NetSuite",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "is_inactive",
      "Column Description": "Boolean flag indicating whether the class has been deactivated to prevent further transaction tagging while preserving historical data for financial reporting and audit requirements",
      "Type": "VARCHAR(5)"
    },
    {
      "Column Name": "last_modified_date",
      "Column Description": "System timestamp of the most recent update to the class configuration, supporting SOX compliance documentation, audit trails, and change management controls within NetSuite",
      "Type": "TIMESTAMP"
    }
  ],
  "Primary Key": "internal_id"
  },
  {
  "Table Name": "currencies",
  "Table Description": "A critical NetSuite configuration table that defines all global currencies supported for the organization's financial operations. This table serves as the foundation for multi-currency accounting, enabling foreign currency transactions, consolidated financial reporting across international subsidiaries, and compliance with ASC 830 (Foreign Currency Matters) and IAS 21 requirements. It provides the reference data necessary for currency conversion, foreign exchange gain/loss calculations, revaluation processes, and global financial consolidation within the NetSuite ERP environment.",
  "Columns": [
    {
      "Column Name": "internal_id",
      "Column Description": "NetSuite's system-generated unique identifier for each currency record that serves as the primary key and maintains referential integrity across all currency-related configurations and transactions",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "currency_name",
      "Column Description": "The official ISO-compliant name of the currency as recognized in global financial markets and used in formal financial statements, regulatory filings, and audit documentation",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "currency_symbol",
      "Column Description": "The standardized typographic character representing the currency in NetSuite financial reports, transaction displays, and user interfaces (e.g., $, €, £, ¥, ₹)",
      "Type": "VARCHAR(5)"
    },
    {
      "Column Name": "currency_exchange_rate",
      "Column Description": "The current foreign exchange (FX) rate relative to the base functional currency, used for transaction conversion, foreign currency translation adjustments, and consolidated financial reporting",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "is_inactive",
      "Column Description": "Boolean flag indicating whether the currency has been deactivated to prevent further transaction processing while preserving historical data for financial reporting and audit requirements",
      "Type": "VARCHAR(5)"
    },
    {
      "Column Name": "last_modified_date",
      "Column Description": "System timestamp of the most recent update to the currency configuration, supporting SOX compliance documentation, audit trails, and change management controls within NetSuite",
      "Type": "TIMESTAMP"
    }
  ],
  "Primary Key": "internal_id"
  },
  {
  "Table Name": "customers",
  "Table Description": "NetSuite's comprehensive customer master record that serves as the central repository for financial, commercial, and operational customer data. This critical table supports end-to-end revenue management processes, including accounts receivable tracking, credit risk assessment, revenue recognition (ASC 606/IFRS 15), customer profitability analysis, and multi-subsidiary financial reporting. It provides a 360-degree view of customer relationships, enabling precise financial modeling, sales performance evaluation, and strategic customer lifecycle management within the enterprise resource planning ecosystem.",
  "Columns": [
    {
      "Column Name": "internal_id",
      "Column Description": "NetSuite's system-generated unique identifier for each customer record that serves as the primary key and maintains referential integrity across all financial transactions, invoices, payments, and revenue recognition schedules",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "customer_id",
      "Column Description": "Unique alphanumeric identifier assigned by NetSuite for customer tracking, enabling precise customer segmentation, financial reporting, and compliance documentation",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "customer_name",
      "Column Description": "Legally recognized business entity or individual name used in invoicing, financial statements, tax reporting, and accounts receivable documentation",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "phone",
      "Column Description": "Primary contact number used for accounts receivable communications, credit verification, and financial transaction authorization processes",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "billing_address",
      "Column Description": "Primary invoice delivery and tax jurisdiction address used for statutory financial reporting, sales tax calculation, and compliance documentation",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "billing_city",
      "Column Description": "Municipality component of the billing address critical for geographic revenue segmentation, tax compliance, and financial reporting analysis",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "billing_state_province",
      "Column Description": "State or provincial tax jurisdiction used for precise sales tax calculations, regional financial reporting, and regulatory compliance tracking",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "sales_rep",
      "Column Description": "Primary sales representative assigned to the customer account for commission calculations, sales performance analysis, and revenue attribution modeling",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "date_created",
      "Column Description": "Timestamp of customer record creation in NetSuite, used for customer lifecycle analysis, cohort reporting, and historical financial trend tracking",
      "Type": "TIMESTAMP"
    },
    {
      "Column Name": "end_date",
      "Column Description": "Optional date marking the conclusion of the customer relationship, used for customer churn analysis, revenue recognition adjustments, and contract lifecycle management",
      "Type": "DATE"
    },
    {
      "Column Name": "stage",
      "Column Description": "Customer lifecycle stage classification (e.g., Prospect, Active, Inactive) used for sales pipeline analysis, revenue forecasting, and customer relationship management",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "primary_subsidiary",
      "Column Description": "Primary NetSuite subsidiary associated with the customer for multi-entity financial reporting, intercompany transaction tracking, and consolidated financial statements",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "country",
      "Column Description": "Customer's primary country of operation used for international tax compliance, transfer pricing analysis, and geographic revenue segmentation",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "zipcode",
      "Column Description": "Postal code used for precise geographic financial reporting, tax jurisdiction determination, and compliance documentation",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "last_modified_date",
      "Column Description": "System timestamp of the most recent update to the customer record, supporting audit trails, SOX compliance documentation, and change management controls",
      "Type": "TIMESTAMP"
    }
  ],
  "Primary Key": "internal_id"
  },
  {
  "Table Name": "departments",
  "Table Description": "NetSuite's critical financial segmentation table that defines organizational cost centers for comprehensive management accounting, internal financial controls, and hierarchical performance reporting. This table serves as the foundational structure for departmental P&L analysis, cost allocation, budget variance tracking, and responsibility accounting. It enables precise financial segmentation, supports multi-level organizational reporting, and facilitates granular insights into operational performance, cost management, and strategic financial decision-making across the enterprise.",
  "Columns": [
    {
      "Column Name": "internal_id",
      "Column Description": "NetSuite's system-generated unique identifier for each department record that serves as the primary key and maintains referential integrity across general ledger entries, budget allocations, and financial reporting hierarchies",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "department_name",
      "Column Description": "The standardized organizational cost center designation used in departmental income statements, overhead allocation calculations, budget-to-actual variance reporting, and management accountability frameworks",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "parent_department",
      "Column Description": "Reference to the higher-level organizational unit, enabling hierarchical financial reporting, consolidated cost center analysis, and multi-level management accounting structures",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "last_modified_date",
      "Column Description": "System timestamp of the most recent update to the department configuration, supporting SOX compliance documentation, audit trails, and change management controls within NetSuite",
      "Type": "TIMESTAMP"
    }
  ],
  "Primary Key": "internal_id"
  },
  {
  "Table Name": "items",
  "Table Description": "NetSuite's comprehensive inventory and product master record that serves as the critical foundation for financial asset management, revenue recognition, and cost accounting. This table provides the definitive source of truth for inventory valuation, product costing, revenue forecasting, and financial reporting in compliance with ASC 330 (Inventory) and IAS 2 standards. It supports advanced financial analysis across product lifecycles, enabling precise gross margin calculations, inventory carrying cost assessments, and multi-dimensional financial reporting for both tangible and service-based products.",
  "Columns": [
    {
      "Column Name": "internal_id",
      "Column Description": "NetSuite's system-generated unique identifier that maintains referential integrity across all financial transactions, including invoices, purchase orders, inventory adjustments, and cost of goods sold journal entries",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "item_name",
      "Column Description": "The standardized stock keeping unit (SKU) identifier used in revenue recognition, inventory asset valuation, financial statement disclosures, and product-level financial reporting",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "item_description",
      "Column Description": "Detailed product specification critical for revenue recognition documentation, invoice line item substantiation, and financial audit trails supporting inventory valuation",
      "Type": "VARCHAR(500)"
    },
    {
      "Column Name": "base_price",
      "Column Description": "Standard list price used for revenue recognition, gross margin calculations, transfer pricing documentation, and financial planning revenue forecasting models",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "preferred_vendor",
      "Column Description": "Primary supplier for procurement, critical for accounts payable analysis, vendor concentration risk assessments, and supply chain financial risk management",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "purchase_price",
      "Column Description": "Standard cost basis used for inventory asset valuation, cost of goods sold calculations, gross margin analysis, and purchase price variance reporting",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "item_class",
      "Column Description": "Financial classification segment determining inventory asset accounting, revenue and COGS general ledger posting rules, and financial statement product categorization",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "manufacturer",
      "Column Description": "Original product producer used for supply chain liability disclosures, inventory provenance tracking, and vendor concentration risk analysis in financial reporting",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "item_type",
      "Column Description": "NetSuite's product classification (e.g., Inventory Item, Non-Inventory Item, Service, Assembly) that governs accounting treatment, revenue recognition, and financial statement presentation",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "is_inactive",
      "Column Description": "Status indicator determining whether the item is available for new transactions while preserving historical financial data for discontinued products",
      "Type": "VARCHAR(50)"
    },
    {
      "Column Name": "date_created",
      "Column Description": "System timestamp of initial item record creation, used for product lifecycle financial analysis, cohort reporting, and historical cost tracking",
      "Type": "TIMESTAMP"
    },
    {
      "Column Name": "last_modified_date",
      "Column Description": "Timestamp of the most recent update to the item configuration, supporting audit trails, SOX compliance documentation, and change management controls",
      "Type": "TIMESTAMP"
    }
  ],
  "Primary Key": "internal_id"
  },
  {
  "Table Name": "locations",
  "Table Description": "NetSuite's comprehensive location master record that serves as a critical financial and operational dimension for multi-entity, multi-location enterprise reporting. This table provides the foundational geographic and legal entity structure for financial consolidation, tax jurisdiction mapping, intercompany transaction tracking, and regulatory compliance across the organization's global operational footprint. It enables precise segmentation of financial performance, supports transfer pricing documentation, and facilitates complex multi-subsidiary reporting requirements.",
  "Columns": [
    {
      "Column Name": "internal_id",
      "Column Description": "NetSuite's system-generated unique identifier for each location record that serves as the primary key and maintains referential integrity across financial transactions, inventory management, and segment reporting",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "location_name",
      "Column Description": "The official business location name as registered with financial and tax authorities, used in statutory financial reporting, tax documentation, and regulatory compliance disclosures",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "phone",
      "Column Description": "Primary contact number for financial communications, regulatory correspondence, and legal entity verification purposes",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "parent_location",
      "Column Description": "Reference to the hierarchical parent location, supporting complex organizational structures, intercompany relationship mapping, and consolidated financial reporting",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "subsidiary",
      "Column Description": "Primary legal entity or subsidiary associated with this location, critical for multi-entity financial consolidation, transfer pricing documentation, and statutory reporting",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "city",
      "Column Description": "Municipal jurisdiction governing local business taxes, financial regulations, and geographic revenue segmentation for financial reporting purposes",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "state",
      "Column Description": "State or provincial tax jurisdiction determining regional tax rates, statutory compliance requirements, and geographic financial performance analysis",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "country",
      "Column Description": "Sovereign nation governing currency controls, international tax treaties, financial regulatory frameworks, and global financial consolidation processes",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "last_modified_date",
      "Column Description": "System timestamp of the most recent update to the location configuration, supporting audit trails, SOX compliance documentation, and change management controls within NetSuite",
      "Type": "TIMESTAMP"
    }
  ],
  "Primary Key": "internal_id"
  },
  {
  "Table Name": "subsidiaries",
  "Table Description": "NetSuite's critical financial master record defining the hierarchical structure of legal entities within the corporate consolidation framework. This table serves as the foundational architecture for multi-entity financial reporting, supporting complex global organizational structures in compliance with ASC 810 (Consolidation) and IFRS 10 standards. It facilitates comprehensive financial consolidation, intercompany transaction management, transfer pricing documentation, foreign currency translation, and statutory reporting across diverse international business units while enabling precise tracking of legal entity relationships, ownership structures, and financial performance segmentation.",
  "Columns": [
    {
      "Column Name": "internal_id",
      "Column Description": "NetSuite's system-generated unique identifier that maintains referential integrity across all financial consolidation transactions, intercompany eliminations, and entity-specific ledgers required for multi-entity accounting and reporting",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "subsidiary_name",
      "Column Description": "The legally registered entity name used in statutory financial statements, tax returns, regulatory filings, and transfer pricing documentation across jurisdictions",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "elimination",
      "Column Description": "Intercompany elimination classification indicating how the entity is treated in the consolidated financial reporting process to prevent double-counting of assets, liabilities, revenues, and expenses",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "currency",
      "Column Description": "Primary functional currency for the subsidiary, critical for foreign currency translation, consolidated financial statement preparation, and international financial reporting compliance",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "fiscal_calendar",
      "Column Description": "Unique fiscal calendar configuration governing the subsidiary's accounting periods, supporting multi-calendar reporting, period-end close processes, and financial consolidation synchronization",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "is_inactive",
      "Column Description": "Status indicator determining whether the subsidiary is actively participating in financial transactions while preserving historical financial data for audit and reporting purposes",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "last_modified_date",
      "Column Description": "System timestamp of the most recent update to the subsidiary configuration, supporting audit trails, SOX compliance documentation, and change management controls within NetSuite's multi-entity reporting framework",
      "Type": "TIMESTAMP"
    }
  ],
  "Primary Key": "internal_id"
  },
  {
    "Table Name": "transactions",
    "Table Description": "The Transactions table represents the comprehensive financial ledger within the NetSuite ecosystem, serving as the definitive single source of truth for all monetary events across the organization. Engineered to support complex global accounting requirements, this table captures the intricate details of financial transactions with unparalleled granularity. It provides a robust framework for multi-subsidiary, multi-currency, and multi-book accounting, enabling real-time financial reporting, comprehensive audit trails, and strategic decision-making. The table is meticulously designed to support enterprise-wide financial transparency, compliance, and advanced analytical capabilities, making it the cornerstone of the organization's financial management infrastructure.",
    "Columns": [
    {
      "Column Name": "transaction_id",
      "Column Description": "The primary key identifier for financial transactions in the NetSuite system, generating a unique, system-wide reference number that ensures absolute traceability and serves as the definitive audit trail marker. This identifier is critical for cross-system reconciliation, supporting drill-down capabilities, and maintaining the integrity of financial transaction tracking across the entire enterprise ecosystem. In NetSuite's sophisticated accounting architecture, this field provides an immutable link to the origin and lifecycle of every monetary event.",
      "Type": "DOUBLE NOT NULL"
    },
    {
      "Column Name": "subsidiary",
      "Column Description": "Captures the precise legal entity or subsidiary associated with the financial transaction, enabling sophisticated multi-entity accounting and consolidated financial reporting. This field is instrumental in supporting complex corporate structures, facilitating inter-company transaction tracking, and ensuring compliance with legal and statutory reporting requirements across different jurisdictions. NetSuite's multi-subsidiary accounting capabilities leverage this field to provide comprehensive visibility into financial performance across diverse organizational units.",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "subsidiary_id",
      "Column Description": "A unique system-generated identifier that links directly to the Subsidiaries master table, facilitating precise multi-entity financial consolidation and elimination processes. This field is crucial in NetSuite's advanced accounting framework, enabling seamless tracking, reporting, and analysis of financial transactions across different legal entities within the corporate structure.",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "transaction_date",
      "Column Description": "The definitive date of the financial event, critical for accurate revenue recognition, expense allocation, and period-specific financial reporting. This field supports NetSuite's robust accounting period management, ensuring precise timing of financial transactions for comprehensive financial statement preparation, tax reporting, and management accounting analysis.",
      "Type": "DATE"
    },
    {
      "Column Name": "period",
      "Column Description": "A detailed fiscal period designation that enables precise financial close, reporting, and compliance tracking. In NetSuite's advanced period management system, this field supports granular control over accounting periods, facilitating closed/open period controls, and providing a structured approach to financial reporting and analysis across different reporting frameworks.",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "document_number",
      "Column Description": "The external reference code that links the transaction to source documents such as invoices, payment vouchers, or journal entry identifiers. This field is crucial for comprehensive financial reconciliation, audit trail maintenance, and supporting detailed transaction verification processes within NetSuite's integrated accounting ecosystem.",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "transaction_type",
      "Column Description": "A comprehensive classification mechanism that defines the nature and purpose of the financial transaction, enabling advanced financial statement mapping, reporting, and analytical capabilities. NetSuite leverages this field to provide detailed transaction categorization, supporting sophisticated financial analysis, reporting, and strategic decision-making across various transaction types.",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "amount",
      "Column Description": "The gross transaction value in the functional currency, representing the total monetary impact of the financial event. This field is critical for comprehensive financial reporting, providing a standard measure of transaction value before tax considerations and supporting advanced financial analysis and reporting capabilities.",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "amount_debit",
      "Column Description": "Captures the debit ledger impact following double-entry accounting principles, providing precise tracking of financial increases in asset or expense accounts. This field is fundamental to NetSuite's robust accounting framework, ensuring accurate representation of financial transactions in compliance with standard accounting practices.",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "amount_credit",
      "Column Description": "Represents the credit ledger impact following double-entry accounting principles, tracking financial increases in liability, equity, or revenue accounts. This field is essential for maintaining the integrity of financial records and supporting comprehensive financial reporting within NetSuite's advanced accounting system.",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "account",
      "Column Description": "The definitive general ledger account designation representing the financial classification of the transaction within the organization's chart of accounts. This field is the cornerstone of NetSuite's financial reporting, enabling precise tracking, classification, and multi-dimensional analysis of monetary events across various financial perspectives.",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "account_id",
      "Column Description": "A unique system-generated identifier linking to the chart of accounts master table, facilitating advanced financial statement mapping, general ledger posting, and comprehensive financial reporting. This field supports NetSuite's sophisticated account tracking and analysis capabilities.",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "account_type",
      "Column Description": "Provides detailed account classification that determines financial statement positioning, accounting treatment, and reporting capabilities. NetSuite utilizes this field to enable advanced financial statement mapping, supporting comprehensive analysis across different account categories and financial reporting requirements.",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "account_name",
      "Column Description": "The descriptive name of the general ledger account, providing additional context and clarity to the financial classification. This field supports enhanced financial reporting and analysis by offering a human-readable representation of the account beyond its technical identifier.",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "account_number",
      "Column Description": "The unique numerical identifier for the general ledger account, supporting traditional accounting practices and facilitating precise account identification across financial reporting and analysis processes.",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "currency",
      "Column Description": "The ISO currency code capturing the original transaction currency, enabling comprehensive multi-currency accounting and foreign exchange management. This field is critical in NetSuite's global financial management capabilities, supporting precise tracking of monetary transactions across different currency domains.",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "currency_id",
      "Column Description": "A unique system-generated identifier for the transaction currency, supporting advanced multi-currency accounting and foreign exchange tracking within NetSuite's sophisticated financial management framework.",
      "Type": "VARCHAR(50)"
    },
    {
      "Column Name": "status",
      "Column Description": "Tracks the current processing state of the transaction within the financial workflow, supporting detailed transaction lifecycle management. This field enables comprehensive monitoring of transaction progression, from initial entry through posting and potential modifications.",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "line_id",
      "Column Description": "A unique identifier for individual journal entry line items, enabling granular transaction tracking and supporting NetSuite's advanced multi-line transaction capabilities. This field is critical for maintaining detailed audit trails, supporting line-level financial analysis, and ensuring comprehensive transaction integrity.",
      "Type": "DOUBLE NOT NULL"
    },
    {
      "Column Name": "class_name",
      "Column Description": "Provides a segment dimension for financial reporting, enabling cross-functional analysis by business line, product category, or strategic initiative. NetSuite leverages this field to support multi-dimensional financial reporting and sophisticated segmented performance analysis.",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "class_id",
      "Column Description": "A unique system-generated identifier for the classification dimension, supporting advanced multi-dimensional financial analysis and management reporting hierarchies within NetSuite's comprehensive accounting framework.",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "department_name",
      "Column Description": "Identifies the specific cost center or functional department associated with the financial transaction, enabling granular financial analysis, cost tracking, and departmental performance measurement. This field is crucial in NetSuite's multi-dimensional accounting approach, supporting detailed organizational financial insights.",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "department_id",
      "Column Description": "A unique system-generated identifier for the department or cost center, facilitating advanced financial tracking, analysis, and reporting across different organizational units within NetSuite's comprehensive accounting ecosystem.",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "location_name",
      "Column Description": "Captures the profit center or business location associated with the accounting entry, enabling geographical and location-based financial analysis. This field supports NetSuite's advanced multi-location financial reporting capabilities, providing insights into location-specific financial performance.",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "location_id",
      "Column Description": "A unique system-generated identifier for the profit center or business location, supporting sophisticated location-based financial analysis and reporting within NetSuite's comprehensive accounting framework.",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "customer_id",
      "Column Description": "A unique system-generated identifier for the accounts receivable entity involved in the transaction, enabling precise customer-related financial tracking and analysis. This field supports NetSuite's advanced customer financial management capabilities.",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "customer_name",
      "Column Description": "The legal name of the accounts receivable entity associated with the revenue transaction, providing comprehensive context for customer-related financial tracking and reporting.",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "vendor_id",
      "Column Description": "A unique system-generated identifier for the accounts payable entity involved in the transaction, supporting detailed vendor financial tracking and analysis within NetSuite's advanced accounting ecosystem.",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "vendor_name",
      "Column Description": "The legal name of the accounts payable entity associated with the expense transaction, providing comprehensive context for vendor-related financial tracking and reporting.",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "item_name",
      "Column Description": "Identifies the specific revenue or expense item involved in the accounting transaction, enabling detailed product or service-level financial analysis and reporting within NetSuite's comprehensive accounting framework.",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "item_id",
      "Column Description": "A unique system-generated identifier for the revenue or expense item, supporting advanced item-level financial tracking and analysis across the organization.",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "posting",
      "Column Description": "A boolean flag indicating the general ledger posting status of the accounting entry, critical for financial statement reporting and audit trail maintenance. This field supports NetSuite's rigorous financial control and reporting processes.",
      "Type": "VARCHAR(5)"
    },
    {
      "Column Name": "main_line_name",
      "Column Description": "The primary accounting description/entity name or memo for the journal entry line item, providing additional context and narrative explanation for the financial transaction. Entity name could be a Customer, Vendors, Partner, Employee or Project",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "est_gross_profit_percent_line",
      "Column Description": "Captures the calculated gross margin percentage for the revenue transaction line item, supporting detailed profitability analysis and contribution margin assessment within NetSuite's comprehensive financial reporting capabilities.",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "date_created",
      "Column Description": "The timestamp recording the initial creation of the accounting entry, providing a critical reference point for audit trail purposes and transaction origination tracking within NetSuite's financial system.",
      "Type": "TIMESTAMP"
    },
    {
      "Column Name": "last_modified_date",
      "Column Description": "The timestamp marking the most recent modification to the accounting entry, ensuring comprehensive change tracking and supporting audit compliance and financial control processes.",
      "Type": "TIMESTAMP"
    },
    {
      "Column Name": "amount_credit_foreign_currency",
      "Column Description": "A critical field in NetSuite's multi-currency accounting framework that captures the credit amount specifically calculated in the transaction's original currency. This field precisely tracks credit amounts for all the transactions, applying the appropriate exchange rate at the time of transaction. It enables accurate financial reporting by representing the exact credit value in the original currency, supporting comprehensive foreign currency accounting and ensuring precise revenue and payable recognition across international business operations.",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "amount_debit_foreign_currency",
      "Column Description": "A pivotal component of NetSuite's advanced multi-currency accounting capabilities, this field captures the debit amount calculated in the transaction's original currency. It precisely tracks debit amounts for all transactions, applying the relevant exchange rate at the time of the transaction. This field ensures accurate financial representation by maintaining the exact debit value in the original currency, supporting comprehensive foreign currency accounting and facilitating precise expense and receivable tracking across global business contexts.",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "amount_foreign_currency",
      "Column Description": "The comprehensive field in NetSuite's multi-currency accounting system that captures the total transaction amount calculated in the original currency. This field provides a complete representation of the transaction value, applying the applicable exchange rate at the time of transaction. It serves as a critical mechanism for maintaining financial accuracy, enabling precise foreign currency tracking, and supporting detailed international financial reporting across diverse business scenarios.",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "accounting_book",
      "Column Description": "A strategic field in NetSuite's advanced multi-book accounting framework that identifies and tracks the specific accounting perspective for a transaction. This field enables organizations to leverage NetSuite's multi-book functionality, allowing simultaneous maintenance of different accounting books such as US GAAP, regional accounting standards (e.g., India accounting regulations), or other specific regional accounting requirements. It provides granular control over financial reporting, supporting compliance with diverse accounting standards and enabling parallel accounting across different jurisdictional or reporting perspectives.",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "exchange_rate",
      "Column Description": "A critical financial metric in NetSuite's multi-currency accounting architecture that captures the precise currency conversion rate at the specific transaction date. This field represents the definitive exchange rate used to convert transaction currency to the subsidiary's functional currency, ensuring accurate financial reporting and comprehensive foreign exchange tracking. It plays a crucial role in maintaining financial accuracy across international transactions, supporting detailed foreign currency revaluation, and providing a transparent mechanism for currency conversion and financial statement preparation.",
      "Type": "DOUBLE"
    }
    ],
    "Primary Key Configuration": {
        "Key Columns": ["Transaction_ID", "Line_ID"],
        "Significance": "Ensures unique identification of each financial transaction line item, supporting comprehensive audit trail and transaction traceability"
    }
  },
  {
  "Table Name": "vendors",
  "Table Description": "NetSuite's comprehensive vendor master record that serves as the critical foundation for accounts payable management, procurement strategy, and financial supply chain operations. This table provides a holistic view of supplier relationships, supporting detailed spend analysis, vendor performance evaluation, tax compliance, and strategic financial decision-making. It enables precise tracking of vendor interactions, payment terms, expense categorization, and financial risk assessment across the organization's global supply chain ecosystem.",
  "Columns": [
    {
      "Column Name": "internal_id",
      "Column Description": "NetSuite's system-generated unique identifier for the accounts payable entity, maintaining referential integrity across procurement transactions, invoice processing, and financial reporting systems",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "vendor_name",
      "Column Description": "The legally registered business name of the vendor as it appears on invoices, purchase orders, tax documents, and financial statements, critical for accounts payable documentation",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "duplicate",
      "Column Description": "Flag indicating potential duplicate vendor records requiring consolidation to ensure accuracy in spend analysis, financial reporting, and vendor master data management",
      "Type": "VARCHAR(5)"
    },
    {
      "Column Name": "category",
      "Column Description": "Vendor classification for expense and procurement reporting, supporting financial statement segmentation, strategic sourcing analysis, and spend control (e.g., capital expenditure, operating expense, inventory supplier)",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "primary_contact",
      "Column Description": "Authorized vendor representative for accounts payable communications, payment authorizations, and strategic vendor relationship management",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "phone",
      "Column Description": "Primary contact number for accounts payable inquiries, vendor communication, payment reconciliation, and financial due diligence",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "email",
      "Column Description": "Electronic communication address for invoice submissions, payment notifications, vendor portal access, and accounts payable correspondence",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "login_access",
      "Column Description": "Indicator of vendor portal access status, enabling secure invoice submission, payment tracking, and self-service vendor management capabilities",
      "Type": "VARCHAR(5)"
    },
    {
      "Column Name": "date_created",
      "Column Description": "System timestamp of initial vendor record creation, used for vendor lifecycle analysis, historical spend tracking, and supplier relationship management metrics",
      "Type": "TIMESTAMP"
    },
    {
      "Column Name": "last_modified_date",
      "Column Description": "Timestamp of the most recent update to the vendor configuration, supporting audit trails, vendor master data governance, and change management controls",
      "Type": "TIMESTAMP"
    }
  ],
  "Primary Key": "internal_id"
  },
  {
  "Table Name": "inventory_details",
  "Table Description": "A comprehensive NetSuite repository tracking inventory assets across the supply chain for financial reporting and operational management. This table enables accurate inventory valuation, cost of goods sold calculations, and supply chain analytics while supporting compliance with accounting standards. It provides granular visibility into inventory status by location, facilitating detailed financial analysis, procurement planning, and order fulfillment metrics critical for financial statement preparation and management decision-making.",
  "Columns": [
    {
      "Column Name": "internal_id",
      "Column Description": "NetSuite's unique system-generated identifier for each inventory item that serves as the primary key and maintains referential integrity across the financial ERP ecosystem",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "inventory_detail_name",
      "Column Description": "Standard inventory item designation used in financial statements, purchase orders, sales invoices, and other accounting documentation",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "item_type",
      "Column Description": "NetSuite classification category (e.g., inventory item, non-inventory item, assembly) that determines accounting treatment, costing method, and balance sheet classification",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "description",
      "Column Description": "Detailed narrative description used in financial documentation, purchase orders, and customer-facing transaction records",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "base_price",
      "Column Description": "Standard list price used for revenue recognition, gross margin analysis, price variance reporting, and standard customer quotations",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "preferred_vendor",
      "Column Description": "Primary supplier in NetSuite's vendor master file, linked to accounts payable subledger and used for procurement automation and vendor spend analysis",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "purchase_price",
      "Column Description": "Standard cost or last purchase price used for inventory valuation, cost of goods sold calculations, and purchase price variance analysis",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "item_class",
      "Column Description": "NetSuite inventory classification hierarchy that supports segmented financial reporting, departmental cost allocations, and profitability analysis",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "manufacturer",
      "Column Description": "Original producer recorded for warranty accrual accounting, product liability reporting, and supply chain documentation compliance",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "quantity_on_hand",
      "Column Description": "Total physical units available company-wide, representing a key component of current assets on the balance sheet and used for inventory turnover calculations",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "quantity_on_order",
      "Column Description": "Aggregate units on purchase orders across all locations, representing future inventory commitments and associated accounts payable obligations",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "on_special",
      "Column Description": "Promotional pricing indicator affecting revenue recognition, discount accounting, and marketing expense allocations",
      "Type": "VARCHAR(5)"
    },
    {
      "Column Name": "preferred_location",
      "Column Description": "Strategic warehouse designation for both customer sales fulfillment and vendor purchase receiving, optimizing lead times and influencing cost accounting allocations",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "preferred_bin",
      "Column Description": "Specific warehouse storage position for precise inventory asset tracking, cycle count reconciliation, and warehouse carrying cost analysis",
      "Type": "VARCHAR(5)"
    },
    {
      "Column Name": "inventory_location",
      "Column Description": "Physical facility name in NetSuite's location hierarchy, essential for segment reporting, tax jurisdiction compliance, and regional P&L analysis",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "inventory_location_id",
      "Column Description": "NetSuite's unique identifier for the warehouse or storage facility, linking inventory assets to specific cost centers and geographic financial segments",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "location_back_ordered",
      "Column Description": "Quantity of customer orders received but unfulfillable from this location due to stock constraints, representing potential revenue at risk and customer satisfaction liabilities",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "location_committed",
      "Column Description": "Quantity allocated to sales orders at this location with fulfillment in process, recognized as committed inventory in financial reporting and excluded from available-to-promise calculations",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "location_in_transit",
      "Column Description": "Quantity shipped from this location but not yet received at destination, classified as in-transit inventory on the balance sheet with specific ownership and risk considerations",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "location_available",
      "Column Description": "Net quantity at this location available for sale after accounting for commitments and reservations, critical for available-to-promise calculations and sales fulfillment analysis",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "location_on_order",
      "Column Description": "Quantity on purchase orders for this location with vendor confirmation pending, representing uncommitted purchase commitments in procurement financial planning",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "location_on_hand",
      "Column Description": "Physical inventory units present at this specific location, used for location-specific asset valuation and inventory holding cost analysis",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "last_modified_date",
      "Column Description": "System timestamp of the most recent record update, essential for audit trails, SOX compliance documentation, and financial data validation procedures",
      "Type": "TIMESTAMP"
    }
  ],
  "Primary Key": "internal_id"
  },
  {
  "Table Name": "inventory_number",
  "Table Description": "A strategic NetSuite table that provides granular inventory tracking at the individual unit level, supporting lot traceability, serialization, and detailed inventory valuation. This table enables precise financial reporting of inventory assets, supports FIFO/LIFO accounting methods, facilitates accurate cost of goods sold calculations, and ensures regulatory compliance for industries requiring lot control or serialization. It serves as a critical component for inventory reconciliation, audit trails, and financial close processes while providing detailed visibility into inventory lifecycle metrics across different locations.",
  "Columns": [
    {
      "Column Name": "internal_id",
      "Column Description": "NetSuite's system-generated unique identifier for each inventory record that serves as the primary key and maintains data integrity across the financial ERP ecosystem",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "item_id",
      "Column Description": "Foreign key reference to the master inventory item in NetSuite's item master, enabling consolidated financial reporting and inventory valuation across multiple units",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "item_name",
      "Column Description": "Descriptive name of the inventory item as it appears in financial statements, purchase orders, invoices, and inventory reports",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "inventory_number",
      "Column Description": "Unique lot, batch, or serial number identifier used for specific inventory unit tracking, critical for FIFO/LIFO accounting and regulatory compliance",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "location",
      "Column Description": "Physical facility name where this inventory unit is stored, essential for segment reporting, tax jurisdiction compliance, and location-specific financial statements",
      "Type": "VARCHAR(255)"
    },
    {
      "Column Name": "location_id",
      "Column Description": "NetSuite's unique identifier for the storage facility, linking inventory assets to specific cost centers and geographic financial segments",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "quantity_in_transit",
      "Column Description": "Units currently being transferred between locations, classified as in-transit inventory on the balance sheet with specific ownership and risk accounting implications",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "quantity_available",
      "Column Description": "Net quantity available for sale or allocation, key for revenue forecasting, available-to-promise calculations, and working capital management",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "quantity_on_order",
      "Column Description": "Units on confirmed purchase orders but not yet received, representing future inventory commitments and associated accounts payable obligations",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "quantity_on_hand",
      "Column Description": "Physical inventory units possessed at this location, directly impacting balance sheet valuation, inventory carrying costs, and asset utilization metrics",
      "Type": "DOUBLE"
    },
    {
      "Column Name": "expiration_date",
      "Column Description": "Date when inventory units become obsolete or unusable, essential for inventory obsolescence reserves, impairment assessments, and markdown accounting",
      "Type": "DATE"
    },
    {
      "Column Name": "date_created",
      "Column Description": "Date when the inventory record was created in the system, supporting FIFO/LIFO accounting methods, inventory aging analysis, and audit trail documentation",
      "Type": "DATE"
    }
  ],
  "Primary Key": "internal_id"
  }
]    

SF_Examples = [
    {
        "input": "List down the names of all active products?",
        "query": "SELECT 'Name' FROM salesforce_products WHERE 'IsActive' = 'True';"
    },
    {
        "input": "List all opportunities that are not closed.",
        "query": "SELECT Name, StageName FROM salesforce_opportunities WHERE IsClosed = 'False';"
    },
    {
        "input": "What is the total expected revenue from all opportunities?",
        "query": "SELECT SUM(CAST('ExpectedRevenue' AS REAL)) AS TotalExpectedRevenue FROM salesforce_opportunities;"
    },
    {
        "input": "How many quotes are currently in draft status?",
        "query": "SELECT COUNT(*) FROM salesforce_quotes WHERE Status = 'Draft';"
    },
    {
        "input": " List all products with their product codes.",
        "query": "SELECT Name, ProductCode FROM salesforce_products;"
    },
    {
        "input": "What is the average amount of opportunities in the 'Qualification' stage?",
        "query": "SELECT AVG(CAST(Amount AS REAL)) AS AverageAmount FROM salesforce_opportunities WHERE StageName = 'Qualification';"
    },
    {
        "input": "List the total number of opportunities by their lead source.",
        "query": "SELECT LeadSource, COUNT(*) AS TotalOpportunities FROM salesforce_opportunities GROUP BY LeadSource;"
    },
    {
        "input": "What is the total price of all quote line items?",
        "query": "SELECT SUM(CAST(TotalPrice AS REAL)) AS TotalPriceSum FROM salesforce_quote_line_items;"
    },
    {
        "input": "Find the number of opportunities failed to won in each fiscal year.",
        "query": "SELECT FiscalYear, COUNT(*) AS NumberOfFailedOpportunities FROM salesforce_opportunities WHERE IsWon = 'False' GROUP BY FiscalYear;"
    },
    {
        "input": "List all quotes with their total price and the number of line items.",
        "query": "SELECT Name, TotalPrice, LineItemCount FROM salesforce_quotes;"
    },
    {
        "input": "What is the total revenue from opportunities that have associated quotes?",
        "query": "SELECT SUM(CAST(o.Amount AS REAL)) AS TotalRevenue FROM salesforce_opportunities o JOIN salesforce_quotes q ON o.Id = q.OpportunityId;"
    },
    {
        "input": "List all products that have been quoted, along with the total quantity quoted.",
        "query": "SELECT p.Name, SUM(q.Quantity) AS TotalQuantityQuoted FROM salesforce_products p JOIN salesforce_quote_line_items q ON p.Id = q.Product2Id GROUP BY p.Name;"
    },
    {
        "input": "Find the average discount given on quote line items for each product.",
        "query": "SELECT p.Name AS ProductName, AVG(CAST(q.Discount AS REAL)) AS AverageDiscount FROM salesforce_quote_line_items q JOIN salesforce_products p ON q.Product2Id = p.Id GROUP BY p.Name;"
    },
    {
        "input": "What are the total number of opportunities and their total expected revenue by type?",
        "query": "SELECT Type, COUNT(*) AS TotalOpportunities, SUM(CAST(ExpectedRevenue AS REAL)) AS TotalExpectedRevenue FROM salesforce_opportunities GROUP BY Type;"
    },
    {
        "input": "List the total number of quotes and their grand total by billing country.",
        "query": "SELECT BillingCountry, COUNT(Id) AS TotalQuotes, SUM(CAST(GrandTotal AS REAL)) AS TotalGrandTotal FROM salesforce_quotes GROUP BY BillingCountry;"
    }
    ]


    # Adding the Table_Info/Database Schema as the context to the model.(SF_Agent)

SF_TABLE_INFO = [
    {
        "Company_Name": "Honeycomb Holdings Inc.",
        "Company_Domain": "Management Consulting or Business Services"
    },
    {
        "Table Name": "salesforce_user_roles",
        "Table Description": "The salesforce_user_roles table stores hierarchical role-based access control (RBAC) information for users within a Salesforce organization. It defines user roles, their relationships (parent-child hierarchy), and their access permissions to accounts, opportunities, cases, and contacts. This table is essential for managing security, data visibility, and access control in Salesforce. Each record represents a unique role that can be assigned to users, determining what data they can view and edit. The table also tracks metadata like role names, system modification details, and portal-related attributes for external users.",
        "Column Name": "attributes",
        "Column Description": "Stores metadata about the user role object, including its type (UserRole) and a reference URL for accessing the specific record via Salesforce's API. This is useful for programmatic interactions, allowing developers to retrieve or manipulate the role using API requests.",
        "Type": "text"
    },
    {
        "Table Name": "salesforce_user_roles",
        "Table Description": "The salesforce_user_roles table stores hierarchical role-based access control (RBAC) information for users within a Salesforce organization. It defines user roles, their relationships (parent-child hierarchy), and their access permissions to accounts, opportunities, cases, and contacts. This table is essential for managing security, data visibility, and access control in Salesforce. Each record represents a unique role that can be assigned to users, determining what data they can view and edit. The table also tracks metadata like role names, system modification details, and portal-related attributes for external users.",
        "Column Name": "Id",
        "Column Description": "Unique identifier for the user role. This is the primary key of the table and is used to reference specific roles in the hierarchy.",
        "Type": "varchar(255) "
    },
    {
        "Table Name": "salesforce_user_roles",
        "Table Description": "The salesforce_user_roles table stores hierarchical role-based access control (RBAC) information for users within a Salesforce organization. It defines user roles, their relationships (parent-child hierarchy), and their access permissions to accounts, opportunities, cases, and contacts. This table is essential for managing security, data visibility, and access control in Salesforce. Each record represents a unique role that can be assigned to users, determining what data they can view and edit. The table also tracks metadata like role names, system modification details, and portal-related attributes for external users.",
        "Column Name": "Name",
        "Column Description": "Represents the title or designation of the user role within the organization. It defines the role\u00cds function or department in the company hierarchy. This column helps define the structure of user roles within the organization, ensuring appropriate access and permissions.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_user_roles",
        "Table Description": "The salesforce_user_roles table stores hierarchical role-based access control (RBAC) information for users within a Salesforce organization. It defines user roles, their relationships (parent-child hierarchy), and their access permissions to accounts, opportunities, cases, and contacts. This table is essential for managing security, data visibility, and access control in Salesforce. Each record represents a unique role that can be assigned to users, determining what data they can view and edit. The table also tracks metadata like role names, system modification details, and portal-related attributes for external users.",
        "Column Name": "ParentRoleId",
        "Column Description": "References the parent role in the hierarchy. If null, the role is at the top level. This is used to define role-based data access.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_user_roles",
        "Table Description": "The salesforce_user_roles table stores hierarchical role-based access control (RBAC) information for users within a Salesforce organization. It defines user roles, their relationships (parent-child hierarchy), and their access permissions to accounts, opportunities, cases, and contacts. This table is essential for managing security, data visibility, and access control in Salesforce. Each record represents a unique role that can be assigned to users, determining what data they can view and edit. The table also tracks metadata like role names, system modification details, and portal-related attributes for external users.",
        "Column Name": "RollupDescription",
        "Column Description": "Contains a description of how the role contributes to hierarchical data roll-up calculations, mainly for reporting and analytics.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_user_roles",
        "Table Description": "The salesforce_user_roles table stores hierarchical role-based access control (RBAC) information for users within a Salesforce organization. It defines user roles, their relationships (parent-child hierarchy), and their access permissions to accounts, opportunities, cases, and contacts. This table is essential for managing security, data visibility, and access control in Salesforce. Each record represents a unique role that can be assigned to users, determining what data they can view and edit. The table also tracks metadata like role names, system modification details, and portal-related attributes for external users.",
        "Column Name": "OpportunityAccessForAccountOwner",
        "Column Description": "Defines the level of access a role has to opportunities related to accounts they own. Values may include \"Read,\" \"Edit,\" or \"None.\"",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_user_roles",
        "Table Description": "The salesforce_user_roles table stores hierarchical role-based access control (RBAC) information for users within a Salesforce organization. It defines user roles, their relationships (parent-child hierarchy), and their access permissions to accounts, opportunities, cases, and contacts. This table is essential for managing security, data visibility, and access control in Salesforce. Each record represents a unique role that can be assigned to users, determining what data they can view and edit. The table also tracks metadata like role names, system modification details, and portal-related attributes for external users.",
        "Column Name": "CaseAccessForAccountOwner",
        "Column Description": "Specifies the level of access a role has to support cases linked to accounts they own. Controls visibility and edit permissions.\n",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_user_roles",
        "Table Description": "The salesforce_user_roles table stores hierarchical role-based access control (RBAC) information for users within a Salesforce organization. It defines user roles, their relationships (parent-child hierarchy), and their access permissions to accounts, opportunities, cases, and contacts. This table is essential for managing security, data visibility, and access control in Salesforce. Each record represents a unique role that can be assigned to users, determining what data they can view and edit. The table also tracks metadata like role names, system modification details, and portal-related attributes for external users.",
        "Column Name": "ContactAccessForAccountOwner",
        "Column Description": "Determines the access level for contacts associated with accounts owned by the role, impacting sharing rules and visibility.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_user_roles",
        "Table Description": "The salesforce_user_roles table stores hierarchical role-based access control (RBAC) information for users within a Salesforce organization. It defines user roles, their relationships (parent-child hierarchy), and their access permissions to accounts, opportunities, cases, and contacts. This table is essential for managing security, data visibility, and access control in Salesforce. Each record represents a unique role that can be assigned to users, determining what data they can view and edit. The table also tracks metadata like role names, system modification details, and portal-related attributes for external users.",
        "Column Name": "ForecastUserId",
        "Column Description": "References a user associated with this role for forecasting purposes. Helps track revenue projections and sales performance.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_user_roles",
        "Table Description": "The salesforce_user_roles table stores hierarchical role-based access control (RBAC) information for users within a Salesforce organization. It defines user roles, their relationships (parent-child hierarchy), and their access permissions to accounts, opportunities, cases, and contacts. This table is essential for managing security, data visibility, and access control in Salesforce. Each record represents a unique role that can be assigned to users, determining what data they can view and edit. The table also tracks metadata like role names, system modification details, and portal-related attributes for external users.",
        "Column Name": "MayForecastManagerShare",
        "Column Description": "Indicates whether this role allows forecast data to be shared with managers. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_user_roles",
        "Table Description": "The salesforce_user_roles table stores hierarchical role-based access control (RBAC) information for users within a Salesforce organization. It defines user roles, their relationships (parent-child hierarchy), and their access permissions to accounts, opportunities, cases, and contacts. This table is essential for managing security, data visibility, and access control in Salesforce. Each record represents a unique role that can be assigned to users, determining what data they can view and edit. The table also tracks metadata like role names, system modification details, and portal-related attributes for external users.",
        "Column Name": "LastModifiedDate",
        "Column Description": "Timestamp of the last modification made to this role record. Useful for tracking updates and audit purposes.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_user_roles",
        "Table Description": "The salesforce_user_roles table stores hierarchical role-based access control (RBAC) information for users within a Salesforce organization. It defines user roles, their relationships (parent-child hierarchy), and their access permissions to accounts, opportunities, cases, and contacts. This table is essential for managing security, data visibility, and access control in Salesforce. Each record represents a unique role that can be assigned to users, determining what data they can view and edit. The table also tracks metadata like role names, system modification details, and portal-related attributes for external users.",
        "Column Name": "LastModifiedById",
        "Column Description": "References the user who last modified this role. Helps identify the last person who updated role settings.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_user_roles",
        "Table Description": "The salesforce_user_roles table stores hierarchical role-based access control (RBAC) information for users within a Salesforce organization. It defines user roles, their relationships (parent-child hierarchy), and their access permissions to accounts, opportunities, cases, and contacts. This table is essential for managing security, data visibility, and access control in Salesforce. Each record represents a unique role that can be assigned to users, determining what data they can view and edit. The table also tracks metadata like role names, system modification details, and portal-related attributes for external users.",
        "Column Name": "SystemModstamp",
        "Column Description": "System-generated timestamp marking the last time the record was modified, used for tracking updates and synchronization.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_user_roles",
        "Table Description": "The salesforce_user_roles table stores hierarchical role-based access control (RBAC) information for users within a Salesforce organization. It defines user roles, their relationships (parent-child hierarchy), and their access permissions to accounts, opportunities, cases, and contacts. This table is essential for managing security, data visibility, and access control in Salesforce. Each record represents a unique role that can be assigned to users, determining what data they can view and edit. The table also tracks metadata like role names, system modification details, and portal-related attributes for external users.",
        "Column Name": "DeveloperName",
        "Column Description": "A unique API name assigned to the role, used by developers for reference in integrations and customizations.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_user_roles",
        "Table Description": "The salesforce_user_roles table stores hierarchical role-based access control (RBAC) information for users within a Salesforce organization. It defines user roles, their relationships (parent-child hierarchy), and their access permissions to accounts, opportunities, cases, and contacts. This table is essential for managing security, data visibility, and access control in Salesforce. Each record represents a unique role that can be assigned to users, determining what data they can view and edit. The table also tracks metadata like role names, system modification details, and portal-related attributes for external users.",
        "Column Name": "PortalAccountId",
        "Column Description": "References the account associated with this role for portal users. Relevant for roles assigned to external customer or partner users.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_user_roles",
        "Table Description": "The salesforce_user_roles table stores hierarchical role-based access control (RBAC) information for users within a Salesforce organization. It defines user roles, their relationships (parent-child hierarchy), and their access permissions to accounts, opportunities, cases, and contacts. This table is essential for managing security, data visibility, and access control in Salesforce. Each record represents a unique role that can be assigned to users, determining what data they can view and edit. The table also tracks metadata like role names, system modification details, and portal-related attributes for external users.",
        "Column Name": "PortalType",
        "Column Description": "Indicates the type of portal the role is associated with (e.g., \"Customer Portal,\" \"Partner Portal\"). Determines external user access levels.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_user_roles",
        "Table Description": "The salesforce_user_roles table stores hierarchical role-based access control (RBAC) information for users within a Salesforce organization. It defines user roles, their relationships (parent-child hierarchy), and their access permissions to accounts, opportunities, cases, and contacts. This table is essential for managing security, data visibility, and access control in Salesforce. Each record represents a unique role that can be assigned to users, determining what data they can view and edit. The table also tracks metadata like role names, system modification details, and portal-related attributes for external users.",
        "Column Name": "PortalAccountOwnerId",
        "Column Description": "References the owner of the portal account linked to this role. Helps manage access permissions for external users.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "attributes",
        "Column Description": "The attributes column contains metadata about the user record, stored as a JSON object. This metadata typically includes the type of Salesforce object (e.g., \"User\") and a url (e.g., an API endpoint) for accessing more detailed information about the user in Salesforce.",
        "Type": "text"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "Id",
        "Column Description": "A unique identifier for each user. This column is essential for identifying and distinguishing each user within the system. It serves as the primary key.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "Username",
        "Column Description": "The login username for the user. This column is used for authentication. It's crucial for login and access control.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "LastName",
        "Column Description": "The user's last name. Useful for display purposes, sorting, or filtering users by their last name.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "FirstName",
        "Column Description": "The user's first name. Used similarly to LastName, it helps in personalizing communications or search filters based on first name.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "Name",
        "Column Description": "A concatenation of FirstName and LastName.  A quick reference for displaying full user names, often used in reports or communication interfaces.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "CompanyName",
        "Column Description": "The name of the company to which the user belongs. Critical for segmentation in multi-tenant or enterprise-level systems where users are associated with different companies.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "Division",
        "Column Description": "The division within the company the user is associated with. Helps segment users for targeted actions, reporting, or specific permissions.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "Department",
        "Column Description": "The specific department where the user works. Can be used for department-specific access controls or to group users for reporting purposes.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "Title",
        "Column Description": "The user's job title. Useful for sorting users by role or title, such as in organizational charts, permissions, or email communication.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "Street",
        "Column Description": "The street address of the user. Helps in geo-targeting, communication, and when shipping physical goods or providing location-based services.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "City",
        "Column Description": "The city in which the user resides. Helps to segment users based on geographic location for targeted actions or reporting.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "State",
        "Column Description": "The state or region where the user resides. Enables geographical filtering for actions or regulations that vary by state.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "PostalCode",
        "Column Description": "The postal code (ZIP code) of the user's address. Used for sorting, geographic segmentation, and in some cases for targeted marketing or compliance.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "Country",
        "Column Description": "The country where the user is located. Critical for international segmentation, tax calculations, compliance (GDPR, etc.), and global reporting.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "Latitude",
        "Column Description": "The latitude coordinate for the user's address. Useful in location-based features such as proximity searches or geographic data analysis.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "Longitude",
        "Column Description": "The longitude coordinate for the user's address. Similar to Latitude, this helps with geographic analysis, such as mapping or geospatial querying.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "GeocodeAccuracy",
        "Column Description": "Indicates the accuracy of the geocoding for the user's address. Important for data quality assurance, ensuring that geographic data is accurate enough for applications.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "Address",
        "Column Description": "A full address concatenating Street, City, State, PostalCode, and Country. Simplifies address-related tasks and ensures full address is readily available.",
        "Type": "text"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "Email",
        "Column Description": "The user's email address. Used for communications, notifications, and login (if email is part of the login system).",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "EmailPreferencesAutoBcc",
        "Column Description": "Whether the user prefers automatic BCC on emails. A setting related to user preferences for email handling, especially for auditing or compliance. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "EmailPreferencesAutoBccStayInTouch",
        "Column Description": "Automatically BCCs the user on Stay-in-Touch messages, ensuring they have a copy for records. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "EmailPreferencesStayInTouchReminder",
        "Column Description": "Enables reminders for Stay-in-Touch updates, helping users maintain updated contact info. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "SenderEmail",
        "Column Description": "Defines the email address used when the user sends messages from Salesforce. Useful for customizing sender identity.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "SenderName",
        "Column Description": "The display name for emails sent from Salesforce. Helps with personalization and branding.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "Signature",
        "Column Description": "The custom email signature attached to outbound emails. Useful for consistency in communication.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "StayInTouchSubject",
        "Column Description": "The default subject for Stay-in-Touch messages, helping maintain engagement.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "StayInTouchSignature",
        "Column Description": "The custom closing signature for Stay-in-Touch messages.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "StayInTouchNote",
        "Column Description": "A personalized note included in Stay-in-Touch emails.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "Phone",
        "Column Description": "User's primary phone number for contact.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "Fax",
        "Column Description": "User's fax number if applicable. Often used for document transmission.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "MobilePhone",
        "Column Description": "The user's mobile phone number for SMS and direct communication.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "Alias",
        "Column Description": "A shorter username identifier (8 characters max) used in reports & searches.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "CommunityNickname",
        "Column Description": "The user's display name in Salesforce Communities.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "BadgeText",
        "Column Description": "Text displayed as a badge or label on the user\u00d5s profile.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "IsActive",
        "Column Description": "Determines if the user can log in and access Salesforce. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "TimeZoneSidKey",
        "Column Description": "The user's time zone setting, used for date/time display adjustments.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserRoleId",
        "Column Description": "Defines the role assigned to the user within the organization.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "LocaleSidKey",
        "Column Description": "Defines the user's locale, affecting date, number, and currency formatting.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "ReceivesInfoEmails",
        "Column Description": "Determines if the user receives marketing emails from Salesforce. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "ReceivesAdminInfoEmails",
        "Column Description": "Determines if the user receives admin-related emails (e.g., system updates). Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "EmailEncodingKey",
        "Column Description": "Specifies character encoding for emails (e.g., UTF-8, ISO-8859-1).",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "ProfileId",
        "Column Description": "Links to a Profile, determining access to objects, fields, and permissions.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserType",
        "Column Description": "Specifies the type of user (Standard, Partner, Customer, etc.).",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "StartDay",
        "Column Description": "The start day of a user's workweek, typically represented as a number. Helps in scheduling, time tracking, and defining the beginning of the work cycle for employees. Used in time-based reporting, leave calculations, and workflow automation.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "EndDay",
        "Column Description": "The last working day of the user's workweek. Defines the end of the user\u00d5s work cycle and is useful in scheduling. Applied in defining weekend policies, overtime calculations, and scheduling automation.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "LanguageLocaleKey",
        "Column Description": "Specifies the language and locale settings for the user (e.g., en_US for English - United States). Determines language preferences for UI, emails, and communications. Ensures that the Salesforce interface and notifications are presented in the preferred language of the user.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "EmployeeNumber",
        "Column Description": "A unique identifier assigned to an employee within the organization. Helps in user management, reporting, and integration with HR systems. Often used in payroll systems, employee records, and compliance tracking.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "DelegatedApproverId",
        "Column Description": "The user who can approve requests on behalf of this user.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "ManagerId",
        "Column Description": "Links to the manager of this user, used for approvals and reporting.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "LastLoginDate",
        "Column Description": "The last time the user successfully logged in.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "LastPasswordChangeDate",
        "Column Description": "The last time the user changed their password.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "CreatedDate",
        "Column Description": "When the user record was created. Important for audits.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "CreatedById",
        "Column Description": "The ID of the user who created this record.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "LastModifiedDate",
        "Column Description": "The last time this record was updated.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "LastModifiedById",
        "Column Description": "The ID of the user who last updated this record.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "SystemModstamp",
        "Column Description": "A timestamp for system-level modifications (e.g., API updates).",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "PasswordExpirationDate",
        "Column Description": "The date when the user\u00d5s password expires.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "NumberOfFailedLogins",
        "Column Description": "Tracks failed login attempts, useful for security monitoring.",
        "Type": "int"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "SuAccessExpirationDate",
        "Column Description": "The expiration date for Super User (SU) access. Critical for managing high-privilege accounts and limiting access based on security policies. Used to enforce temporary elevated access for troubleshooting, audits, or emergency tasks.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "OfflineTrialExpirationDate",
        "Column Description": "Specifies when the user's offline trial period will expire. Important for tracking trial periods for offline access features. Ensures that trial access to offline functionality is revoked after a set period.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "OfflinePdaTrialExpirationDate",
        "Column Description": "Expiration date for offline PDA (Personal Digital Assistant) access. Manages trial periods for users accessing Salesforce via PDA devices. Used for licensing and compliance tracking for mobile device access.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPermissionsMarketingUser",
        "Column Description": "If True, the user can create and manage campaigns. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPermissionsOfflineUser",
        "Column Description": "If True, the user can access data offline. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPermissionsCallCenterAutoLogin",
        "Column Description": "Determines whether the user is allowed to auto-login to Salesforce Call Center. Enhances user experience for call center agents by streamlining login. Used in call center automation to allow agents to log in automatically without manual authentication. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPermissionsSFContentUser",
        "Column Description": "Grants permission to access Salesforce Content. Controls whether the user can create, edit, and manage Salesforce Content. Used in document management, file sharing, and collaboration. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPermissionsKnowledgeUser",
        "Column Description": "Allows knowledge base article management. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPermissionsInteractionUser",
        "Column Description": "Grants permission for interaction-related features in Salesforce. Controls user access to customer interaction data. Commonly used in customer service and sales functions. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPermissionsSupportUser",
        "Column Description": "Grants access to case management and support tools. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPermissionsJigsawProspectingUser",
        "Column Description": "Determines if the user can access Jigsaw (now part of Data.com) for prospecting. Grants access to business contact and company data. Used in sales prospecting to find and qualify leads. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPermissionsSiteforceContributorUser",
        "Column Description": "Allows the user to contribute content to Siteforce (Salesforce Sites). Controls content contributions for web portals and customer-facing sites. Used by content creators and marketing teams. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPermissionsSiteforcePublisherUser",
        "Column Description": "Allows the user to publish content on Salesforce Sites. Enables website administrators to publish updates. Used in website and portal management. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPermissionsWorkDotComUserFeature",
        "Column Description": "Grants access to Work.com features (Salesforce\u00d5s performance management tool). Enables users to access coaching, feedback, and recognition tools. Used in HR and performance management workflows. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "ForecastEnabled",
        "Column Description": "Indicates whether the user has forecasting enabled. Controls access to revenue and sales forecasting tools. Used in sales pipeline management. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesActivityRemindersPopup",
        "Column Description": "Determines if users receive popup reminders for activities. Helps users stay on top of scheduled tasks. Used in task and event management. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesEventRemindersCheckboxDefault",
        "Column Description": "Controls whether event reminders are checked by default. Ensures users do not miss calendar events. Default behavior for event notifications. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesTaskRemindersCheckboxDefault",
        "Column Description": "Controls whether task reminders are enabled by default. Ensures tasks are not forgotten. Used in task management automation. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesReminderSoundOff",
        "Column Description": "Determines whether reminder sounds are turned off. Provides users with control over notification sounds. Customizes the user experience. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesDisableAllFeedsEmail",
        "Column Description": "Disables all email notifications from Chatter feeds. Reduces email clutter. Used by users who prefer to engage only within Salesforce. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesDisableFollowersEmail",
        "Column Description": "Controls whether the user receives email notifications when they get a new follower in Salesforce Chatter. Helps users manage email overload from Chatter notifications. Used by those who prefer to track followers within Salesforce rather than through email. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesDisableProfilePostEmail",
        "Column Description": "Determines whether the user receives emails when someone posts on their Chatter profile. Helps users control email notifications from profile interactions. Ideal for users who prefer to monitor Chatter activity in-app rather than via email. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesDisableChangeCommentEmail",
        "Column Description": "Disables email notifications when someone edits a comment on a user\u00d5s post. Prevents unnecessary email updates for minor comment edits. Used by users who want to reduce email clutter. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesDisableLaterCommentEmail",
        "Column Description": "Controls whether users receive emails when someone comments on a Chatter post they have previously engaged with. Helps manage email notifications from ongoing discussions. Helps in reducing unwanted follow-up notifications. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesDisProfPostCommentEmail",
        "Column Description": "Disables email notifications when someone comments on a post made on the user's profile. Allows users to choose whether they want to be notified about post interactions via email. Helps users manage their engagement with Chatter posts more efficiently. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesContentNoEmail",
        "Column Description": "Disables email notifications related to Salesforce Content updates. Useful for users who do not want email alerts when new content is published or updated. Helps reduce unnecessary email notifications. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesContentEmailAsAndWhen",
        "Column Description": "Enables immediate email notifications for Salesforce Content updates. Ensures users are promptly notified about new content. Useful for users who actively engage with Salesforce Content. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesApexPagesDeveloperMode",
        "Column Description": "Enables developer mode for Apex Visualforce pages. Useful for developers debugging and modifying Apex pages. Allows inline editing and debugging tools for Visualforce development. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesReceiveNoNotificationsAsApprover",
        "Column Description": "Disables notifications when the user is assigned as an approver in an approval process. Reduces notification overload for high-volume approvers. Typically used by senior management who rely on other tracking methods. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesReceiveNotificationsAsDelegatedApprover",
        "Column Description": "Enables notifications when the user is assigned as a delegated approver. Ensures delegated approvers are notified when they have items to approve. Used in workflows where approvals are delegated. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesHideCSNGetChatterMobileTask",
        "Column Description": "Hides Chatter mobile onboarding tasks. Helps streamline the onboarding experience. Used to declutter the user interface for experienced users. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesDisableMentionsPostEmail",
        "Column Description": "Prevents email notifications when the user is mentioned in a Chatter post. Helps users manage email overload from mentions. Used by users who prefer in-app notifications. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesDisMentionsCommentEmail",
        "Column Description": "Disables email notifications when the user is mentioned in a Chatter comment. Reduces email clutter for users frequently mentioned in discussions. Ideal for users who prefer to check Chatter manually. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesHideCSNDesktopTask",
        "Column Description": "Hides Chatter desktop onboarding tasks. Reduces UI clutter for users already familiar with Chatter. Enhances user experience for advanced users. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesHideChatterOnboardingSplash",
        "Column Description": "Prevents the Chatter onboarding splash screen from appearing. Streamlines the user experience. Typically used for experienced users who do not need onboarding. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesHideSecondChatterOnboardingSplash",
        "Column Description": "Hides the second-stage Chatter onboarding splash. Further refines the user experience. Used in UI customization for returning users. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesDisCommentAfterLikeEmail",
        "Column Description": "Prevents email notifications when someone comments after liking a post. Reduces unnecessary notifications. Helps users control the number of emails they receive. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesDisableLikeEmail",
        "Column Description": "If True, disables like notifications for posts/comments. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesSortFeedByComment",
        "Column Description": "Sorts Chatter feeds by comment activity rather than chronological order. Highlights active discussions. Enhances engagement with Chatter feeds. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesDisableMessageEmail",
        "Column Description": "Disables email notifications when the user receives a direct message in Salesforce Chatter.  Helps reduce email clutter. Users who prefer to check messages within Salesforce rather than receiving email alerts. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesHideLegacyRetirementModal",
        "Column Description": "Controls whether the retirement modal for legacy features is hidden. Useful for organizations transitioning to Lightning Experience that do not want unnecessary prompts. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesJigsawListUser",
        "Column Description": "Determines if the user has access to Jigsaw (now Data.com) lists. Relevant for sales teams leveraging Data.com for lead generation. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesDisableBookmarkEmail",
        "Column Description": "Prevents email notifications when a post or content is bookmarked by the user. Avoids unnecessary email alerts for personal bookmarks. Ideal for users who bookmark frequently and prefer to track content within Salesforce. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesDisableSharePostEmail",
        "Column Description": "Disables email notifications when a user's post is shared. Reduces notification overload. Helps users control the volume of emails they receive. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesEnableAutoSubForFeeds",
        "Column Description": "Auto-subscribes the user to feed updates. Helps users stay updated on discussions they participate in. Ensures users don\u00d5t miss replies to their comments.  Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesDisableFileShareNotificationsForApi",
        "Column Description": "Prevents email notifications when a file is shared via API interactions. Useful in integrations where large volumes of files are shared programmatically. Reduces email overload from automated processes. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesShowTitleToExternalUsers",
        "Column Description": "Controls whether the user's job title is visible to external users. Ensures privacy settings are adhered to. Used to limit exposure of internal details. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesShowManagerToExternalUsers",
        "Column Description": "Controls whether the user's manager is visible to external users. Helps manage visibility in business networks. Used in corporate hierarchy settings. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesShowEmailToExternalUsers",
        "Column Description": "Controls email visibility to external users. Protects user contact details from exposure. Used for privacy settings in external collaborations. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesShowWorkPhoneToExternalUsers",
        "Column Description": "Controls Workphone information is visible to external users in Salesforce. Helps maintain user privacy while allowing selective visibility of business information. Organizations configure these settings based on data-sharing policies. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesShowMobilePhoneToExternalUsers",
        "Column Description": "Controls Mobilephone information is visible to external users in Salesforce. Helps maintain user privacy while allowing selective visibility of business information. Organizations configure these settings based on data-sharing policies. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesShowFaxToExternalUsers",
        "Column Description": "Controls Fax information is visible to external users in Salesforce. Helps maintain user privacy while allowing selective visibility of business information. Organizations configure these settings based on data-sharing policies. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesShowStreetAddressToExternalUsers",
        "Column Description": "Controls StreetAddress information is visible to external users in Salesforce. Helps maintain user privacy while allowing selective visibility of business information. Organizations configure these settings based on data-sharing policies. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesShowCityToExternalUsers",
        "Column Description": "Controls City information is visible to external users in Salesforce. Helps maintain user privacy while allowing selective visibility of business information. Organizations configure these settings based on data-sharing policies. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesShowStateToExternalUsers",
        "Column Description": "Controls State information is visible to external users in Salesforce. Helps maintain user privacy while allowing selective visibility of business information. Organizations configure these settings based on data-sharing policies. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesShowPostalCodeToExternalUsers",
        "Column Description": "Controls PostalCode information is visible to external users in Salesforce. Helps maintain user privacy while allowing selective visibility of business information. Organizations configure these settings based on data-sharing policies. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesShowCountryToExternalUsers",
        "Column Description": "Controls Country information is visible to external users in Salesforce. Helps maintain user privacy while allowing selective visibility of business information. Organizations configure these settings based on data-sharing policies. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesShowProfilePicToGuestUsers",
        "Column Description": "Defines ProfilePic information is visible to guest users (users without authentication). Helps maintain user privacy while allowing selective visibility of business information. Organizations configure these settings based on data-sharing policies. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesShowTitleToGuestUsers",
        "Column Description": "Defines Title information is visible to guest users (users without authentication). Helps maintain user privacy while allowing selective visibility of business information. Organizations configure these settings based on data-sharing policies. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesShowCityToGuestUsers",
        "Column Description": "Defines City information is visible to guest users (users without authentication). Helps maintain user privacy while allowing selective visibility of business information. Organizations configure these settings based on data-sharing policies. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesShowStateToGuestUsers",
        "Column Description": "Defines State information is visible to guest users (users without authentication). Helps maintain user privacy while allowing selective visibility of business information. Organizations configure these settings based on data-sharing policies. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesShowPostalCodeToGuestUsers",
        "Column Description": "Defines PostalCode information is visible to guest users (users without authentication). Helps maintain user privacy while allowing selective visibility of business information. Organizations configure these settings based on data-sharing policies. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesShowCountryToGuestUsers",
        "Column Description": "Defines Country information is visible to guest users (users without authentication). Helps maintain user privacy while allowing selective visibility of business information. Organizations configure these settings based on data-sharing policies. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesShowForecastingChangeSignals",
        "Column Description": "Enables indicators for forecasting changes in reports. Helps sales teams track pipeline changes. Provides insights into sales performance trends. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesHideS1BrowserUI",
        "Column Description": "Determines whether the Salesforce1 (now Salesforce Mobile) browser-based UI is hidden for the user. Useful for organizations that want users to access Salesforce only through the mobile app instead of a browser. Helps enforce mobile app usage and streamline the user experience. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesDisableEndorsementEmail",
        "Column Description": "Disables email notifications when a user is endorsed for a skill in Salesforce Chatter. Helps reduce unnecessary email clutter from endorsements. Used by users who prefer to track skill endorsements within Salesforce rather than receiving email notifications. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesPathAssistantCollapsed",
        "Column Description": "Determines whether the Path Assistant section is collapsed by default. Controls UI customization based on user preference. Used in sales workflows where path guidance is not needed. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesCacheDiagnostics",
        "Column Description": "Enables cache diagnostics for troubleshooting performance issues. Helps in debugging and optimizing Salesforce performance. Used by developers and IT admins. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesShowEmailToGuestUsers",
        "Column Description": "Defines Email information is visible to guest users (users without authentication). Helps maintain user privacy while allowing selective visibility of business information. Organizations configure these settings based on data-sharing policies. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesShowManagerToGuestUsers",
        "Column Description": "Defines Manager information is visible to guest users (users without authentication). Helps maintain user privacy while allowing selective visibility of business information. Organizations configure these settings based on data-sharing policies. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesShowWorkPhoneToGuestUsers",
        "Column Description": "Defines Workphone information is visible to guest users (users without authentication). Helps maintain user privacy while allowing selective visibility of business information. Organizations configure these settings based on data-sharing policies. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesShowMobilePhoneToGuestUsers",
        "Column Description": "Defines MobilePhone information is visible to guest users (users without authentication). Helps maintain user privacy while allowing selective visibility of business information. Organizations configure these settings based on data-sharing policies. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesShowFaxToGuestUsers",
        "Column Description": "Defines Fax information is visible to guest users (users without authentication). Helps maintain user privacy while allowing selective visibility of business information. Organizations configure these settings based on data-sharing policies. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesShowStreetAddressToGuestUsers",
        "Column Description": "Defines StreetAddress information is visible to guest users (users without authentication). Helps maintain user privacy while allowing selective visibility of business information. Organizations configure these settings based on data-sharing policies. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesLightningExperiencePreferred",
        "Column Description": "If True, user prefers Lightning UI over Classic. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesPreviewLightning",
        "Column Description": "Enables the Lightning Experience preview. Allows users to test new UI before full adoption. Used in transition planning for UI updates. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesHideEndUserOnboardingAssistantModal",
        "Column Description": "Prevents the onboarding assistant modal from appearing in Lightning Experience. Reduces distractions for experienced users. Streamlines the UI for power users. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesHideLightningMigrationModal",
        "Column Description": "Determines whether the Lightning Experience migration modal is hidden for the user. Prevents the user from seeing the pop-up message that encourages migration to Lightning Experience. Useful for organizations that do not want users to be prompted about switching to Lightning or for users who prefer Classic. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesHideSfxWelcomeMat",
        "Column Description": "Controls whether the Salesforce Experience (SFX) Welcome Mat is displayed. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesHideBiggerPhotoCallout",
        "Column Description": "Hides the callout that encourages users to upload a larger profile photo. Prevents users from seeing notifications suggesting they upload a higher-resolution profile picture. Useful for organizations that do not prioritize profile photo updates or want to reduce non-essential notifications. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesGlobalNavBarWTShown",
        "Column Description": "Tracks whether the global navigation bar walkthrough has been shown. Used in UI onboarding experiences. Helps track user education on new features. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesGlobalNavGridMenuWTShown",
        "Column Description": "Indicates whether the user has been shown the Global Navigation Grid Menu walkthrough. Ensures users are familiar with navigation elements, improving usability. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesCreateLEXAppsWTShown",
        "Column Description": "Specifies whether the user has been shown the walkthrough for creating apps in Lightning Experience. Useful for monitoring user training and onboarding progress. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesFavoritesWTShown",
        "Column Description": "Indicates whether the walkthrough for using the Favorites feature in Lightning Experience has been shown. Enhances user familiarity with the Favorites function for quick access to frequently used records. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesRecordHomeSectionCollapseWTShown",
        "Column Description": "Determines if the user has seen the walkthrough explaining how to collapse sections on a record home page. Useful for tracking whether users have learned about optimizing their interface. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesRecordHomeReservedWTShown",
        "Column Description": "Indicates if the user has seen the Record Home Reserved Walkthrough. Helps track onboarding completion. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesFavoritesShowTopFavorites",
        "Column Description": "Controls whether the user sees top favorites at the top of the navigation bar. Improves navigation efficiency for power users. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesExcludeMailAppAttachments",
        "Column Description": "Prevents attachments from being included in Salesforce emails sent via the Mail App. Helps manage email storage and security concerns. Used to limit the size of outbound emails. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesSuppressTaskSFXReminders",
        "Column Description": "Suppresses task-related reminders in Salesforce for the user. Prevents unnecessary pop-ups or notifications. Used by users who manage tasks manually. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesSuppressEventSFXReminders",
        "Column Description": "Disables event reminders in Salesforce. Helps users focus on their workflow without constant notifications. Useful for users who prefer managing event schedules separately. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesPreviewCustomTheme",
        "Column Description": "Determines whether the user can preview custom themes before applying them. Useful for organizations that want to standardize branding. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesHasCelebrationBadge",
        "Column Description": "Indicates if the user has a celebration badge enabled. Used in gamification strategies within Salesforce. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesUserDebugModePref",
        "Column Description": "Enables or disables debug mode for the user. Typically enabled for developers testing custom scripts in Lightning Experience. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesSRHOverrideActivities",
        "Column Description": "Determines if activities are overridden in the Service Resource Hierarchy (SRH). Relevant for service teams managing structured resource hierarchies. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesNewLightningReportRunPageEnabled",
        "Column Description": "Enables the new Lightning report run page experience. Gives users access to the latest reporting UI. Used by organizations transitioning to enhanced reporting. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesReverseOpenActivitiesView",
        "Column Description": "Reverses the default sorting of open activities. Allows customization of how open tasks are displayed. Helps users prioritize tasks more effectively. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesShowTerritoryTimeZoneShifts",
        "Column Description": "Controls whether users see time zone shifts in territory management. Useful for companies with distributed sales territories. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesHasSentWarningEmail",
        "Column Description": "Indicates if the user has been sent a warning email regarding system usage or policy violations. Typically used by administrators for monitoring user activity. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesHasSentWarningEmail238",
        "Column Description": "A specific version of the warning email tracking flag, likely related to a particular policy or system update. Ensures users are informed about system changes or violations. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesHasSentWarningEmail240",
        "Column Description": "Another variant of the warning email preference, tracking if a particular type of system-related email has been sent. Useful for administrators enforcing policy adherence. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "UserPreferencesNativeEmailClient",
        "Column Description": "Determines if the user prefers to use their native email client instead of Salesforce email functionalities. Useful for users who prefer Outlook, Gmail, or other native email clients over Salesforce email. Boolean field (e.g., True or False).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "ContactId",
        "Column Description": "The ID of the contact record associated with the user. Links users to contacts in CRM. Used for customer relationship mapping.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "AccountId",
        "Column Description": "The ID of the account associated with the user. Links users to company accounts. Used in business hierarchy management.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "CallCenterId",
        "Column Description": "The ID of the call center the user belongs to. Associates users with call center configurations. Used in telephony integrations.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "Extension",
        "Column Description": "The user's phone extension. Used in corporate directories. Helps in internal call routing.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "FederationIdentifier",
        "Column Description": "A unique identifier for federated authentication. Enables SSO (Single Sign-On). Used in authentication and identity management.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "AboutMe",
        "Column Description": "User's biography or self-description. Provides context in collaboration tools. Visible in Chatter and profile pages.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "FullPhotoUrl",
        "Column Description": "URL to the user's full-size profile photo. Used for identification. Displayed in user profiles and Chatter.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "SmallPhotoUrl",
        "Column Description": "URL to a smaller version of the profile photo. Used in UI elements requiring compact images. Displayed in comments, feed posts, and notifications.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "IsExtIndicatorVisible",
        "Column Description": "Indicates whether an external indicator is displayed on the user's profile. Helps distinguish internal vs. external users.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "OutOfOfficeMessage",
        "Column Description": "Stores the user's out-of-office message. Helps notify colleagues of availability.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "MediumPhotoUrl",
        "Column Description": "URL to a medium-sized version of the profile photo. Optimized for different screen sizes. Used in profile previews.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "DigestFrequency",
        "Column Description": "Defines how often the user receives summary notifications for Chatter and group activities. Helps manage email notification preferences.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "DefaultGroupNotificationFrequency",
        "Column Description": "Defines how often the user receives summary notifications for Chatter and group activities. Helps manage email notification preferences.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "JigsawImportLimitOverride",
        "Column Description": "Custom import limit for Jigsaw (Data.com) records. Used in Salesforce Data.com integrations.",
        "Type": "int"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "LastViewedDate",
        "Column Description": "The last date the user accessed their Salesforce profile. Useful for monitoring engagement. Helps administrators track active users.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "LastReferencedDate",
        "Column Description": "The last time the user was referenced in an activity or interaction. Helps in tracking user interactions. Used in reporting and engagement tracking.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "BannerPhotoUrl",
        "Column Description": "URLs for banner images on the user's profile.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "SmallBannerPhotoUrl",
        "Column Description": "URLs for banner images on the user's profile.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "MediumBannerPhotoUrl",
        "Column Description": "URLs for banner images on the user's profile.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "IsProfilePhotoActive",
        "Column Description": "Indicates if the user's profile photo is active.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_users",
        "Table Description": "The salesforce_users table stores information about users within the Salesforce system, including employees, partners, and other stakeholders who have access to the platform. This table contains essential details such as usernames, contact information, roles, permissions, and system preferences. The data in this table helps define user identities, access levels, preferences, and system-wide settings that control how users interact with Salesforce features, including email settings, login details, localization, and notification preferences.",
        "Column Name": "IndividualId",
        "Column Description": "Links the user to an Individual record for GDPR compliance.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "attributes",
        "Column Description": "The attributes column stores metadata related to the Salesforce record, including API version, record type, and object reference details. It helps in tracking system-related information when integrating Salesforce with external systems via API calls. This metadata is crucial for automated processes, as it enables developers to access structured data about records without querying multiple fields separately.",
        "Type": "text"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "Id",
        "Column Description": "The Id column (Primary Key) is the unique identifier assigned to each account record within Salesforce. It is an alphanumeric string (15 or 18 characters) that allows precise retrieval and manipulation of data. Its significance extends to integrations where external systems reference Salesforce accounts through this identifier.",
        "Type": "varchar(255"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "IsDeleted",
        "Column Description": "The IsDeleted column is a boolean flag indicating whether an account has been deleted (TRUE) or remains active (FALSE). This field is essential for auditing and maintaining data integrity, as it helps track deletions and prevent unintended data loss.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "MasterRecordId",
        "Column Description": "The MasterRecordId field is used when duplicate accounts are merged in Salesforce. It stores the ID of the master (or surviving) record, allowing for data consolidation while preserving historical references. This column plays a vital role in maintaining data cleanliness and avoiding duplicate records, which is critical for CRM efficiency and reporting accuracy.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "Name",
        "Column Description": "The Name column represents the official name of the account, typically the business or organization name. It is a required field and a fundamental identifier used in CRM workflows, searches, and reporting. The Name field is crucial for account management, as it provides an easily recognizable label for sales and support teams when interacting with customers.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "Type",
        "Column Description": "The Type column categorizes the account based on its business relationship, such as \"Customer,\" \"Vendor,\" \"Partner,\" or \"Prospect.\" This classification is essential for segmentation, reporting, and targeting within sales and marketing efforts. It allows businesses to tailor engagement strategies based on the account type, improving customer relationship management and business planning.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "ParentId",
        "Column Description": "The ParentId column establishes hierarchical relationships between accounts, linking a subsidiary to its parent company. This relationship is useful for multinational corporations or business franchises that require consolidated reporting and visibility into interconnected entities. It enhances organizational structure management, allowing sales teams to navigate complex account relationships effectively.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "BillingStreet",
        "Column Description": "The BillingStreet field stores the street address for the account\u0092s billing location. It is part of the broader billing address information, essential for invoicing, taxation, and financial reporting. Ensuring accurate billing addresses helps businesses minimize payment processing issues and maintain compliance with financial regulations.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "BillingCity",
        "Column Description": "The BillingCity column records the city associated with the billing address. It is often used in address validation, taxation calculations, and regional reporting. Businesses leverage this field to analyze revenue distribution across different geographical areas and optimize location-specific sales strategies.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "BillingState",
        "Column Description": "The BillingState field captures the state or province of the billing address. This information is critical for tax jurisdiction compliance, shipping logistics, and regional business analysis. Many organizations use this field to segment customers based on their geographical location for marketing and service optimization.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "BillingPostalCode",
        "Column Description": "The BillingPostalCode column contains the ZIP or postal code for the billing address. It is an essential element for ensuring correct mail delivery, taxation purposes, and customer segmentation. Accurate postal code data enhances geolocation-based analytics and streamlines operational processes like territory assignment.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "BillingCountry",
        "Column Description": "The BillingCountry field specifies the country associated with the billing address. This is a crucial attribute for international businesses managing multi-regional accounts, tax compliance, and global sales reporting. It also plays a key role in determining currency preferences and regulatory requirements.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "BillingLatitude",
        "Column Description": "The BillingLatitude field stores the geographic latitude coordinate of the billing address. This field, when used in conjunction with longitude, enables businesses to leverage location-based services, route optimization, and territory mapping for field sales representatives. It is particularly useful for analytics and market expansion strategies.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "BillingLongitude",
        "Column Description": "The BillingLongitude field captures the geographic longitude coordinate of the billing address. Like BillingLatitude, this field facilitates geospatial analysis, mapping, and logistics planning. Businesses can use this data for proximity-based customer segmentation and service deployment.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "BillingGeocodeAccuracy",
        "Column Description": "The BillingGeocodeAccuracy field indicates the precision level of the geocoded billing address, such as \"Exact,\" \"Street Level,\" or \"City Level.\" It helps businesses assess the reliability of location data for various applications, including targeted marketing campaigns and service coverage planning.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "BillingAddress",
        "Column Description": "The BillingAddress column is a compound field that aggregates all billing address components, including street, city, state, postal code, and country. It provides a standardized format for address management and geolocation services. This field simplifies integrations with external mapping tools and customer address verification systems.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "ShippingStreet",
        "Column Description": "The ShippingStreet field stores the street address used for shipping products or services to the account. It is crucial for logistics, ensuring that deliveries reach the correct location. Businesses rely on this field for order fulfillment and supply chain efficiency.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "ShippingCity",
        "Column Description": "The ShippingCity column holds the city of the shipping address, which is used for delivery logistics and regional distribution planning. It aids in determining shipping costs, transit times, and operational strategies for managing shipments effectively",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "ShippingState",
        "Column Description": "The ShippingState field records the state or province of the shipping address. This information is vital for regional shipping compliance, determining shipping rates, and ensuring timely deliveries. It is commonly used in logistics management to streamline distribution processes.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "ShippingPostalCode",
        "Column Description": "The ShippingPostalCode field contains the ZIP or postal code of the shipping address. It is an essential component for calculating shipping rates, tracking deliveries, and ensuring accuracy in logistics. Businesses leverage this field for efficient order processing and customer service reliability.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "ShippingCountry",
        "Column Description": "The ShippingCountry column specifies the country associated with the shipping address of the account. This field is essential for international shipping, customs documentation, and regulatory compliance. Businesses use this field to segment customers geographically and calculate region-specific shipping costs and delivery times.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "ShippingLatitude",
        "Column Description": "The ShippingLatitude column stores the latitude coordinate of the shipping address. It is primarily used for geolocation-based applications, including route optimization, territory planning, and delivery tracking. This data helps logistics teams improve shipping efficiency and enables businesses to analyze customer distribution geographically.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "ShippingLongitude",
        "Column Description": "The ShippingLongitude field records the longitude coordinate of the shipping address. When combined with ShippingLatitude, it allows businesses to plot customer locations on a map, optimize delivery routes, and provide location-based services. It also supports real-time tracking for shipments.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "ShippingGeocodeAccuracy",
        "Column Description": "The ShippingGeocodeAccuracy column indicates the level of precision of the geocoded shipping address, such as \"Exact,\" \"Street Level,\" or \"City Level.\" This information is valuable for logistics and delivery operations, ensuring that businesses can rely on accurate location data for efficient dispatching and distribution.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "ShippingAddress",
        "Column Description": "The ShippingAddress column is a compound field that consolidates all components of the shipping address, including street, city, state, postal code, and country. This structured format simplifies address management, ensuring data consistency across integrations with external logistics and mapping services.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "Phone",
        "Column Description": "The Phone column stores the primary business phone number associated with the account. It is a critical field for customer support, sales outreach, and account management. Keeping this data accurate ensures smooth communication between the business and its clients.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "Fax",
        "Column Description": "The Fax column contains the fax number of the account, which is used for document transmission. While fax usage has declined with digital alternatives, some industries (such as healthcare and legal) still rely on fax for secure document exchange.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "AccountNumber",
        "Column Description": "The AccountNumber field holds a unique identifier assigned to the account for internal tracking and financial transactions. It is often used for invoicing, order management, and account reconciliation in enterprise systems.\n",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "Website",
        "Column Description": "The Website column records the official website URL of the account. This field is useful for marketing, sales research, and integrations with external analytics tools. Companies leverage this data to gather insights about a business, analyze web presence, and automate lead generation.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "PhotoUrl",
        "Column Description": "The PhotoUrl field stores the URL of the account\u0092s logo or profile picture. This enhances the visual representation of accounts in Salesforce dashboards and reports. Businesses use this for branding, making CRM interfaces more engaging and informative.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "Sic",
        "Column Description": "The Sic column contains the SIC code, which classifies the account\u0092s industry sector. This field is crucial for industry analysis, benchmarking, and targeted sales strategies. Companies use SIC codes to segment accounts by industry and analyze market trends.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "Industry",
        "Column Description": "The Industry column specifies the industry in which the account operates, such as \"Technology,\" \"Healthcare,\" or \"Retail.\" This classification is valuable for lead generation, industry-specific marketing campaigns, and performance benchmarking against competitors.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "AnnualRevenue",
        "Column Description": "The AnnualRevenue column records the estimated yearly revenue of the account. This financial metric is used for segmentation, prioritizing high-value clients, and forecasting business growth. Sales teams often leverage this field to tailor engagement strategies for different revenue tiers.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "NumberOfEmployees",
        "Column Description": "The NumberOfEmployees column captures the total number of employees working in the organization. It helps in determining the company\u0092s size and potential business opportunities. This field is useful for enterprise sales, staffing solutions, and market segmentation.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "Ownership",
        "Column Description": "The Ownership field indicates the ownership structure of the company, such as \"Public,\" \"Private,\" \"Government,\" or \"Non-Profit.\" This classification helps businesses understand organizational governance and regulatory requirements, aiding in risk assessment and partnership decisions.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "TickerSymbol",
        "Column Description": "The TickerSymbol column holds the stock ticker symbol of publicly traded accounts. This field is particularly useful for tracking financial performance, investment opportunities, and market trends related to corporate clients.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "Description",
        "Column Description": "The Description column contains a free-text field where users can enter additional information about the account. It is often used to capture key business details, customer preferences, or historical interactions. This field is crucial for sales and customer service teams to retain context about an account\u0092s background.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "Rating",
        "Column Description": "The Rating field provides a qualitative assessment of the account, such as \"Hot,\" \"Warm,\" or \"Cold.\" It helps sales teams prioritize leads and focus on high-potential opportunities. This field is often used in pipeline management to gauge interest and likelihood of conversion.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "Site",
        "Column Description": "The Site column represents a specific location or branch of the account. This is useful for organizations with multiple locations, such as retail chains, franchises, or corporate offices. Businesses leverage this field to manage site-specific interactions and services.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "OwnerId",
        "Column Description": "The OwnerId column stores the ID of the Salesforce user who owns or manages the account. This is critical for assigning responsibility, tracking account interactions, and ensuring accountability within the sales team. Ownership data is frequently used for workload distribution and performance evaluation.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "CreatedDate",
        "Column Description": "The CreatedDate column stores the timestamp when the account record was first created in Salesforce. This field is automatically populated by the system and is useful for tracking when an account was onboarded, performing historical data analysis, and identifying newly added customers for reporting and automation.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "CreatedById",
        "Column Description": "The CreatedById column contains the unique identifier of the Salesforce user who created the account. This field helps in tracking ownership and accountability for data entry. Businesses use it for auditing purposes and understanding who introduced the account into the CRM.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "LastModifiedDate",
        "Column Description": "The LastModifiedDate field records the timestamp of the most recent update made to the account. It is critical for tracking changes, identifying recently updated records, and ensuring that the latest information is available for reporting and decision-making.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "LastModifiedById",
        "Column Description": "The LastModifiedById column captures the ID of the Salesforce user who last modified the account record. This field is crucial for audit trails, compliance, and accountability, helping teams track who made recent updates and ensuring proper data governance.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "SystemModstamp",
        "Column Description": "The SystemModstamp column is a system-generated timestamp that updates whenever the record undergoes any modification, including system-triggered updates. Unlike LastModifiedDate, it captures changes made by automated processes, workflows, or data integrations, making it valuable for sync operations and external data processing.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "LastActivityDate",
        "Column Description": "The LastActivityDate column stores the date of the last completed activity (such as an email, call, task, or event) related to the account. This field is useful for tracking engagement, identifying inactive accounts, and prioritizing follow-ups to maintain customer relationships.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "LastViewedDate",
        "Column Description": "The LastViewedDate field records the last time a user viewed the account record. This helps in understanding which accounts are actively being referenced by the sales or support teams. It is useful for tracking account engagement trends within the CRM.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "LastReferencedDate",
        "Column Description": "The LastReferencedDate column tracks the most recent instance when the account was accessed through related objects, reports, or dashboards. It provides insights into how frequently an account is being interacted with indirectly, such as through opportunities or cases.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "Jigsaw",
        "Column Description": "The Jigsaw column previously stored the Jigsaw (now Data.com) identifier for the account. This field was used to link Salesforce records with Jigsaw\u0092s business directory for data enrichment. Since Data.com was retired, this field is no longer actively used.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "JigsawCompanyId",
        "Column Description": "Similar to Jigsaw, the JigsawCompanyId field contained the unique company identifier from Jigsaw/Data.com. It was primarily used for business verification and contact enrichment but is now deprecated.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "CleanStatus",
        "Column Description": "The CleanStatus field indicates whether the account data has been verified, updated, or flagged as outdated. Possible values include \u0093Matched,\u0094 \u0093Different,\u0094 \u0093In Sync,\u0094 or \u0093Not Found,\u0094 depending on whether the account\u0092s details align with external data sources like Dun & Bradstreet. This field is crucial for maintaining accurate and up-to-date CRM records.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "AccountSource",
        "Column Description": "The AccountSource column captures the origin of the account, such as \"Web,\" \"Referral,\" \"Trade Show,\" or \"Partner.\" It is valuable for tracking lead sources, assessing marketing campaign effectiveness, and optimizing customer acquisition strategies.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "DunsNumber",
        "Column Description": "The DunsNumber column stores the unique nine-digit identifier assigned by Dun & Bradstreet (D&B) to business entities. This number is widely used for credit reporting, business verification, and corporate data management. It helps in linking Salesforce records with external financial and business intelligence databases.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "Tradestyle",
        "Column Description": "The Tradestyle field holds the trade name or \"doing business as\" (DBA) name of the account. It is useful for distinguishing businesses that operate under different names than their legal entity names, improving clarity in customer interactions and reporting.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "NaicsCode",
        "Column Description": "The NaicsCode column contains the industry classification code assigned to the account based on NAICS standards. It helps businesses segment accounts by industry, analyze market trends, and develop industry-specific sales strategies.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "NaicsDesc",
        "Column Description": "The NaicsDesc column provides a textual description of the NAICS industry classification. This field gives additional context about the industry in which the account operates, supporting better sales targeting and industry analysis.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "YearStarted",
        "Column Description": "The YearStarted column records the year when the business was established. This information helps in understanding business maturity, assessing financial stability, and tailoring engagement strategies for startups versus long-established companies.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "SicDesc",
        "Column Description": "The SicDesc column provides the textual description of the SIC code assigned to the account. It complements the SIC code by offering a more readable industry classification, assisting sales and marketing teams in industry-based segmentation.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "DandbCompanyId",
        "Column Description": "The DandbCompanyId column stores the unique identifier assigned by Dun & Bradstreet to a company. This ID is crucial for integrating Salesforce with D&B\u0092s business intelligence data, enabling risk assessment, credit scoring, and market research.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "OperatingHoursId",
        "Column Description": "The OperatingHoursId column links the account to a predefined set of operating hours in Salesforce. This field is useful for businesses that manage support or service contracts based on specific time zones and business hours, ensuring accurate scheduling and SLA adherence.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "CustomerPriority__c",
        "Column Description": "The CustomerPriority__c column is a custom field typically used to classify accounts based on their priority level, such as \"High,\" \"Medium,\" or \"Low.\" Businesses use this field to prioritize customer interactions, allocate resources efficiently, and tailor service levels based on customer importance.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "SLA__c",
        "Column Description": "The SLA__c column represents the level of service commitment assigned to the account, such as \"Gold,\" \"Silver,\" or \"Bronze.\" This field helps businesses manage customer expectations, define support response times, and ensure compliance with contractual service agreements. It is essential for prioritizing customer support requests based on SLA tiers.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "Active__c",
        "Column Description": "The Active__c column is a boolean field (typically \"True\" or \"False\" OR \"Yes\" or \"No\") indicating whether the account is currently active. This field is useful for filtering operational accounts, identifying inactive customers for re-engagement, and managing account lifecycle statuses.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "NumberofLocations__c",
        "Column Description": "The NumberofLocations__c column captures the total number of physical locations or branches associated with the account. It helps in understanding business scale, planning multi-site service operations, and assessing potential revenue opportunities.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "UpsellOpportunity__c",
        "Column Description": "The UpsellOpportunity__c column identifies whether there is a potential upsell opportunity for the account, often categorized as \"Yes,\" \"No,\" or \"Maybe.\" This field is crucial for sales teams to target existing customers for additional products or services, enhancing revenue growth and customer retention strategies.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "SLASerialNumber__c",
        "Column Description": "The SLASerialNumber__c column stores a unique identifier or serial number assigned to the Service-Level Agreement (SLA) associated with the account. This field is valuable for contract tracking, SLA compliance verification, and support case escalation processes.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_accounts",
        "Table Description": "The salesforce_accounts table represents company accounts within Salesforce. It stores detailed information about each account, including its identification details, hierarchy, location, and geospatial data. This table is commonly used in Customer Relationship Management (CRM) to track businesses and organizations that a company interacts with.",
        "Column Name": "SLAExpirationDate__c",
        "Column Description": "The SLAExpirationDate__c column holds the expiration date of the SLA agreement for the account. It is critical for ensuring timely renewals, maintaining continuous support coverage, and preventing service disruptions for key customers.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "attributes",
        "Column Description": "This field stores metadata related to the record, including its type and URL reference within the Salesforce API. It helps applications interact with Salesforce data programmatically.",
        "Type": "text"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "Id",
        "Column Description": "The primary key of the contact record, uniquely identifying each contact within Salesforce. It is a system-generated 18-character Salesforce ID, crucial for linking contacts with related records in other tables (e.g., accounts, opportunities).",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "IsDeleted",
        "Column Description": "A boolean flag (TRUE/FALSE) that indicates whether the contact has been deleted. If TRUE, the record is in the Salesforce Recycle Bin and can be restored or permanently deleted based on retention policies.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "MasterRecordId",
        "Column Description": "If a duplicate contact record is merged with another, this field stores the ID of the master record that remains after the merge. This helps in deduplication and data integrity.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "AccountId",
        "Column Description": "This column holds the ID of the related account, linking the contact to a specific company or organization in the salesforce_accounts table. It is critical for managing business-to-business (B2B) relationships and tracking all contacts associated with an account.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "LastName",
        "Column Description": "Stores the last name (surname) of the contact, which is a mandatory field in Salesforce. It is commonly used for sorting and searching contact records.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "FirstName",
        "Column Description": "Stores the first name of the contact. This field is optional but useful for personalized communication and segmentation in marketing campaigns.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "Salutation",
        "Column Description": "Stores honorific titles (e.g., \"Mr.\", \"Ms.\", \"Dr.\") associated with the contact. This enhances personalization in formal communication.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "Name",
        "Column Description": "A concatenated field that automatically combines Salutation, FirstName, and LastName into a full name (e.g., \"Dr. John Smith\"). It simplifies reporting and display in UI components.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "OtherStreet",
        "Column Description": "Stores the street address of an alternative location for the contact, such as a secondary office or home address.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "OtherCity",
        "Column Description": "Stores the city for the alternative address.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "OtherState",
        "Column Description": "Stores the state or province for the alternative address.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "OtherPostalCode",
        "Column Description": "Stores the postal or ZIP code for the alternative address.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "OtherCountry",
        "Column Description": "Stores the country of the alternative address.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "OtherLatitude",
        "Column Description": "Stores the latitude coordinate of the alternative address, useful for geolocation-based analytics and mapping.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "OtherLongitude",
        "Column Description": "Stores the longitude coordinate of the alternative address, complementing OtherLatitude for precise geospatial tracking.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "OtherGeocodeAccuracy",
        "Column Description": "Indicates the accuracy level of the geolocation data (e.g., rooftop, postal code level). It helps determine how precisely the latitude and longitude match the actual location.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "OtherAddress",
        "Column Description": "A compound field that combines OtherStreet, OtherCity, OtherState, OtherPostalCode, and OtherCountry into a single structured address field for easier display and reporting.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "MailingStreet",
        "Column Description": "Stores the primary street address for the contact. This is typically the main location where the contact receives correspondence.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "MailingCity",
        "Column Description": "Stores the city for the primary mailing address.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "MailingState",
        "Column Description": "This column contains the state or province of the contact's primary mailing address. It helps categorize contacts based on geographical regions, assisting in territory-based sales, marketing campaigns, and tax jurisdiction assignments.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "MailingPostalCode",
        "Column Description": "Stores the ZIP code or postal code of the contact\u0092s mailing address. It is useful for postal deliveries, location-based analytics, and demographic targeting.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "MailingCountry",
        "Column Description": "This field contains the country associated with the contact\u0092s mailing address. It plays a crucial role in international communication, compliance with regional regulations, and cross-border business operations.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "MailingLatitude",
        "Column Description": "Stores the latitude coordinate of the primary mailing address. It enables geospatial analytics, territory mapping, and location-based insights.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "MailingLongitude",
        "Column Description": "Stores the longitude coordinate of the primary mailing address. It works in conjunction with MailingLatitude for mapping and location-based marketing.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "MailingGeocodeAccuracy",
        "Column Description": "Indicates the accuracy level of the geolocation data (e.g., rooftop, postal code level). It helps businesses assess location precision for mapping and logistics.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "MailingAddress",
        "Column Description": "A compound field that combines MailingStreet, MailingCity, MailingState, MailingPostalCode, and MailingCountry into a single structured address. This field simplifies reporting and API integrations.",
        "Type": "text"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "Phone",
        "Column Description": "Stores the main business phone number of the contact. It is the default point of contact for sales, customer support, and business communication.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "Fax",
        "Column Description": "Stores the fax number associated with the contact. Although fax usage has declined, some industries (e.g., healthcare, legal) still rely on it for document transmission.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "MobilePhone",
        "Column Description": "Stores the mobile phone number of the contact. It is essential for direct and urgent communication, especially for sales follow-ups and SMS marketing.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "HomePhone",
        "Column Description": "Stores the home phone number of the contact. This field is typically used in B2C (business-to-consumer) relationships, where personal contact details are required.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "OtherPhone",
        "Column Description": "Stores an alternative phone number for the contact. This could be another business line or a secondary personal number, useful for backup communication.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "AssistantPhone",
        "Column Description": "Stores the phone number of the contact\u0092s assistant. This field is beneficial when reaching out to high-level executives who delegate scheduling and communication to their assistants.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "ReportsToId",
        "Column Description": "Stores the Salesforce Contact ID of the person to whom this contact reports. It helps businesses map organizational hierarchies, reporting structures, and relationship management.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "Email",
        "Column Description": "Stores the contact\u0092s primary email address. This is the main channel for email marketing, communication, and transactional notifications.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "Title",
        "Column Description": "Stores the contact\u0092s job title, such as \"CEO,\" \"Marketing Manager,\" or \"Sales Associate.\" This field helps sales teams identify decision-makers and key stakeholders.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "Department",
        "Column Description": "Stores the department to which the contact belongs, such as \"Finance,\" \"IT,\" or \"HR.\" It helps businesses segment contacts based on their roles and tailor communication accordingly.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "AssistantName",
        "Column Description": "Stores the name of the contact\u0092s assistant. This field is useful when scheduling meetings or contacting executives who delegate calls and emails to assistants.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "LeadSource",
        "Column Description": "Stores the source from which the contact was acquired, such as \"Website,\" \"Referral,\" \"Trade Show,\" or \"Advertisement.\" This field is crucial for measuring marketing effectiveness and tracking lead generation channels.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "Birthdate",
        "Column Description": "Stores the birthdate of the contact, typically formatted as YYYY-MM-DD. This field is valuable for customer engagement strategies, birthday campaigns, and loyalty programs.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "Description",
        "Column Description": "This column stores additional notes or a brief summary about the contact. It can include details such as communication history, special preferences, or customer insights. It is useful for sales teams, customer support agents, and marketing teams to maintain contextual information.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "OwnerId",
        "Column Description": "Stores the Salesforce User ID or Queue ID of the person or team responsible for the contact. Ownership determines who can view, edit, or manage the contact record based on Salesforce sharing rules and permissions.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "CreatedDate",
        "Column Description": "This system-generated timestamp stores the exact date and time the contact record was created. It helps track data entry patterns, user activity, and record freshness.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "CreatedById",
        "Column Description": "Stores the Salesforce User ID of the person who created the contact record. It is useful for audit trails, accountability, and tracking user contributions.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "LastModifiedDate",
        "Column Description": "Stores the timestamp of the most recent update to the contact record. It is useful for tracking changes, updating reports, and monitoring data freshness.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "LastModifiedById",
        "Column Description": "Stores the Salesforce User ID of the person who last modified the record. This field is useful for audit logs, tracking updates, and monitoring data ownership.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "SystemModstamp",
        "Column Description": "Similar to LastModifiedDate, this timestamp is automatically updated by Salesforce whenever the record is modified. It is primarily used in data synchronization, API integrations, and replication processes to detect changes efficiently.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "LastActivityDate",
        "Column Description": "Stores the most recent date of an activity (such as a logged call, email, or meeting) related to the contact. This helps track engagement, prioritize follow-ups, and monitor customer interactions.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "LastCURequestDate",
        "Column Description": "Stores the timestamp of the last Chatter update request related to this contact. Chatter is Salesforce\u0092s internal social collaboration tool, and this field helps track when users last queried for updates.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "LastCUUpdateDate",
        "Column Description": "Stores the last time the contact\u0092s record was updated through Chatter. It helps track collaboration activity, social interactions, and real-time updates.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "LastViewedDate",
        "Column Description": "Stores the timestamp of when a user last viewed the contact record. It is helpful for tracking user engagement, monitoring CRM usage, and identifying frequently accessed records.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "LastReferencedDate",
        "Column Description": "Stores the timestamp of when the record was last referenced in a related object query. This field helps track indirect engagement with the contact, such as being referenced in reports, dashboards, or workflows.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "EmailBouncedReason",
        "Column Description": "Stores the reason why an email sent to this contact bounced. Common reasons include invalid email addresses, full inboxes, or spam filter rejections. This is crucial for email marketing health and communication strategies.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "EmailBouncedDate",
        "Column Description": "Stores the date and time when an email bounced for this contact. Helps businesses track email deliverability and take corrective actions (e.g., verifying the email address).",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "IsEmailBounced",
        "Column Description": "A TRUE/FALSE field indicating whether an email sent to this contact has bounced. If TRUE, businesses may need to update the email address, reattempt delivery, or remove the contact from email campaigns.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "PhotoUrl",
        "Column Description": "Stores a link to the contact\u0092s profile picture in Salesforce. This can be used for visual identification in UI dashboards, customer profiles, and mobile applications.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "Jigsaw",
        "Column Description": "Previously used to integrate external business data from Jigsaw (now Data.com). This field is no longer in active use.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "JigsawContactId",
        "Column Description": "Previously stored a unique ID for Jigsaw (Data.com) contact records. No longer actively used but may exist in older Salesforce implementations.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "CleanStatus",
        "Column Description": "Indicates the accuracy and validity of the contact\u0092s data compared to external sources (e.g., Data.com). Common statuses include \"Matched,\" \"Different,\" \"Reviewed,\" and \"Inactive.\" Helps organizations maintain clean and reliable contact records.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "IndividualId",
        "Column Description": "Stores the ID of an associated \"Individual\" record, which is used in Salesforce for data privacy regulations like GDPR and CCPA. This field helps businesses manage data consent, right-to-forget requests, and compliance tracking.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "Level__c",
        "Column Description": "A custom field (indicated by __c) that likely stores the priority level or engagement tier of the contact. For example, contacts might be classified as \"Gold,\" \"Silver,\" or \"Bronze\" based on their importance.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_contacts",
        "Table Description": "The salesforce_contacts table stores information about individual contacts associated with business accounts. It helps organizations manage relationships with customers, partners, and other stakeholders. Each record in this table represents a specific person and contains key details such as name, address, account association, and geolocation data. This table plays a critical role in customer relationship management (CRM), enabling businesses to track interactions, segment contacts, and personalize engagement efforts.",
        "Column Name": "Languages__c",
        "Column Description": "A custom field that stores the languages spoken by the contact. This is valuable for multilingual customer support, targeted communication, and localization strategies.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "attributes",
        "Column Description": "The attributes column holds system-generated metadata about each opportunity record, such as the record type and API reference URL. This metadata is used by Salesforce integrations and custom applications to identify the nature of the record and streamline data operations without requiring additional queries. It is essential for developers and system administrators when automating processes or integrating with external systems.",
        "Type": "text"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "Id",
        "Column Description": "Primary Key. The Id column is the unique identifier assigned to each opportunity record. Typically a 15- or 18-character alphanumeric string, it ensures that every opportunity can be distinctly referenced within the Salesforce ecosystem. This identifier is critical for linking the opportunity to related objects, such as accounts, contacts, and products, and for executing precise data operations and integrations.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "IsDeleted",
        "Column Description": "The IsDeleted column is a boolean field that indicates whether the opportunity record has been deleted. When set to TRUE, the record is moved to the Recycle Bin rather than being permanently removed immediately, allowing for potential recovery. This field plays a key role in maintaining data integrity and ensuring that deleted records do not inadvertently affect active reporting or analytics.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "AccountId",
        "Column Description": "The AccountId column stores the identifier of the account associated with the opportunity. This linkage enables a clear connection between the potential deal and the customer or client it is tied to. It is crucial for consolidating sales data, generating comprehensive account-based reports, and understanding customer relationships within the CRM.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "IsPrivate",
        "Column Description": "The IsPrivate column is a boolean indicator that designates whether the opportunity is private. A private opportunity restricts visibility to only certain users or teams, ensuring that sensitive deal information remains confidential. This field is important for maintaining competitive advantage and protecting strategic sales data within the organization.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "Name",
        "Column Description": "The Name column holds the title or name of the opportunity, providing a brief descriptor that summarizes the potential deal. Often including information such as the project name or customer reference, this field is essential for quickly identifying and distinguishing between multiple opportunities. It is heavily used in dashboards, reports, and search functions within Salesforce.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "Description",
        "Column Description": "The Description column is a free-text field that allows sales teams to capture detailed information about the opportunity. This can include background context, key requirements, competitive information, or any other relevant details that might help in understanding the deal\u0092s nuances. It enhances communication across teams and supports strategic decision-making by providing additional context.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "StageName",
        "Column Description": "The StageName column records the current stage of the sales process for the opportunity, such as \u0093Prospecting,\u0094 \u0093Qualification,\u0094 \u0093Proposal,\u0094 or \u0093Negotiation.\u0094 Tracking the stage is vital for forecasting revenue and managing the sales pipeline, as it helps teams understand where each opportunity stands and what actions are required to move it forward.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "Amount",
        "Column Description": "The Amount column represents the monetary value of the opportunity, reflecting the potential revenue if the deal is closed successfully. This field is a key metric for revenue forecasting and prioritizing opportunities, as it directly impacts financial planning and resource allocation within the sales team.",
        "Type": "float"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "Probability",
        "Column Description": "The Probability column captures the estimated likelihood (typically as a percentage) that the opportunity will be successfully closed. This estimation is based on historical data and sales expertise and is used to weight the potential revenue of each opportunity. It assists in refining sales forecasts and helps management assess overall pipeline health.",
        "Type": "float"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "ExpectedRevenue",
        "Column Description": "The ExpectedRevenue column calculates the anticipated revenue from the opportunity by combining the Amount and the Probability (e.g., Amount \u00d7 Probability/100). This field provides a more realistic view of potential earnings, enabling better revenue prediction and more informed business planning.",
        "Type": "float"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "TotalOpportunityQuantity",
        "Column Description": "The TotalOpportunityQuantity column records the total number of units, items, or services included in the opportunity. This field is particularly useful for organizations that sell products or services in quantities, as it allows for detailed analysis of sales volume in addition to the deal\u0092s value.",
        "Type": "float"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "CloseDate",
        "Column Description": "The CloseDate column stores the expected date by which the opportunity is anticipated to be closed, whether won or lost. This field is crucial for pipeline management, helping sales teams schedule follow-ups and forecast when revenue will be realized. It also assists in setting timelines for strategic planning and resource deployment.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "Type",
        "Column Description": "The Type column categorizes the opportunity, distinguishing between various deal types such as new business, existing customer renewal, upsell, or cross-sell. By classifying opportunities, organizations can tailor their sales strategies, marketing efforts, and customer service approaches based on the nature of the opportunity.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "NextStep",
        "Column Description": "The NextStep column is a free-text field that outlines the immediate action required to advance the opportunity. This might include scheduling a meeting, sending a proposal, or following up on a customer query. Defining the next step is essential for keeping the sales process moving forward and ensuring accountability within the sales team.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "LeadSource",
        "Column Description": "The LeadSource column captures the origin of the opportunity, such as referrals, web inquiries, trade shows, or marketing campaigns. Understanding the lead source is vital for measuring the effectiveness of different marketing channels and for refining lead generation strategies to maximize conversion rates.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "IsClosed",
        "Column Description": "The IsClosed column is a boolean field that indicates whether the opportunity has been closed. A closed opportunity means that no further sales activity is expected, as the deal has either been won or lost. This field is important for filtering active deals from historical data and for accurate sales performance reporting.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "IsWon",
        "Column Description": "The IsWon column is a boolean field that specifies whether a closed opportunity was successfully won. This field helps in tracking the success rate of the sales team, contributing to performance analysis and the calculation of key sales metrics such as win rate and overall revenue impact.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "ForecastCategory",
        "Column Description": "The ForecastCategory column categorizes the opportunity based on its likelihood to contribute to sales forecasts. It typically classifies deals into categories such as \u0093Pipeline,\u0094 \u0093Best Case,\u0094 \u0093Committed,\u0094 or \u0093Closed.\u0094 This categorization is fundamental for revenue forecasting, enabling sales leaders to make strategic decisions based on the quality and potential of opportunities in the pipeline.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "ForecastCategoryName",
        "Column Description": "The ForecastCategoryName column provides a descriptive label for the forecast category assigned to the opportunity. This field adds clarity by translating internal forecast codes into understandable terms for sales managers and executives, thereby facilitating more effective communication around pipeline health and revenue projections.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "CampaignId",
        "Column Description": "The CampaignId column links the opportunity to a specific marketing campaign. This association helps in tracking the effectiveness of campaigns in generating revenue and converting leads into deals. It enables marketing and sales teams to analyze which campaigns yield the highest ROI and optimize future marketing strategies.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "HasOpportunityLineItem",
        "Column Description": "A boolean field that indicates whether the opportunity has associated line items (products or services). If TRUE, it means specific items from a price book have been added to the deal. This field is essential for organizations tracking product-level details in their sales pipeline.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "Pricebook2Id",
        "Column Description": "The Pricebook2Id column identifies the price book used for the opportunity. Price books define the list of products and their pricing that applies to the deal. This field is crucial for companies managing multiple pricing strategies across different markets or customer segments.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "OwnerId",
        "Column Description": "The OwnerId column holds the unique identifier of the Salesforce user who owns the opportunity. This is usually a sales representative or account manager. Assigning ownership helps in tracking sales team performance and defining responsibility for closing deals.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "CreatedDate",
        "Column Description": "The CreatedDate column records the exact timestamp when the opportunity record was created. This is useful for tracking deal lifecycles, measuring sales velocity, and analyzing lead conversion time.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "CreatedById",
        "Column Description": "The CreatedById column stores the ID of the user who initially created the opportunity. This helps in identifying who introduced the deal into the system, which is useful for tracking sales reps\u0092 contributions and monitoring data integrity.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "LastModifiedDate",
        "Column Description": "The LastModifiedDate column captures the timestamp of the most recent modification made to the opportunity. It helps in auditing changes and understanding how frequently opportunities are updated.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "LastModifiedById",
        "Column Description": "The LastModifiedById column contains the ID of the user who last modified the opportunity. This helps in maintaining accountability for updates and tracking collaboration on deals.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "SystemModstamp",
        "Column Description": "The SystemModstamp column is an automated timestamp field that updates whenever any system-level change (e.g., automated process or trigger) occurs on the opportunity. It is primarily used for data synchronization and auditing.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "LastActivityDate",
        "Column Description": "The LastActivityDate column records the date of the most recent interaction related to the opportunity, such as emails, calls, or meetings. This field helps sales teams stay engaged by identifying deals that require follow-up.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "PushCount",
        "Column Description": "The PushCount column tracks the number of times an opportunity\u0092s Close Date has been postponed or rescheduled. A high push count can indicate delays or hesitancy in closing deals, helping sales managers identify at-risk opportunities.",
        "Type": "int"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "LastStageChangeDate",
        "Column Description": "The LastStageChangeDate column captures the last time the StageName of the opportunity was modified. This helps in analyzing the time spent in each sales stage and identifying potential bottlenecks in the pipeline.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "FiscalQuarter",
        "Column Description": "The FiscalQuarter column records the fiscal quarter in which the opportunity is expected to close. It aligns sales forecasting with financial reporting, helping finance teams analyze revenue distribution.",
        "Type": "int"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "FiscalYear",
        "Column Description": "The FiscalYear column denotes the fiscal year in which the opportunity is projected to close. This field is essential for long-term revenue forecasting and budget planning.",
        "Type": "int"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "Fiscal",
        "Column Description": "The Fiscal column combines both the fiscal year and fiscal quarter into a single value (e.g., \"FY2025 Q3\"). This format simplifies reporting and revenue tracking based on accounting periods.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "ContactId",
        "Column Description": "The ContactId column links the opportunity to a specific contact in Salesforce, typically the primary decision-maker or point of contact for the deal. This is crucial for managing customer relationships and personalizing sales efforts.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "LastViewedDate",
        "Column Description": "The LastViewedDate column captures the most recent time a user viewed the opportunity record. This helps in understanding engagement levels and tracking active deals.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "LastReferencedDate",
        "Column Description": "The LastReferencedDate column records the last time the opportunity was referenced in a related Salesforce action, such as being included in a report or API call. It helps in understanding which opportunities are being actively used.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "SyncedQuoteId",
        "Column Description": "The SyncedQuoteId column identifies the active quote (if applicable) that is linked to the opportunity. Quotes provide detailed pricing and proposal information for a deal, making this field critical for sales teams managing proposals.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "HasOpenActivity",
        "Column Description": "A boolean field indicating whether the opportunity has any open tasks or activities, such as scheduled follow-ups or pending meetings. This helps sales reps stay on top of pending tasks.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "HasOverdueTask",
        "Column Description": "A boolean field indicating whether any overdue tasks are associated with the opportunity. This serves as a flag for sales reps and managers to take immediate action on deals that may be at risk due to inactivity.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "LastAmountChangedHistoryId",
        "Column Description": "The LastAmountChangedHistoryId column references the most recent historical record of an Amount field change. This helps in tracking pricing adjustments, negotiation trends, and discount strategies.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "LastCloseDateChangedHistoryId",
        "Column Description": "The LastCloseDateChangedHistoryId column references the most recent historical change in the CloseDate field. It provides insight into deal slippage and helps sales managers address delays.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "DeliveryInstallationStatus__c",
        "Column Description": "A custom field tracking the delivery or installation status of products/services related to the opportunity. This is essential for post-sale logistics, ensuring smooth implementation and customer satisfaction.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "TrackingNumber__c",
        "Column Description": "A custom field that may store a shipment tracking number related to the opportunity, particularly for deals involving physical product delivery. It helps in tracking order fulfillment and logistics.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "OrderNumber__c",
        "Column Description": "This custom field holds the sales order number associated with the opportunity. It provides a link between the sales pipeline and order management system, ensuring accurate fulfillment and invoicing.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "CurrentGenerators__c",
        "Column Description": "A custom field that records information about the products or services the customer currently uses from competitors or internal solutions. This helps sales teams tailor their pitch by identifying areas for improvement or differentiation.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_opportunities",
        "Table Description": "The salesforce_opportunities table (often referred to as the Opportunities table in Salesforce) is central to managing and tracking potential revenue-generating deals within an organization. This table stores critical data about each sales opportunity, from its initial identification to its eventual closure, whether won or lost. It supports the sales process by providing visibility into key metrics such as deal value, sales stages, and forecast data, enabling sales teams and management to prioritize opportunities, predict revenue, and strategize for business growth.",
        "Column Name": "MainCompetitors__c",
        "Column Description": "A custom field capturing the primary competitors associated with the opportunity. Tracking competitor involvement allows sales teams to refine their strategies and address objections effectively",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_products",
        "Table Description": "The salesforce_products table (also known as Products in Salesforce) contains information about the products and services a company sells. These products can be associated with opportunities, quotes, and orders to track sales and revenue. This table is crucial for product catalog management, pricing strategies, and sales pipeline integration. It helps sales teams select the right products for deals, manage inventory, track product performance, and generate accurate sales forecasts.",
        "Column Name": "attributes",
        "Column Description": "The attributes column contains metadata about the product record, primarily used in API responses. It provides essential details such as the object reference, API URLs, and record type information, ensuring efficient interaction with Salesforce's data architecture. This metadata helps in retrieving, updating, or linking product records dynamically.",
        "Type": "text"
    },
    {
        "Table Name": "salesforce_products",
        "Table Description": "The salesforce_products table (also known as Products in Salesforce) contains information about the products and services a company sells. These products can be associated with opportunities, quotes, and orders to track sales and revenue. This table is crucial for product catalog management, pricing strategies, and sales pipeline integration. It helps sales teams select the right products for deals, manage inventory, track product performance, and generate accurate sales forecasts.",
        "Column Name": "Id\u00e6",
        "Column Description": "The Id column is a unique system-generated identifier assigned to each product record. It serves as the primary key, ensuring that each product can be uniquely referenced across different Salesforce objects, including opportunities, price books, and orders. This ID is crucial for data integrity and system-wide consistency.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_products",
        "Table Description": "The salesforce_products table (also known as Products in Salesforce) contains information about the products and services a company sells. These products can be associated with opportunities, quotes, and orders to track sales and revenue. This table is crucial for product catalog management, pricing strategies, and sales pipeline integration. It helps sales teams select the right products for deals, manage inventory, track product performance, and generate accurate sales forecasts.",
        "Column Name": "Name",
        "Column Description": "The Name column stores the name of the product, making it the primary identifier for sales teams and customers. A well-defined product name ensures easy recognition and selection within the Salesforce ecosystem. For instance, a product might be named \"Enterprise CRM Software\" or \"Premium Support Package,\" helping teams quickly locate the correct offering.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_products",
        "Table Description": "The salesforce_products table (also known as Products in Salesforce) contains information about the products and services a company sells. These products can be associated with opportunities, quotes, and orders to track sales and revenue. This table is crucial for product catalog management, pricing strategies, and sales pipeline integration. It helps sales teams select the right products for deals, manage inventory, track product performance, and generate accurate sales forecasts.",
        "Column Name": "ProductCode",
        "Column Description": "The ProductCode column contains a unique product identifier, often referred to as a Stock Keeping Unit (SKU) or internal product code. It is vital for tracking inventory, managing sales reports, and streamlining order processing. For example, a product may have a code like \"CRM-001\" or \"SUP-100,\" distinguishing it from similar offerings within the system.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_products",
        "Table Description": "The salesforce_products table (also known as Products in Salesforce) contains information about the products and services a company sells. These products can be associated with opportunities, quotes, and orders to track sales and revenue. This table is crucial for product catalog management, pricing strategies, and sales pipeline integration. It helps sales teams select the right products for deals, manage inventory, track product performance, and generate accurate sales forecasts.",
        "Column Name": "Description",
        "Column Description": "The Description column provides detailed information about the product, including its features, specifications, and key selling points. This description is often used in sales proposals, product catalogs, and customer communications, helping sales teams convey product value effectively.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_products",
        "Table Description": "The salesforce_products table (also known as Products in Salesforce) contains information about the products and services a company sells. These products can be associated with opportunities, quotes, and orders to track sales and revenue. This table is crucial for product catalog management, pricing strategies, and sales pipeline integration. It helps sales teams select the right products for deals, manage inventory, track product performance, and generate accurate sales forecasts.",
        "Column Name": "IsActive",
        "Column Description": "The IsActive column is a boolean field that determines whether the product is currently available for selection in sales transactions. If set to TRUE, the product can be used in opportunities and quotes; if FALSE, it is inactive and unavailable for new transactions. This feature helps in managing product availability without deleting historical records.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_products",
        "Table Description": "The salesforce_products table (also known as Products in Salesforce) contains information about the products and services a company sells. These products can be associated with opportunities, quotes, and orders to track sales and revenue. This table is crucial for product catalog management, pricing strategies, and sales pipeline integration. It helps sales teams select the right products for deals, manage inventory, track product performance, and generate accurate sales forecasts.",
        "Column Name": "CreatedDate",
        "Column Description": "The CreatedDate column captures the exact timestamp when the product record was first created in Salesforce. This field is essential for tracking when a product was introduced into the system, supporting reporting and compliance requirements.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_products",
        "Table Description": "The salesforce_products table (also known as Products in Salesforce) contains information about the products and services a company sells. These products can be associated with opportunities, quotes, and orders to track sales and revenue. This table is crucial for product catalog management, pricing strategies, and sales pipeline integration. It helps sales teams select the right products for deals, manage inventory, track product performance, and generate accurate sales forecasts.",
        "Column Name": "CreatedById",
        "Column Description": "The CreatedById column identifies the Salesforce user who initially created the product record. This information is useful for auditing changes and tracking user contributions to the product catalog.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_products",
        "Table Description": "The salesforce_products table (also known as Products in Salesforce) contains information about the products and services a company sells. These products can be associated with opportunities, quotes, and orders to track sales and revenue. This table is crucial for product catalog management, pricing strategies, and sales pipeline integration. It helps sales teams select the right products for deals, manage inventory, track product performance, and generate accurate sales forecasts.",
        "Column Name": "LastModifiedDate",
        "Column Description": "The LastModifiedDate column stores the timestamp of the most recent modification made to the product record. It helps teams track updates and maintain version control over product details, ensuring that the latest information is always available.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_products",
        "Table Description": "The salesforce_products table (also known as Products in Salesforce) contains information about the products and services a company sells. These products can be associated with opportunities, quotes, and orders to track sales and revenue. This table is crucial for product catalog management, pricing strategies, and sales pipeline integration. It helps sales teams select the right products for deals, manage inventory, track product performance, and generate accurate sales forecasts.",
        "Column Name": "LastModifiedById",
        "Column Description": "The LastModifiedById column records the user ID of the individual who last updated the product record. This field is essential for accountability and auditing, allowing administrators to monitor changes and maintain data accuracy.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_products",
        "Table Description": "The salesforce_products table (also known as Products in Salesforce) contains information about the products and services a company sells. These products can be associated with opportunities, quotes, and orders to track sales and revenue. This table is crucial for product catalog management, pricing strategies, and sales pipeline integration. It helps sales teams select the right products for deals, manage inventory, track product performance, and generate accurate sales forecasts.",
        "Column Name": "SystemModstamp",
        "Column Description": "The SystemModstamp column is a system-generated timestamp that updates whenever any background process or system-level modification occurs on the record. This field is commonly used in synchronization processes and integration scenarios to track record changes efficiently.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_products",
        "Table Description": "The salesforce_products table (also known as Products in Salesforce) contains information about the products and services a company sells. These products can be associated with opportunities, quotes, and orders to track sales and revenue. This table is crucial for product catalog management, pricing strategies, and sales pipeline integration. It helps sales teams select the right products for deals, manage inventory, track product performance, and generate accurate sales forecasts.",
        "Column Name": "Family",
        "Column Description": "The Family column categorizes the product under a broader classification, such as \"Software,\" \"Hardware,\" \"Services,\" or \"Support.\" Grouping products into families helps in better reporting, segmentation, and pricing strategies, enabling organizations to manage their product offerings more effectively.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_products",
        "Table Description": "The salesforce_products table (also known as Products in Salesforce) contains information about the products and services a company sells. These products can be associated with opportunities, quotes, and orders to track sales and revenue. This table is crucial for product catalog management, pricing strategies, and sales pipeline integration. It helps sales teams select the right products for deals, manage inventory, track product performance, and generate accurate sales forecasts.",
        "Column Name": "ExternalDataSourceId",
        "Column Description": "The ExternalDataSourceId column links the product to an external system, such as an ERP or inventory management database. This integration is essential for organizations that manage product data across multiple platforms, ensuring consistency and real-time updates.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_products",
        "Table Description": "The salesforce_products table (also known as Products in Salesforce) contains information about the products and services a company sells. These products can be associated with opportunities, quotes, and orders to track sales and revenue. This table is crucial for product catalog management, pricing strategies, and sales pipeline integration. It helps sales teams select the right products for deals, manage inventory, track product performance, and generate accurate sales forecasts.",
        "Column Name": "ExternalId",
        "Column Description": "The ExternalId column is a custom external identifier that businesses use when integrating Salesforce with third-party systems. It provides a unique reference that ensures seamless data synchronization across multiple platforms.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_products",
        "Table Description": "The salesforce_products table (also known as Products in Salesforce) contains information about the products and services a company sells. These products can be associated with opportunities, quotes, and orders to track sales and revenue. This table is crucial for product catalog management, pricing strategies, and sales pipeline integration. It helps sales teams select the right products for deals, manage inventory, track product performance, and generate accurate sales forecasts.",
        "Column Name": "DisplayUrl",
        "Column Description": "The DisplayUrl column contains a web link associated with the product, often pointing to an image, a product information page, or an e-commerce listing. This URL is useful for sales presentations, digital catalogs, and external integrations.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_products",
        "Table Description": "The salesforce_products table (also known as Products in Salesforce) contains information about the products and services a company sells. These products can be associated with opportunities, quotes, and orders to track sales and revenue. This table is crucial for product catalog management, pricing strategies, and sales pipeline integration. It helps sales teams select the right products for deals, manage inventory, track product performance, and generate accurate sales forecasts.",
        "Column Name": "QuantityUnitOfMeasure",
        "Column Description": "The QuantityUnitOfMeasure column defines the unit of measurement for the product, such as \"Each,\" \"Hour,\" or \"Bundle.\" This information is critical for inventory management, pricing strategies, and accurate order processing, ensuring that the correct unit is applied to each sale.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_products",
        "Table Description": "The salesforce_products table (also known as Products in Salesforce) contains information about the products and services a company sells. These products can be associated with opportunities, quotes, and orders to track sales and revenue. This table is crucial for product catalog management, pricing strategies, and sales pipeline integration. It helps sales teams select the right products for deals, manage inventory, track product performance, and generate accurate sales forecasts.",
        "Column Name": "IsDeleted",
        "Column Description": "The IsDeleted column is a boolean flag that indicates whether the product has been deleted. If set to TRUE, the product record has been soft-deleted and resides in the Salesforce Recycle Bin. This feature helps in data recovery and record management without permanent deletion.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_products",
        "Table Description": "The salesforce_products table (also known as Products in Salesforce) contains information about the products and services a company sells. These products can be associated with opportunities, quotes, and orders to track sales and revenue. This table is crucial for product catalog management, pricing strategies, and sales pipeline integration. It helps sales teams select the right products for deals, manage inventory, track product performance, and generate accurate sales forecasts.",
        "Column Name": "IsArchived",
        "Column Description": "The IsArchived column determines whether the product is archived, meaning it is no longer actively sold but remains in the system for historical reference. Archiving is useful for retiring old products while maintaining access to past records for reporting purposes.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_products",
        "Table Description": "The salesforce_products table (also known as Products in Salesforce) contains information about the products and services a company sells. These products can be associated with opportunities, quotes, and orders to track sales and revenue. This table is crucial for product catalog management, pricing strategies, and sales pipeline integration. It helps sales teams select the right products for deals, manage inventory, track product performance, and generate accurate sales forecasts.",
        "Column Name": "LastViewedDate",
        "Column Description": "The LastViewedDate column records the most recent date when a user viewed the product record. This field helps track product engagement and monitor which products receive frequent user attention.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_products",
        "Table Description": "The salesforce_products table (also known as Products in Salesforce) contains information about the products and services a company sells. These products can be associated with opportunities, quotes, and orders to track sales and revenue. This table is crucial for product catalog management, pricing strategies, and sales pipeline integration. It helps sales teams select the right products for deals, manage inventory, track product performance, and generate accurate sales forecasts.",
        "Column Name": "LastReferencedDate",
        "Column Description": "The LastReferencedDate column captures the last time the product was referenced in a report, API call, or related record query. This information helps administrators understand product usage trends and identify frequently accessed products.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_products",
        "Table Description": "The salesforce_products table (also known as Products in Salesforce) contains information about the products and services a company sells. These products can be associated with opportunities, quotes, and orders to track sales and revenue. This table is crucial for product catalog management, pricing strategies, and sales pipeline integration. It helps sales teams select the right products for deals, manage inventory, track product performance, and generate accurate sales forecasts.",
        "Column Name": "StockKeepingUnit",
        "Column Description": "The StockKeepingUnit column, often known as SKU, stores a custom product identifier used for inventory tracking. Some businesses define their own SKU structures to streamline warehouse and sales operations.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_products",
        "Table Description": "The salesforce_products table (also known as Products in Salesforce) contains information about the products and services a company sells. These products can be associated with opportunities, quotes, and orders to track sales and revenue. This table is crucial for product catalog management, pricing strategies, and sales pipeline integration. It helps sales teams select the right products for deals, manage inventory, track product performance, and generate accurate sales forecasts.",
        "Column Name": "Type",
        "Column Description": "The Type column specifies the classification of the product, such as \"Physical Goods,\" \"Subscription Service,\" or \"Consulting.\" This distinction helps businesses differentiate product types for sales, accounting, and pricing purposes.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_products",
        "Table Description": "The salesforce_products table (also known as Products in Salesforce) contains information about the products and services a company sells. These products can be associated with opportunities, quotes, and orders to track sales and revenue. This table is crucial for product catalog management, pricing strategies, and sales pipeline integration. It helps sales teams select the right products for deals, manage inventory, track product performance, and generate accurate sales forecasts.",
        "Column Name": "ProductClass",
        "Column Description": "The ProductClass column provides an additional classification layer for products, offering businesses more flexibility in defining product categories. It is particularly useful for organizations that require a more granular product segmentation approach.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "attributes",
        "Column Description": "The attributes column contains metadata about the profile record, primarily used in API responses. This metadata helps identify object references, system-level properties, and endpoint URLs when interacting with Salesforce programmatically. It ensures seamless API integrations and efficient data handling.",
        "Type": "text"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "Id",
        "Column Description": "Primary Key. The Id column is the unique identifier assigned to each profile record. This system-generated ID ensures that each profile can be uniquely referenced across Salesforce. It plays a crucial role in assigning profiles to users and managing access controls within an organization.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "Name",
        "Column Description": "The Name column represents the name of the profile, such as \"System Administrator,\" \"Standard User,\" \"Read-Only User,\" or \"Custom Sales Profile.\" The profile name helps distinguish different access levels assigned to users, ensuring that permissions align with job roles and responsibilities.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsEmailSingle",
        "Column Description": "The PermissionsEmailSingle column determines whether users with this profile can send individual emails from Salesforce. If set to TRUE, users can send single emails through Salesforce\u0092s email functionality, such as sending direct messages to leads, contacts, or opportunities. This permission is useful for sales and customer service teams.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsEmailMass",
        "Column Description": "The PermissionsEmailMass column controls whether users can send mass emails. If enabled, users can send bulk email communications, such as newsletters or promotional campaigns, to multiple contacts at once. This permission is particularly important for marketing and outreach teams.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsEditTask",
        "Column Description": "The PermissionsEditTask column defines whether users can edit tasks. Tasks in Salesforce represent to-do items or follow-ups linked to records like leads, opportunities, and accounts. Allowing users to edit tasks ensures that updates, status changes, and reassignment of responsibilities can be managed effectively.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsEditEvent",
        "Column Description": "The PermissionsEditEvent column specifies whether users can edit calendar events. Events are scheduled activities within Salesforce, such as meetings, calls, or appointments. With this permission, users can modify event details, reschedule meetings, and manage their calendars efficiently.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsExportReport",
        "Column Description": "The PermissionsExportReport column determines whether users can export reports from Salesforce. If enabled, users can download reports in formats such as CSV or Excel, allowing them to analyze data externally. This permission is crucial for data analysts and decision-makers but must be restricted for security-sensitive roles.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsImportPersonal",
        "Column Description": "The PermissionsImportPersonal column allows users to import their personal data, such as contacts, leads, or other records, into Salesforce. This permission is useful for sales representatives and account managers who need to upload client information but should be restricted for roles that do not require direct data imports.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsDataExport",
        "Column Description": "The PermissionsDataExport column provides users the ability to export all Salesforce data, including records, reports, and metadata. This is a high-level administrative permission that should be assigned cautiously, as it grants full data extraction capabilities, which can be a security risk if misused.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageUsers",
        "Column Description": "The PermissionsManageUsers column allows users to create, update, and deactivate user accounts within Salesforce. This permission is typically granted to system administrators and HR personnel, enabling them to manage employee access, assign roles, and configure user settings.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsEditPublicFilters",
        "Column Description": "The PermissionsEditPublicFilters column determines whether users can edit public list views and filters. Public filters help users refine record searches within Salesforce objects like leads, contacts, and opportunities. Allowing edits ensures better collaboration, but unrestricted access could lead to confusion or mismanagement of shared filters.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsEditPublicTemplates",
        "Column Description": "The PermissionsEditPublicTemplates column enables users to modify public email templates. Salesforce email templates help standardize customer communications, such as welcome emails and follow-ups. This permission is vital for marketing and sales teams that require consistent messaging but should be limited to prevent unauthorized modifications.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsModifyAllData",
        "Column Description": "The PermissionsModifyAllData column is one of the most powerful permissions, granting users full access to all data in Salesforce. Users with this permission can view, create, edit, delete, and transfer any record across all objects. This permission is typically reserved for system administrators and should be carefully managed to prevent data loss or security breaches.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsEditBillingInfo",
        "Column Description": "The PermissionsEditBillingInfo column controls whether users can edit billing information within Salesforce. This includes modifying account payment details, subscription plans, and invoice records. Only finance or administrative users should have this permission, as it involves sensitive financial data.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageCases",
        "Column Description": "The PermissionsManageCases column allows users to create, update, and close customer support cases. Cases represent customer service requests in Salesforce Service Cloud, and this permission ensures that support agents can efficiently manage customer issues.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsMassInlineEdit",
        "Column Description": "The PermissionsMassInlineEdit column enables users to make bulk edits to multiple records at once using inline editing. This feature helps users quickly update field values across numerous records, improving efficiency for teams managing large data sets. However, improper use of mass edits could lead to data inconsistencies.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsEditKnowledge",
        "Column Description": "The PermissionsEditKnowledge column grants users the ability to edit articles in the Salesforce Knowledge Base. This is critical for support teams who manage help articles, FAQs, and internal documentation. Restricting this permission ensures that only authorized personnel can modify official knowledge resources.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageKnowledge",
        "Column Description": "The PermissionsManageKnowledge column extends beyond editing and allows users to create, publish, and archive knowledge articles. This permission is typically assigned to content managers, support leads, and administrators responsible for maintaining accurate and up-to-date knowledge bases.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageSolutions",
        "Column Description": "The PermissionsManageSolutions column allows users to manage solutions, which are predefined responses to customer issues. Although Salesforce has largely transitioned from Solutions to Knowledge, this permission is still relevant in organizations using legacy Salesforce implementations.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsCustomizeApplication",
        "Column Description": "The PermissionsCustomizeApplication column grants users the ability to customize and configure Salesforce applications. This permission allows users to modify page layouts, create custom fields, set up automation rules, and manage custom objects. It is typically assigned to administrators and developers responsible for tailoring Salesforce to meet business needs.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsEditReadonlyFields",
        "Column Description": "The PermissionsEditReadonlyFields column allows users to edit fields that are normally read-only, such as system-generated fields or fields locked by validation rules. This permission is crucial for administrators and advanced users who need to override field restrictions for data correction or migration purposes.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsRunReports",
        "Column Description": "The PermissionsRunReports column determines whether users can execute and generate reports in Salesforce. Reports help users analyze data, track performance, and make informed decisions. This permission is commonly granted to managers, analysts, and decision-makers who rely on data insights for strategic planning.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsViewSetup",
        "Column Description": "The PermissionsViewSetup column controls whether users can access the Salesforce Setup menu, which contains system configurations, security settings, and customization options. Users with this permission can view setup-related configurations but cannot necessarily modify them. This is useful for auditors and compliance officers who need visibility into system settings without the ability to change them.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsTransferAnyEntity",
        "Column Description": "The PermissionsTransferAnyEntity column allows users to transfer ownership of any record across all objects, such as accounts, opportunities, leads, and cases. This permission is particularly useful for system administrators and sales managers who need to reassign records due to organizational changes, but it should be carefully managed to prevent unauthorized data transfers.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsNewReportBuilder",
        "Column Description": "The PermissionsNewReportBuilder column enables users to create reports using Salesforce's enhanced Report Builder interface. This feature provides a drag-and-drop experience for building detailed, customized reports. It is essential for business analysts and team leaders who need to generate insights based on real-time data.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsActivateContract",
        "Column Description": "The PermissionsActivateContract column grants users the ability to activate contracts, making them legally binding. This permission is crucial for sales and legal teams that finalize contract agreements with customers. Once a contract is activated, it typically cannot be modified, making this a sensitive permission that should be assigned carefully.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsActivateOrder",
        "Column Description": "The PermissionsActivateOrder column allows users to activate orders, making them ready for fulfillment. This is a critical permission for order management teams, as activating an order confirms that it is approved and ready for processing. Careful management of this permission ensures that orders are not mistakenly activated before necessary approvals.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsImportLeads",
        "Column Description": "The PermissionsImportLeads column enables users to import lead records into Salesforce. This is particularly useful for sales teams that acquire new leads from external sources, such as marketing campaigns or third-party databases. While this permission enhances lead generation efforts, it should be restricted to prevent unauthorized or duplicate lead imports.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageLeads",
        "Column Description": "The PermissionsManageLeads column grants users full control over lead records, allowing them to create, edit, transfer, and delete leads. This permission is commonly assigned to sales managers and lead generation specialists who oversee lead qualification and distribution within the sales pipeline.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsTransferAnyLead",
        "Column Description": "The PermissionsTransferAnyLead column allows users to transfer ownership of any lead to another user. This is particularly useful for sales teams that need to reassign leads due to territory changes or workload balancing. Proper control of this permission ensures that leads are reassigned efficiently while maintaining data integrity.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsViewAllData",
        "Column Description": "The PermissionsViewAllData column provides users with read access to all records in Salesforce, regardless of ownership or sharing rules. This is a highly sensitive permission typically reserved for administrators, compliance officers, or executives who require complete data visibility for oversight and reporting.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsEditPublicDocuments",
        "Column Description": "The PermissionsEditPublicDocuments column enables users to modify public documents stored in Salesforce. Public documents include shared templates, policies, and marketing materials. This permission is essential for content managers and marketing teams, but unauthorized changes could lead to inconsistencies in official documentation.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsViewEncryptedData",
        "Column Description": "The PermissionsViewEncryptedData column allows users to view data that has been encrypted for security purposes. This permission is typically assigned to highly trusted users, such as security administrators or compliance officers, since encrypted data often contains sensitive information such as customer financial details or personally identifiable information (PII).",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsEditBrandTemplates",
        "Column Description": "The PermissionsEditBrandTemplates column grants users the ability to modify branding templates used in emails, reports, and other Salesforce-generated content. This permission is important for marketing and brand management teams who need to ensure consistency in corporate communications.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsEditHtmlTemplates",
        "Column Description": "The PermissionsEditHtmlTemplates column allows users to edit HTML-based email templates. This is valuable for marketing teams that use custom-designed emails for campaigns, ensuring brand alignment and engagement. However, improper changes could result in broken email layouts or incorrect messaging.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsChatterInternalUser",
        "Column Description": "The PermissionsChatterInternalUser column determines whether a user can participate in Salesforce Chatter, an internal collaboration tool. Chatter allows users to post updates, share files, and collaborate with colleagues. This permission is essential for fostering communication within an organization.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageEncryptionKeys",
        "Column Description": "The PermissionsManageEncryptionKeys column grants users control over Salesforce\u0092s encryption keys, which are used to protect sensitive data. This is an extremely sensitive permission that should only be assigned to security administrators, as mishandling encryption keys could compromise data security.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsDeleteActivatedContract",
        "Column Description": "The PermissionsDeleteActivatedContract column allows users to delete contracts that have already been activated. Since activated contracts are legally binding agreements, this permission is rarely granted except to system administrators or legal personnel who need to manage contract exceptions.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsChatterInviteExternalUsers",
        "Column Description": "The PermissionsChatterInviteExternalUsers column enables users to invite external users, such as partners or customers, to participate in Salesforce Chatter discussions. This permission is useful for organizations that collaborate with third-party vendors or clients, but it should be controlled to prevent unauthorized external access.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsSendSitRequests",
        "Column Description": "The PermissionsSendSitRequests column allows users to send Single Instance Tenant (SIT) requests, typically used for requesting site-specific configurations or service requests. This permission is relevant for IT administrators managing Salesforce environments and support teams handling system adjustments.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsApiUserOnly",
        "Column Description": "The PermissionsApiUserOnly column restricts a user to only API access, preventing them from logging into the Salesforce UI. This permission is commonly assigned to system integration users and service accounts that interact with Salesforce through external applications rather than the standard interface.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageRemoteAccess",
        "Column Description": "The PermissionsManageRemoteAccess column enables users to manage OAuth-enabled remote access applications. This permission is critical for controlling third-party applications that integrate with Salesforce, ensuring that external systems can securely authenticate and interact with Salesforce data.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsCanUseNewDashboardBuilder",
        "Column Description": "The PermissionsCanUseNewDashboardBuilder column grants users access to Salesforce's new dashboard builder interface, allowing them to create, customize, and manage dashboards using enhanced visualization tools. This permission is beneficial for analysts and business users who rely on dashboards for real-time data insights.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageCategories",
        "Column Description": "The PermissionsManageCategories column allows users to create, modify, and delete categories for organizing knowledge articles, solutions, and content. This permission is essential for knowledge managers and content administrators responsible for structuring Salesforce's knowledge base and public-facing documentation.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsConvertLeads",
        "Column Description": "The PermissionsConvertLeads column enables users to convert leads into accounts, contacts, and opportunities. This is a key sales function that helps transition potential customers into the sales pipeline. Granting this permission ensures that sales teams can efficiently qualify and manage new business prospects.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsPasswordNeverExpires",
        "Column Description": "The PermissionsPasswordNeverExpires column prevents a user\u0092s password from expiring, overriding standard security policies. This is a high-risk permission that should only be assigned in specific scenarios, such as for API users or system accounts where automated workflows depend on stable authentication credentials.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsUseTeamReassignWizards",
        "Column Description": "The PermissionsUseTeamReassignWizards column allows users to use Salesforce\u0092s Team Reassignment Wizards, which facilitate mass reassignment of team members on accounts and opportunities. This is useful for sales managers overseeing organizational changes or territory adjustments.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsEditActivatedOrders",
        "Column Description": "The PermissionsEditActivatedOrders column grants users the ability to modify orders that have already been activated. Since activated orders are typically locked to prevent changes after approval, this permission is restricted to high-level users such as order managers and finance teams who handle special cases.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsInstallMultiforce",
        "Column Description": "The PermissionsInstallMultiforce column enables users to install MultiForce applications, which are custom or third-party apps deployed within Salesforce. This permission is typically given to system administrators responsible for managing app installations and integrations.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsPublishMultiforce",
        "Column Description": "The PermissionsPublishMultiforce column allows users to publish MultiForce applications, making them available for deployment across the organization. This is crucial for developers and IT admins who build and distribute internal applications within Salesforce.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsChatterOwnGroups",
        "Column Description": "The PermissionsChatterOwnGroups column permits users to create and manage their own Chatter groups within Salesforce\u0092s social collaboration platform. This permission is useful for employees who need to organize discussions, projects, or knowledge-sharing groups within the organization.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsEditOppLineItemUnitPrice",
        "Column Description": "The PermissionsEditOppLineItemUnitPrice column grants users the ability to edit unit prices for opportunity line items. This permission is important for sales teams who negotiate pricing with customers and need flexibility to adjust prices at the product level within opportunities.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsCreateMultiforce",
        "Column Description": "The PermissionsCreateMultiforce column allows users to create MultiForce applications, which are custom applications developed within Salesforce\u0092s platform. This permission is typically reserved for developers and IT personnel responsible for building internal business applications.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsBulkApiHardDelete",
        "Column Description": "The PermissionsBulkApiHardDelete column enables users to permanently delete records using the Bulk API. Unlike standard deletions that send records to the Recycle Bin, hard deletions remove data permanently. This is a highly sensitive permission, usually granted only to administrators handling data purges.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsSolutionImport",
        "Column Description": "The PermissionsSolutionImport column allows users to import solutions into the Salesforce Knowledge Base. This is useful for support teams and knowledge managers who upload troubleshooting guides, FAQs, and best practices into the system.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageCallCenters",
        "Column Description": "The PermissionsManageCallCenters column grants users the ability to configure call center settings, including managing telephony integrations and defining call center users. This is crucial for customer service managers and IT administrators responsible for overseeing call center operations.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageSynonyms",
        "Column Description": "The PermissionsManageSynonyms column enables users to define and manage synonyms for Salesforce search functions. This is useful for optimizing search results within knowledge articles, cases, and records, improving the user experience by allowing related terms to be linked together.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsViewContent",
        "Column Description": "The PermissionsViewContent column allows users to access and view Salesforce content, including documents, files, and media stored in the system. This permission is commonly assigned to employees who need to retrieve shared resources without modifying them.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageEmailClientConfig",
        "Column Description": "The PermissionsManageEmailClientConfig column enables users to configure email client settings, including integration with external email services like Outlook or Gmail. This is a key permission for IT admins and email integration specialists managing company-wide email connectivity.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsEnableNotifications",
        "Column Description": "The PermissionsEnableNotifications column allows users to enable and manage Salesforce notifications. These notifications help keep users informed about important updates, approvals, or system alerts, making this permission useful for managers and team leads who rely on timely information.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageDataIntegrations",
        "Column Description": "The PermissionsManageDataIntegrations column grants users control over Salesforce\u0092s data integration settings, allowing them to manage connections between Salesforce and external databases or applications. This permission is critical for IT teams overseeing system interoperability.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsDistributeFromPersWksp",
        "Column Description": "The PermissionsDistributeFromPersWksp column allows users to distribute content from their personal workspace to shared libraries. This is useful for employees who manage personal drafts or templates before making them available for broader team use.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsViewDataCategories",
        "Column Description": "The PermissionsViewDataCategories column permits users to view data categories, which are used for organizing records in Salesforce Knowledge and other structured content repositories. This permission is essential for users who need read-only access to categorized data.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageDataCategories",
        "Column Description": "The PermissionsManageDataCategories column allows users to create, edit, and delete data categories. This permission is critical for knowledge managers and content administrators who structure and maintain Salesforce\u0092s categorized information.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsAuthorApex",
        "Column Description": "The PermissionsAuthorApex column grants users the ability to write and deploy Apex code, Salesforce\u0092s proprietary programming language. This permission is reserved for developers and technical users responsible for building automation scripts, triggers, and advanced business logic.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageMobile",
        "Column Description": "The PermissionsManageMobile column enables users to configure mobile access settings for Salesforce. This includes managing mobile security policies, app permissions, and user access settings. IT administrators and mobile strategy teams commonly handle this responsibility.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsApiEnabled",
        "Column Description": "The PermissionsApiEnabled column allows users to access Salesforce via API, enabling integration with external applications, automation tools, and data synchronization processes. This permission is crucial for developers and system integrators managing third-party connections.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageCustomReportTypes",
        "Column Description": "The PermissionsManageCustomReportTypes column permits users to create and modify custom report types, allowing organizations to define specific data structures for reporting purposes. This is a key permission for business analysts and report administrators.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsEditCaseComments",
        "Column Description": "The PermissionsEditCaseComments column enables users to edit comments added to Salesforce cases. This is particularly useful for customer support teams that need to clarify or update case notes, ensuring accurate documentation of customer interactions.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsTransferAnyCase",
        "Column Description": "The PermissionsTransferAnyCase column allows users to transfer ownership of any case within the organization, even if they are not the current owner. This is essential for customer support managers and administrators who need to reassign cases for better workload distribution or escalation management.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsContentAdministrator",
        "Column Description": "The PermissionsContentAdministrator column designates a user as a content administrator, giving them the ability to manage content libraries, folders, and documents in Salesforce CRM Content. This is a crucial permission for knowledge managers and content strategists responsible for maintaining structured and accessible information.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsCreateWorkspaces",
        "Column Description": "The PermissionsCreateWorkspaces column enables users to create content workspaces, which are collaborative spaces for storing, managing, and sharing documents. This is useful for teams that require separate repositories for different projects or departments.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageContentPermissions",
        "Column Description": "The PermissionsManageContentPermissions column grants users control over content permissions, allowing them to set access levels for different users and groups. This ensures that sensitive documents and proprietary information are only available to authorized personnel.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageContentProperties",
        "Column Description": "The PermissionsManageContentProperties column allows users to configure metadata properties for content stored in Salesforce. This is critical for organizing and classifying files efficiently, enabling advanced search and retrieval capabilities.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageContentTypes",
        "Column Description": "The PermissionsManageContentTypes column gives users the ability to define and modify content types within Salesforce CRM Content. This is essential for organizations that categorize documents based on type, such as contracts, proposals, and case studies.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageExchangeConfig",
        "Column Description": "The PermissionsManageExchangeConfig column enables users to configure Salesforce\u0092s integration with Microsoft Exchange. This permission is primarily used by IT administrators managing email synchronization and calendar integrations for users.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageAnalyticSnapshots",
        "Column Description": "The PermissionsManageAnalyticSnapshots column allows users to configure and manage analytic snapshots, which are scheduled reports that capture historical data for trend analysis. This is valuable for business analysts who need to track performance metrics over time.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsScheduleReports",
        "Column Description": "The PermissionsScheduleReports column grants users the ability to schedule reports to run at specific times and deliver results via email or dashboards. This is useful for automating recurring analytics and ensuring key stakeholders receive timely data insights.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageBusinessHourHolidays",
        "Column Description": "The PermissionsManageBusinessHourHolidays column gives users control over defining business hours and holiday schedules in Salesforce. This is crucial for customer service teams and support centers that need to ensure accurate response time calculations for SLAs.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageEntitlements",
        "Column Description": "The PermissionsManageEntitlements column allows users to configure and manage entitlement processes, defining service levels and support agreements. This permission is essential for companies that track customer support entitlements based on contracts or service agreements.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageDynamicDashboards",
        "Column Description": "The PermissionsManageDynamicDashboards column enables users to create and manage dynamic dashboards that display data based on the viewer's access level. This is useful for executives and managers who need personalized reports without duplicating dashboard templates.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsCustomSidebarOnAllPages",
        "Column Description": "The PermissionsCustomSidebarOnAllPages column grants users the ability to customize the Salesforce sidebar across all pages. This permission is valuable for administrators who want to implement custom navigation links, widgets, or quick actions for users.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageInteraction",
        "Column Description": "The PermissionsManageInteraction column enables users to configure and manage Salesforce interaction logs, which are used to track customer interactions across multiple channels. This is useful for sales and support teams looking to maintain a complete history of client engagement.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsViewMyTeamsDashboards",
        "Column Description": "The PermissionsViewMyTeamsDashboards column allows users to view dashboards owned by their direct reports or team members. This is beneficial for managers who need visibility into team performance metrics without requiring dashboard ownership.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsModerateChatter",
        "Column Description": "The PermissionsModerateChatter column grants users the ability to moderate Chatter posts and comments, ensuring compliance with company policies. This permission is commonly assigned to HR teams or community managers responsible for internal collaboration guidelines.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsResetPasswords",
        "Column Description": "The PermissionsResetPasswords column enables users to reset passwords for other users within the system. This is an essential administrative function that allows helpdesk and IT teams to assist users who have forgotten their credentials.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsFlowUFLRequired",
        "Column Description": "The PermissionsFlowUFLRequired column ensures that users must provide explicit consent when running flows that update fields. This permission is used to enforce security and compliance measures when automating business processes.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsCanInsertFeedSystemFields",
        "Column Description": "The PermissionsCanInsertFeedSystemFields column allows users to insert system fields into Chatter feed posts, such as timestamps or system-generated values. This is useful for logging automated updates and ensuring complete audit trails in collaboration threads.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsActivitiesAccess",
        "Column Description": "The PermissionsActivitiesAccess column grants users access to Salesforce\u0092s Activities feature, which includes tasks, events, and calendar entries. This permission is crucial for sales and service teams that rely on tracking meetings, calls, and follow-ups.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageKnowledgeImportExport",
        "Column Description": "The PermissionsManageKnowledgeImportExport column enables users to import and export knowledge articles in bulk. This is particularly useful for organizations that migrate content from external knowledge bases or update large sets of articles regularly.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsEmailTemplateManagement",
        "Column Description": "The PermissionsEmailTemplateManagement column allows users to create, edit, and manage email templates. This is essential for marketing and sales teams that rely on standardized messaging for customer communications.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsEmailAdministration",
        "Column Description": "The PermissionsEmailAdministration column grants users administrative control over email settings in Salesforce, including configuring email servers, sending limits, and monitoring email delivery status. This is a key permission for IT administrators managing company-wide email integrations.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageChatterMessages",
        "Column Description": "The PermissionsManageChatterMessages column allows users to monitor and manage private Chatter messages sent between users. This is useful for compliance teams that need to oversee internal communications for security and regulatory reasons.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsAllowEmailIC",
        "Column Description": "The PermissionsAllowEmailIC column enables users to send and receive email from within the Salesforce interface using the email client integration. This permission is useful for sales and service professionals who need to track customer emails without switching applications.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsChatterFileLink",
        "Column Description": "The PermissionsChatterFileLink column grants users the ability to share files in Chatter using links rather than uploading duplicate files. This is useful for teams that collaborate on shared documents and need version control.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsForceTwoFactor",
        "Column Description": "The PermissionsForceTwoFactor column mandates two-factor authentication for users with this permission enabled. This is a critical security setting that enforces an additional layer of protection for sensitive data access.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsViewEventLogFiles",
        "Column Description": "The PermissionsViewEventLogFiles column allows users to access event log files, which record detailed system activities such as logins, API calls, and security events. This permission is essential for security analysts and IT administrators monitoring system usage.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageNetworks",
        "Column Description": "The PermissionsManageNetworks column enables users to configure Salesforce Communities and Experience Cloud settings, allowing them to create, modify, and manage external-facing portals. This is particularly useful for organizations that engage with partners and customers through Salesforce Communities.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageAuthProviders",
        "Column Description": "The PermissionsManageAuthProviders column grants users control over authentication provider settings, allowing them to configure single sign-on (SSO) and OAuth-based integrations. This permission is crucial for IT teams responsible for managing user authentication and identity federation.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsRunFlow",
        "Column Description": "The PermissionsRunFlow column grants users the ability to run automated flows within Salesforce. Flows are essential for automating business processes such as data updates, approvals, or notifications, and this permission ensures users can initiate these flows to improve operational efficiency.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsCreateCustomizeDashboards",
        "Column Description": "The PermissionsCreateCustomizeDashboards column allows users to create and customize dashboards within Salesforce. Dashboards are a key feature for visualizing data and trends, and this permission enables users to create personalized, actionable reports that can enhance decision-making.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsCreateDashboardFolders",
        "Column Description": "The PermissionsCreateDashboardFolders column grants users the ability to create folders to organize dashboards. This is important for administrators or managers who need to structure dashboard access for different teams or business units, ensuring ease of use and effective data organization.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsViewPublicDashboards",
        "Column Description": "The PermissionsViewPublicDashboards column allows users to view dashboards that have been shared publicly within the organization. This permission is valuable for employees who need to access high-level insights or metrics that are made available for broader consumption across teams.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageDashbdsInPubFolders",
        "Column Description": "The PermissionsManageDashbdsInPubFolders column enables users to manage dashboards within public folders. This includes editing, sharing, and organizing dashboards that are meant to be visible to all members of an organization, ensuring better accessibility of key business data.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsCreateCustomizeReports",
        "Column Description": "The PermissionsCreateCustomizeReports column grants users the ability to create and customize reports. This is a crucial feature for sales, service, and operations teams who rely on reporting to track progress, analyze trends, and monitor performance indicators.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsCreateReportFolders",
        "Column Description": "The PermissionsCreateReportFolders column allows users to create folders to organize reports. Similar to dashboard folder creation, this ensures that reports are stored in a structured manner, allowing for easy access and management based on the user\u0092s role or department.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsViewPublicReports",
        "Column Description": "The PermissionsViewPublicReports column gives users the ability to view reports that are shared publicly. This is useful for accessing reports that are meant to be widely distributed or available for organizational transparency, without being restricted to individual teams.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageReportsInPubFolders",
        "Column Description": "The PermissionsManageReportsInPubFolders column enables users to manage reports within public folders. This includes creating, editing, and organizing reports, ensuring that important data is available to all necessary stakeholders in an easily accessible and organized manner.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsEditMyDashboards",
        "Column Description": "The PermissionsEditMyDashboards column allows users to edit dashboards that they own or have access to. This is important for users who need to adjust their personal dashboards to reflect changes in business objectives or data sources.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsEditMyReports",
        "Column Description": "The PermissionsEditMyReports column enables users to edit reports they have created or have access to. This permission is essential for ensuring that users can make necessary adjustments to reports to meet their evolving needs or improve data accuracy.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsViewAllUsers",
        "Column Description": "The PermissionsViewAllUsers column grants users the ability to view all users within the organization. This is often given to administrators or managers who need to oversee user activity and profiles across Salesforce, ensuring appropriate permissions and access controls.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsBypassEmailApproval",
        "Column Description": "The PermissionsBypassEmailApproval column allows users to bypass email approval processes, typically used for system-generated messages. This is useful for administrators who need to approve or bypass certain email workflows for efficiency or troubleshooting.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsAllowUniversalSearch",
        "Column Description": "The PermissionsAllowUniversalSearch column allows users to access the universal search functionality in Salesforce, enabling them to search for records across all objects, including custom objects. This permission is essential for users who need to find specific data quickly across a wide range of Salesforce records.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsConnectOrgToEnvironmentHub",
        "Column Description": "The PermissionsConnectOrgToEnvironmentHub column enables users to connect their Salesforce organization to Salesforce Environment Hub, facilitating the integration with different environments, such as sandboxes and production instances, for development and testing purposes.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsWorkCalibrationUser",
        "Column Description": "The PermissionsWorkCalibrationUser column designates users who are allowed to calibrate work processes within Salesforce, such as measuring team performance or optimizing workflows. This is useful for operational teams seeking to improve work efficiency or quality.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsCreateCustomizeFilters",
        "Column Description": "The PermissionsCreateCustomizeFilters column allows users to create and customize filters for reports and dashboards. Filters enable users to narrow down their data analysis to specific conditions, and this permission is vital for tailoring reports to meet business requirements.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsWorkDotComUserPerm",
        "Column Description": "The PermissionsWorkDotComUserPerm column designates users who can access and work with Salesforce\u0092s Work.com platform, which focuses on employee performance and productivity. This permission is useful for HR and team managers who need to track and enhance employee performance.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsContentHubUser",
        "Column Description": "The PermissionsContentHubUser column grants users the ability to access Salesforce Content Hub, a centralized location for managing digital content such as documents, videos, and images. This is essential for teams that rely on content management as part of their business operations.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsGovernNetworks",
        "Column Description": "The PermissionsGovernNetworks column allows users to manage and govern Salesforce Communities and Experience Cloud networks. This includes controlling settings, permissions, and user access within external-facing portals or internal collaboration spaces.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsSalesConsole",
        "Column Description": "The PermissionsSalesConsole column grants users the ability to use the Salesforce Sales Console, a specialized interface designed for sales representatives to streamline their workflow. This is crucial for sales teams that rely on a simplified and efficient interface for managing leads, opportunities, and accounts.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsTwoFactorApi",
        "Column Description": "The PermissionsTwoFactorApi column enables the use of two-factor authentication (2FA) through the API. This permission enhances security by requiring a second verification step when accessing Salesforce data through API integrations, ensuring that sensitive information is better protected.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsDeleteTopics",
        "Column Description": "The PermissionsDeleteTopics column allows users to delete topics within the Salesforce platform. Topics are used for categorizing records, and this permission is important for maintaining the organization\u0092s taxonomy by removing obsolete or incorrect topics.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsEditTopics",
        "Column Description": "The PermissionsEditTopics column grants users the ability to edit existing topics within Salesforce. This permission is useful for categorizing or re-categorizing records, ensuring that topics are aligned with business changes or updates in data structure.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsCreateTopics",
        "Column Description": "The PermissionsCreateTopics column enables users to create new topics within Salesforce, which are used to organize and classify records. This is essential for ensuring that content, cases, and other objects are categorized appropriately for easier searching and filtering.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsAssignTopics",
        "Column Description": "The PermissionsAssignTopics column allows users to assign topics to records. This is useful for categorizing cases, documents, or opportunities and enabling users to find records related to specific themes, products, or services.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsIdentityEnabled",
        "Column Description": "The PermissionsIdentityEnabled column indicates whether identity features are enabled within Salesforce, such as single sign-on (SSO) and user authentication. This permission is important for IT administrators who manage user identity and access policies.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsIdentityConnect",
        "Column Description": "The PermissionsIdentityConnect column grants users the ability to use Salesforce Identity Connect to synchronize user data between Salesforce and external identity systems. This is crucial for organizations that use centralized identity management platforms.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsAllowViewKnowledge",
        "Column Description": "The PermissionsAllowViewKnowledge column allows users to view knowledge articles within Salesforce Knowledge. This is important for support teams, customer service reps, and employees who need access to self-service resources or internal knowledge bases.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsContentWorkspaces",
        "Column Description": "The PermissionsContentWorkspaces column allows users to create and manage workspaces within Salesforce Content. Workspaces are used to organize content and facilitate collaboration, making this permission valuable for teams that need to store and manage shared documents and resources.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageSearchPromotionRules",
        "Column Description": "The PermissionsManageSearchPromotionRules column grants users the ability to manage search promotion rules, which allow specific search results to be boosted in Salesforce. This is valuable for administrators or users who want to highlight important records or improve the search experience within the organization.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsCustomMobileAppsAccess",
        "Column Description": "The PermissionsCustomMobileAppsAccess column gives users access to custom mobile apps in Salesforce. This permission is critical for mobile users or sales teams that use customized mobile apps to access Salesforce data and perform tasks while on the go.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsViewHelpLink",
        "Column Description": "The PermissionsViewHelpLink column allows users to view the help link for Salesforce. This is helpful for users seeking assistance with using Salesforce, ensuring they can quickly find guides or documentation to support their work.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageProfilesPermissionsets",
        "Column Description": "The PermissionsManageProfilesPermissionsets column grants users the ability to manage profiles and permission sets. This is a key permission for system administrators who configure user access, ensuring users have appropriate permissions based on their roles within the organization.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsAssignPermissionSets",
        "Column Description": "The PermissionsAssignPermissionSets column enables users to assign permission sets to other users. This is essential for administrators managing the roles and permissions of other users, ensuring they have the correct access levels to perform their job functions.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageRoles",
        "Column Description": "The PermissionsManageRoles column allows users to manage roles within Salesforce. This is an important permission for administrators who need to assign, modify, or delete roles to control access to records and ensure the proper hierarchical structure is maintained.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageIpAddresses",
        "Column Description": "The PermissionsManageIpAddresses column grants users the ability to manage IP address settings, such as configuring trusted IP ranges for login security. This is vital for system administrators concerned with controlling and securing access to the Salesforce instance from specific network ranges.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageSharing",
        "Column Description": "The PermissionsManageSharing column enables users to configure and manage sharing rules, which define the visibility of records based on criteria such as role, group, or ownership. This is a critical permission for ensuring sensitive data is shared securely and appropriately within the organization.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageInternalUsers",
        "Column Description": "The PermissionsManageInternalUsers column allows users to manage internal Salesforce users, such as creating or deactivating user accounts. This permission is typically granted to system administrators responsible for overseeing user lifecycle management within the organization.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManagePasswordPolicies",
        "Column Description": "The PermissionsManagePasswordPolicies column gives users the ability to configure password policies, including setting password strength requirements, expiration periods, and other security measures. This is an important permission for ensuring that Salesforce accounts adhere to security best practices.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageLoginAccessPolicies",
        "Column Description": "The PermissionsManageLoginAccessPolicies column allows users to define and configure login access policies, such as controlling login hours or enforcing IP address restrictions. This is a key permission for administrators ensuring secure and controlled access to Salesforce.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsViewPlatformEvents",
        "Column Description": "The PermissionsViewPlatformEvents column enables users to view platform events, which are used to integrate Salesforce with external systems. This permission is crucial for users working with event-driven architecture or integrating real-time data into Salesforce workflows.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageCustomPermissions",
        "Column Description": "The PermissionsManageCustomPermissions column grants users the ability to manage custom permissions, which are specific access rights that can be assigned to users or processes. This is valuable for organizations that require tailored security policies beyond standard Salesforce permissions.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsCanVerifyComment",
        "Column Description": "The PermissionsCanVerifyComment column allows users to verify comments, likely within the context of data validation or approval processes. This is an essential permission for users managing comments or feedback on records to ensure that they meet the necessary criteria or guidelines.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageUnlistedGroups",
        "Column Description": "The PermissionsManageUnlistedGroups column gives users control over managing unlisted groups, which are internal groups that aren\u0092t publicly visible. This is useful for managing private, specialized groups or teams within Salesforce that need restricted access.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsStdAutomaticActivityCapture",
        "Column Description": "The PermissionsStdAutomaticActivityCapture column allows users to automatically capture activities (like emails, events, or calls) in Salesforce. This is particularly helpful for sales and service teams to track interactions with customers without manually entering activity data.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsInsightsAppDashboardEditor",
        "Column Description": "The PermissionsInsightsAppDashboardEditor column grants users the ability to edit dashboards within the Salesforce Insights application. This is important for business intelligence teams or analysts who need to customize or modify analytics dashboards to reflect business needs.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageTwoFactor",
        "Column Description": "The PermissionsManageTwoFactor column allows users to manage two-factor authentication settings within Salesforce. This is critical for enforcing additional security measures to ensure that users' accounts are protected by a second layer of verification during login.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsInsightsAppUser",
        "Column Description": "The PermissionsInsightsAppUser column provides users with access to use the Salesforce Insights application. This permission is useful for teams analyzing business performance and generating reports from the platform\u0092s analytics tools.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsInsightsAppAdmin",
        "Column Description": "The PermissionsInsightsAppAdmin column grants users administrative rights within the Salesforce Insights application, allowing them to configure settings, manage users, and oversee the platform\u0092s analytics capabilities.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsInsightsAppEltEditor",
        "Column Description": "The PermissionsInsightsAppEltEditor column allows users to edit the data extraction, transformation, and loading (ETL) processes within the Insights app. This is crucial for teams managing data pipelines to ensure that data is properly ingested and prepared for analysis.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsInsightsAppUploadUser",
        "Column Description": "The PermissionsInsightsAppUploadUser column provides users with the ability to upload data into the Salesforce Insights application. This permission is valuable for data analysts or teams responsible for integrating new datasets into Salesforce for analysis and reporting.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsInsightsCreateApplication",
        "Column Description": "The PermissionsInsightsCreateApplication column grants users the ability to create new applications within Salesforce Insights. This is a key permission for teams that build and deploy custom analytics solutions tailored to the organization\u0092s needs.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsLightningExperienceUser",
        "Column Description": "The PermissionsLightningExperienceUser column enables users to access Salesforce's Lightning Experience interface, which provides a modern and streamlined user experience. This permission is essential for users transitioning from Salesforce Classic to Lightning, offering enhanced features and functionality.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsViewDataLeakageEvents",
        "Column Description": "The PermissionsViewDataLeakageEvents column allows users to view data leakage events, which track unauthorized data access or data exports. This is an important permission for security and compliance teams monitoring sensitive data flows within Salesforce.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsConfigCustomRecs",
        "Column Description": "The PermissionsConfigCustomRecs column grants users the ability to configure custom recommendations within Salesforce. This is useful for marketing and sales teams using predictive analytics or AI-driven suggestions to optimize customer interactions and business processes.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsSubmitMacrosAllowed",
        "Column Description": "The PermissionsSubmitMacrosAllowed column allows users to submit macros in Salesforce, which are predefined sets of actions or steps to automate repetitive tasks. This is important for customer service or support teams who use macros to increase productivity.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsBulkMacrosAllowed",
        "Column Description": "The PermissionsBulkMacrosAllowed column enables users to run macros in bulk. This is useful for teams that need to execute the same macro across many records or cases at once, automating large-scale tasks efficiently.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsShareInternalArticles",
        "Column Description": "The PermissionsShareInternalArticles column grants users the ability to share internal articles within Salesforce, which are knowledge base articles or documents used by internal teams. This permission is important for knowledge management teams managing internal resources.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageSessionPermissionSets",
        "Column Description": "The PermissionsManageSessionPermissionSets column allows users to manage session-based permission sets, which control what permissions are available to users during specific sessions. This is crucial for dynamic user management and access control in more secure or regulated environments.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageTemplatedApp",
        "Column Description": "The PermissionsManageTemplatedApp column grants users the ability to manage templated applications within Salesforce. Templated apps are predefined app structures that can be customized and deployed. This permission is useful for administrators who need to create, edit, or delete these apps for organizational use.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsUseTemplatedApp",
        "Column Description": "The PermissionsUseTemplatedApp column allows users to use templated applications. This is important for employees or teams who need to leverage predefined templates to streamline their work processes within Salesforce, enhancing productivity without needing to create applications from scratch.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsSendAnnouncementEmails",
        "Column Description": "The PermissionsSendAnnouncementEmails column enables users to send announcement emails to other users or groups within Salesforce. This permission is valuable for users tasked with internal communications, ensuring that announcements about system updates, events, or other important news reach the right people.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsChatterEditOwnPost",
        "Column Description": "The PermissionsChatterEditOwnPost column allows users to edit their own posts in Chatter. This is an important feature for users who may need to correct or update information in their posts after sharing them with colleagues, ensuring that their contributions are accurate and up to date.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsChatterEditOwnRecordPost",
        "Column Description": "The PermissionsChatterEditOwnRecordPost column grants users the ability to edit posts on records they have created in Chatter. This is useful for users who interact with records through Chatter and need to adjust their posts or comments to reflect new information or changes.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsWaveTabularDownload",
        "Column Description": "The PermissionsWaveTabularDownload column allows users to download data in tabular format from Wave Analytics. This is essential for users who need to export data for further analysis or reporting, making it easier to manipulate or share the data outside of Salesforce.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsWaveCommunityUser",
        "Column Description": "The PermissionsWaveCommunityUser column grants users access to Wave Analytics in community environments. This is useful for users within Salesforce Communities who need to interact with analytic data in Wave, such as partners or customers involved in the analytics process.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsAutomaticActivityCapture",
        "Column Description": "The PermissionsAutomaticActivityCapture column allows users to automatically capture activities like emails, calls, and meetings within Salesforce. This permission enhances efficiency by ensuring all interactions with customers are logged without manual entry, improving CRM data accuracy.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsImportCustomObjects",
        "Column Description": "The PermissionsImportCustomObjects column grants users the ability to import custom objects into Salesforce. This is crucial for administrators and data teams who need to import data for custom objects into Salesforce to enrich the CRM system with additional, unique data.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsSalesforceIQInbox",
        "Column Description": "The PermissionsSalesforceIQInbox column allows users to access SalesforceIQ Inbox, which is a tool for managing emails, calendar events, and customer interactions. This is important for users who rely on SalesforceIQ to manage communications and streamline workflow processes.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsDelegatedTwoFactor",
        "Column Description": "The PermissionsDelegatedTwoFactor column enables users to delegate two-factor authentication for other users. This permission is useful in environments where administrators or security teams need to manage two-factor authentication settings for other users.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsChatterComposeUiCodesnippet",
        "Column Description": "The PermissionsChatterComposeUiCodesnippet column grants users the ability to compose code snippets in the Chatter feed. This is important for users who need to share technical information or code snippets with others in the organization, enabling collaboration on development-related tasks.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsSelectFilesFromSalesforce",
        "Column Description": "The PermissionsSelectFilesFromSalesforce column allows users to select files stored within Salesforce to attach or reference them in records or communications. This is an essential feature for users who need to work with documents or media directly within the Salesforce platform.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsModerateNetworkUsers",
        "Column Description": "The PermissionsModerateNetworkUsers column grants users the ability to moderate other users in Salesforce networks. This includes managing user participation, ensuring appropriate content is shared, and removing disruptive users. It is essential for managing the social aspect of Salesforce communities and networks.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsMergeTopics",
        "Column Description": "The PermissionsMergeTopics column enables users to merge topics within Salesforce. This is useful for administrators or knowledge managers who want to combine duplicate or similar topics to ensure content is properly categorized and searchable in Salesforce.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsSubscribeToLightningReports",
        "Column Description": "The PermissionsSubscribeToLightningReports column allows users to subscribe to Lightning Reports. This is beneficial for users who want to receive automated notifications about reports, ensuring they stay informed about important metrics and KPIs without needing to check manually.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManagePvtRptsAndDashbds",
        "Column Description": "The PermissionsManagePvtRptsAndDashbds column grants users the ability to manage private reports and dashboards. This is important for users who need to control visibility and access to reports and dashboards that should not be publicly available, typically for sensitive or internal data.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsAllowLightningLogin",
        "Column Description": "The PermissionsAllowLightningLogin column enables users to log in using the Lightning Experience interface. This is essential for users who prefer or need to use Salesforce\u0092s modern Lightning interface over the older Classic version.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsCampaignInfluence2",
        "Column Description": "The PermissionsCampaignInfluence2 column allows users to view and manage campaign influence models, which are used to track the impact of campaigns on opportunities in Salesforce. This permission is important for marketing and sales teams that need to analyze how marketing efforts are influencing sales outcomes.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsViewDataAssessment",
        "Column Description": "The PermissionsViewDataAssessment column grants users the ability to view data assessments, which provide insights into the quality and health of Salesforce data. This is essential for data governance and quality control teams who need to monitor and assess the state of organizational data.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsRemoveDirectMessageMembers",
        "Column Description": "The PermissionsRemoveDirectMessageMembers column allows users to remove members from direct message groups within Salesforce Chatter. This is useful for managing group membership, ensuring that only relevant users remain in communications channels.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsCanApproveFeedPost",
        "Column Description": "The PermissionsCanApproveFeedPost column enables users to approve posts in the Chatter feed. This is important for administrators or moderators who are responsible for ensuring that posts meet organizational standards or guidelines before being made public.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsAddDirectMessageMembers",
        "Column Description": "The PermissionsAddDirectMessageMembers column grants users the ability to add members to direct message groups in Chatter. This is useful for users who need to manage communication channels and ensure the right participants are included in discussions.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsAllowViewEditConvertedLeads",
        "Column Description": "The PermissionsAllowViewEditConvertedLeads column enables users to view and edit converted leads. This is important for sales teams that need to review or modify lead records even after they\u0092ve been converted to opportunities, accounts, or contacts.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsShowCompanyNameAsUserBadge",
        "Column Description": "The PermissionsShowCompanyNameAsUserBadge column allows users to display their company name as part of their user badge in Salesforce. This is useful for users who want to personalize their profile and make their identity more recognizable within the organization.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsAccessCMC",
        "Column Description": "The PermissionsAccessCMC column grants users access to the Customer Management Console (CMC). This is a valuable permission for support or customer success teams that need to manage customer relationships and interactions.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsArchiveArticles",
        "Column Description": "The PermissionsArchiveArticles column enables users to archive articles within Salesforce. This is useful for knowledge management teams who need to organize or retire articles that are no longer relevant or up to date.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsPublishArticles",
        "Column Description": "The PermissionsPublishArticles column grants users the ability to publish articles in Salesforce\u0092s knowledge base. This is important for content creators or subject matter experts who need to share knowledge and resources with other Salesforce users.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsViewHealthCheck",
        "Column Description": "The PermissionsViewHealthCheck column allows users to view the Salesforce Health Check, which provides insights into the security settings of the Salesforce instance. This is valuable for security teams or administrators who need to assess the overall security posture of Salesforce.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageHealthCheck",
        "Column Description": "The PermissionsManageHealthCheck column grants users the ability to configure and manage Salesforce Health Check settings. This is an important permission for security administrators responsible for ensuring that the organization\u0092s Salesforce configuration is secure and compliant.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsPackaging2",
        "Column Description": "The PermissionsPackaging2 column allows users to manage Salesforce packaging, which is used to bundle and distribute customizations and applications. This is essential for developers or administrators who need to create, edit, or manage packaged solutions.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageCertificates",
        "Column Description": "The PermissionsManageCertificates column grants users the ability to manage SSL certificates and other security certificates in Salesforce. This is a critical permission for ensuring that the Salesforce instance is secure and compliant with industry standards.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsCreateReportInLightning",
        "Column Description": "The PermissionsCreateReportInLightning column allows users to create reports in the Lightning Experience interface. This is valuable for users who are using the modern reporting tools in Salesforce Lightning to create and customize reports that meet their business needs.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsPreventClassicExperience",
        "Column Description": "The PermissionsPreventClassicExperience column prevents users from switching back to the Classic interface, enforcing the use of Lightning Experience for a more modern, feature-rich user experience. This permission is often used in organizations that want to fully transition to Lightning.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsHideReadByList",
        "Column Description": "The PermissionsHideReadByList column allows users to hide the \"Read By\" list in Chatter posts. This is useful for managing privacy and reducing clutter in Chatter posts, especially in large or active groups.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsSubmitForTranslation",
        "Column Description": "The PermissionsSubmitForTranslation column enables users to submit records for translation in Salesforce. This is essential for organizations that operate in multiple languages and need to translate content like articles or knowledge base entries to ensure global accessibility.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsEditTranslation",
        "Column Description": "The PermissionsEditTranslation column grants users the ability to edit translations in Salesforce. This is particularly important for multilingual teams or global organizations, allowing users to refine or correct translated content to maintain accuracy across regions.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsPublishTranslation",
        "Column Description": "The PermissionsPublishTranslation column allows users to publish translations in Salesforce. This permission is essential for ensuring that translated content is made available to users in the appropriate language, enhancing accessibility and user experience in international markets.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsListEmailSend",
        "Column Description": "The PermissionsListEmailSend column allows users to send email list communications within Salesforce. This is useful for marketing teams that want to send mass emails to customers, prospects, or internal stakeholders, typically for campaigns or notifications.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsFeedPinning",
        "Column Description": "The PermissionsFeedPinning column allows users to pin posts in Salesforce feeds. This is a helpful feature for administrators or team leads who want to highlight important information or discussions, ensuring they remain visible to all users or team members.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsChangeDashboardColors",
        "Column Description": "The PermissionsChangeDashboardColors column allows users to customize the color scheme of dashboards in Salesforce. This permission is useful for users who want to personalize their dashboard views, making them more visually appealing or easier to interpret based on user preferences.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageRecommendationStrategies",
        "Column Description": "The PermissionsManageRecommendationStrategies column grants users the ability to manage recommendation strategies within Salesforce. This is essential for users involved in managing product recommendations, customer journey optimization, or other strategies aimed at enhancing user experience or business outcomes.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManagePropositions",
        "Column Description": "The PermissionsManagePropositions column allows users to manage propositions in Salesforce, which could relate to product offerings or customer solutions. This is crucial for sales or product management teams that need to create, update, or modify propositions in the system.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsCloseConversations",
        "Column Description": "The PermissionsCloseConversations column enables users to close conversations in Salesforce, which is useful for customer service or support teams. It ensures that once an issue or inquiry has been resolved, the conversation can be closed and properly documented.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsSubscribeReportRolesGrps",
        "Column Description": "The PermissionsSubscribeReportRolesGrps column allows users to subscribe specific roles or groups to reports in Salesforce. This is important for keeping key stakeholders informed about report results, without requiring them to manually access the report each time it\u0092s updated.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsSubscribeDashboardRolesGrps",
        "Column Description": "The PermissionsSubscribeDashboardRolesGrps column grants users the ability to subscribe roles or groups to dashboards in Salesforce. This is beneficial for organizations that want to keep teams or leadership updated with real-time dashboard information automatically.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsUseWebLink",
        "Column Description": "The PermissionsUseWebLink column allows users to access and use web links integrated within Salesforce. This is important for teams that need to navigate between Salesforce and external websites, tools, or resources to complete their workflows.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsHasUnlimitedNBAExecutions",
        "Column Description": "The PermissionsHasUnlimitedNBAExecutions column grants users unlimited executions of Next Best Action (NBA) strategies. This is critical for sales or service teams who use NBA to drive customer engagement, making sure they can execute actions without limitations.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsViewOnlyEmbeddedAppUser",
        "Column Description": "The PermissionsViewOnlyEmbeddedAppUser column allows users to view embedded applications within Salesforce but restricts them from making edits. This is valuable for users who need to access data or functionality from external applications but do not require editing privileges.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsViewAllActivities",
        "Column Description": "The PermissionsViewAllActivities column enables users to view all activities in Salesforce, including tasks, events, and logged interactions. This is essential for users, such as managers or executives, who need to monitor or review all activities within the system to ensure transparency and coordination.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsSubscribeReportToOtherUsers",
        "Column Description": "The PermissionsSubscribeReportToOtherUsers column allows users to subscribe other users to reports in Salesforce. This is useful for administrators or report owners who want to automate report distribution to various users or teams.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsLightningConsoleAllowedForUser",
        "Column Description": "The PermissionsLightningConsoleAllowedForUser column enables users to access the Salesforce Lightning Console. This is essential for teams that rely on the Lightning Console interface, such as service agents or sales reps, to manage and track customer interactions more efficiently.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsSubscribeReportsRunAsUser",
        "Column Description": "The PermissionsSubscribeReportsRunAsUser column allows users to subscribe to reports that run as specific users. This is important for scenarios where reports are required to be viewed with the context of another user's data or permissions.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsSubscribeToLightningDashboards",
        "Column Description": "The PermissionsSubscribeToLightningDashboards column enables users to subscribe to Lightning dashboards in Salesforce. This permission is vital for teams that need to receive real-time insights and data updates through visually-driven dashboards.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsSubscribeDashboardToOtherUsers",
        "Column Description": "The PermissionsSubscribeDashboardToOtherUsers column allows users to subscribe other users to dashboards. This is useful for managers or administrators who want to ensure that key personnel are notified about important metrics or KPIs in the system.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsCreateLtngTempInPub",
        "Column Description": "The PermissionsCreateLtngTempInPub column grants users the ability to create Lightning templates in public folders. This is beneficial for teams that need to create and share reusable templates, enhancing consistency across the organization.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsAppointmentBookingUserAccess",
        "Column Description": "The PermissionsAppointmentBookingUserAccess column provides users with the ability to book appointments in Salesforce. This is particularly useful for service teams or sales teams who need to schedule appointments with customers directly from within Salesforce.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsTransactionalEmailSend",
        "Column Description": "The PermissionsTransactionalEmailSend column allows users to send transactional emails from Salesforce. This is important for automating communications related to transactions, such as order confirmations, payment receipts, or subscription updates.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsViewPrivateStaticResources",
        "Column Description": "The PermissionsViewPrivateStaticResources column grants users access to private static resources within Salesforce. This is crucial for users who need to view or interact with certain resources that are protected or restricted for specific use cases.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsCreateLtngTempFolder",
        "Column Description": "The PermissionsCreateLtngTempFolder column allows users to create folders for Lightning templates. This helps in organizing and categorizing templates, making it easier for users to find and manage them within Salesforce.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsApexRestServices",
        "Column Description": "The PermissionsApexRestServices column enables users to access and use Apex REST services. This is important for developers or integrators who need to integrate Salesforce with other systems via custom REST APIs.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsConfigureLiveMessage",
        "Column Description": "The PermissionsConfigureLiveMessage column allows users to configure Live Message settings in Salesforce. This is essential for teams who want to enable real-time messaging capabilities with customers, improving engagement and support.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsLiveMessageAgent",
        "Column Description": "The PermissionsLiveMessageAgent column grants users the ability to act as agents in Live Message, interacting with customers in real time. This permission is useful for customer service or sales teams using Live Message for direct communication.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsEnableCommunityAppLauncher",
        "Column Description": "The PermissionsEnableCommunityAppLauncher column allows users to enable the Community App Launcher. This is beneficial for users who manage Salesforce Communities, enabling them to customize and launch apps for community members.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsGiveRecognitionBadge",
        "Column Description": "The PermissionsGiveRecognitionBadge column allows users to award recognition badges in Salesforce. This is useful for administrators or managers who want to encourage positive behavior or reward achievements within the organization.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsLightningSchedulerUserAccess",
        "Column Description": "The PermissionsLightningSchedulerUserAccess column grants users access to Lightning Scheduler, which helps manage appointments, meetings, and bookings. This is important for users involved in scheduling activities or resource management.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsAllowObjectDetection",
        "Column Description": "The PermissionsAllowObjectDetection column allows users to enable and use Object Detection capabilities in Salesforce. This is valuable for teams working with images and need to detect specific objects, such as products or features, within those images.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsSalesforceIQInternal",
        "Column Description": "The PermissionsSalesforceIQInternal column grants users access to SalesforceIQ for internal use. SalesforceIQ is a tool designed to streamline communication and relationship management, and this permission ensures internal teams can leverage its capabilities.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsUseMySearch",
        "Column Description": "The PermissionsUseMySearch column enables users to use personalized search features within Salesforce. This allows individuals to quickly find the information they need by customizing their search experience, enhancing overall efficiency.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsLtngPromoReserved01UserPerm",
        "Column Description": "The PermissionsLtngPromoReserved01UserPerm column is a reserved permission for promotional use, typically for users participating in beta programs or special promotional activities within Salesforce.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageSubscriptions",
        "Column Description": "The PermissionsManageSubscriptions column grants users the ability to manage subscriptions in Salesforce. This is crucial for teams handling recurring billing, service subscriptions, or any feature that requires managing ongoing relationships with customers.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsWaveManagePrivateAssetsUser",
        "Column Description": "The PermissionsWaveManagePrivateAssetsUser column enables users to manage private assets within Wave Analytics. This is important for users responsible for maintaining sensitive or proprietary data in the analytics environment.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsAllowObjectDetectionTraining",
        "Column Description": "The PermissionsAllowObjectDetectionTraining column allows users to train Object Detection models within Salesforce. This is useful for teams involved in improving object detection capabilities by providing data to train and refine detection models.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsCanEditDataPrepRecipe",
        "Column Description": "The PermissionsCanEditDataPrepRecipe column grants users the ability to edit data prep recipes within Salesforce. This is essential for data teams who need to clean, transform, or prepare data for analysis or reporting.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsAddAnalyticsRemoteConnections",
        "Column Description": "The PermissionsAddAnalyticsRemoteConnections column enables users to add remote connections to Analytics, allowing data from external sources to be integrated and analyzed within Salesforce. This is important for teams working with diverse data sources.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageSurveys",
        "Column Description": "The PermissionsManageSurveys column allows users to create, manage, and distribute surveys within Salesforce. This is useful for organizations that want to gather feedback from customers or employees, enabling them to better understand needs and improve services.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsUseAssistantDialog",
        "Column Description": "The PermissionsUseAssistantDialog column grants users access to use Assistant Dialogs within Salesforce. This permission is essential for leveraging Salesforce's AI-powered assistant capabilities to automate tasks or provide guidance based on user inputs.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsUseQuerySuggestions",
        "Column Description": "The PermissionsUseQuerySuggestions column enables users to receive and utilize query suggestions within Salesforce. This helps users save time by suggesting frequently used or relevant queries, improving efficiency during data exploration.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsRecordVisibilityAPI",
        "Column Description": " The PermissionsRecordVisibilityAPI column grants access to the Record Visibility API, allowing users to configure and manage record visibility settings through API calls. This is crucial for automating and scaling data visibility management across different user roles or groups.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsViewRoles",
        "Column Description": "The PermissionsViewRoles column allows users to view roles in Salesforce. This is essential for administrators or managers who need to understand user role assignments and ensure proper access control.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsCanManageMaps",
        "Column Description": "The PermissionsCanManageMaps column grants users the ability to manage maps within Salesforce. This is important for organizations using geographic data and mapping tools, enabling users to customize and update map visualizations and settings.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsLMOutboundMessagingUserPerm",
        "Column Description": "The PermissionsLMOutboundMessagingUserPerm column provides users the ability to send outbound messages in Salesforce's Live Messaging (LM) system. This is useful for customer service teams engaging with clients in real-time messaging exchanges.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsModifyDataClassification",
        "Column Description": "The PermissionsModifyDataClassification column allows users to modify data classification settings within Salesforce. This is critical for organizations that need to categorize data for compliance, security, or operational purposes.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsPrivacyDataAccess",
        "Column Description": "The PermissionsPrivacyDataAccess column grants users access to sensitive privacy data in Salesforce. This is important for teams handling personally identifiable information (PII) and ensuring data privacy regulations are adhered to.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsQueryAllFiles",
        "Column Description": "The PermissionsQueryAllFiles column enables users to query all files within Salesforce, including those that might typically be restricted. This is useful for administrators or power users needing full access to manage and analyze files.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsModifyMetadata",
        "Column Description": "The PermissionsModifyMetadata column provides the ability to modify metadata within Salesforce. This permission is essential for developers or administrators working on customizations or configurations within the platform.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageCMS",
        "Column Description": "The PermissionsManageCMS column allows users to manage content management systems (CMS) within Salesforce. This permission is vital for users tasked with maintaining, updating, and organizing content across various Salesforce communities or platforms.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsSandboxTestingInCommunityApp",
        "Column Description": "The PermissionsSandboxTestingInCommunityApp column enables users to perform sandbox testing within Salesforce Communities. This helps developers or admins test new features and configurations in a safe environment before deploying them to production.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsCanEditPrompts",
        "Column Description": "The PermissionsCanEditPrompts column allows users to edit prompts within Salesforce, such as for custom applications or chatbots. This is valuable for teams working with conversational AI or guided flows in Salesforce.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsViewUserPII",
        "Column Description": "The PermissionsViewUserPII column grants access to view personally identifiable information (PII) of users in Salesforce. This is essential for teams handling sensitive data, ensuring they can access and manage PII securely.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsViewDraftArticles",
        "Column Description": "The PermissionsViewDraftArticles column allows users to view draft articles within Salesforce. This is useful for content teams who need to review or edit articles before they are published, ensuring quality and compliance.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsViewArchivedArticles",
        "Column Description": "The PermissionsViewArchivedArticles column grants users the ability to view archived articles in Salesforce. This is important for teams who need to reference past content, even after it has been archived.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageHubConnections",
        "Column Description": "The PermissionsManageHubConnections column enables users to manage connections within Salesforce's Hub, which could involve third-party integrations or internal system connections. This is crucial for maintaining an efficient and connected Salesforce ecosystem.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsB2BMarketingAnalyticsUser",
        "Column Description": "The PermissionsB2BMarketingAnalyticsUser column allows users to access and use B2B marketing analytics tools within Salesforce. This is important for marketing teams who want to analyze and optimize their B2B campaigns and strategies.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsTraceXdsQueries",
        "Column Description": "The PermissionsTraceXdsQueries column provides users with the ability to trace and debug XDS (XML Data Services) queries in Salesforce. This is valuable for developers or administrators working with complex data queries or integrations.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsViewSecurityCommandCenter",
        "Column Description": "The PermissionsViewSecurityCommandCenter column grants users access to view the Security Command Center in Salesforce. This is important for security teams monitoring data security and privacy within the Salesforce platform.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageSecurityCommandCenter",
        "Column Description": "The PermissionsManageSecurityCommandCenter column allows users to manage the Security Command Center settings. This permission is essential for users responsible for overseeing and managing security protocols and actions in Salesforce.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsViewAllCustomSettings",
        "Column Description": "The PermissionsViewAllCustomSettings column enables users to view all custom settings in Salesforce. This is valuable for administrators who need to manage or troubleshoot configurations and customizations.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsViewAllForeignKeyNames",
        "Column Description": "The PermissionsViewAllForeignKeyNames column allows users to view all foreign key names in Salesforce. This is important for database management and integration tasks, as foreign keys are critical for establishing relationships between records.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsAddWaveNotificationRecipients",
        "Column Description": "The PermissionsAddWaveNotificationRecipients column allows users to add recipients to notifications in Salesforce Wave Analytics. This is useful for users managing reports and dashboards, ensuring that the right people are notified when key metrics change.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsHeadlessCMSAccess",
        "Column Description": "The PermissionsHeadlessCMSAccess column grants access to headless CMS features within Salesforce. This is important for teams working with decoupled content management systems, where content is created and managed separately from the presentation layer.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsUseFulfillmentAPIs",
        "Column Description": "The PermissionsUseFulfillmentAPIs column allows users to access fulfillment APIs within Salesforce. This is essential for teams involved in order processing or managing the delivery of services or products to customers.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsLMEndMessagingSessionUserPerm",
        "Column Description": "The PermissionsLMEndMessagingSessionUserPerm column enables users to end messaging sessions in Salesforce Live Messaging. This is valuable for support or sales agents who need to conclude a conversation or service session appropriately.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsConsentApiUpdate",
        "Column Description": "The PermissionsConsentApiUpdate column allows users to update consent information via API calls in Salesforce. This is important for compliance purposes, ensuring that user consent records are kept up-to-date and accurate.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsPaymentsAPIUser",
        "Column Description": "The PermissionsPaymentsAPIUser column grants users access to the Payments API in Salesforce. This is essential for teams involved in processing payments, managing subscriptions, or handling financial transactions through Salesforce integrations.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsAccessContentBuilder",
        "Column Description": "The PermissionsAccessContentBuilder column enables users to access Salesforce's Content Builder. This is useful for teams responsible for creating and managing content, such as marketing emails or landing pages, within the Salesforce platform.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsAccountSwitcherUser",
        "Column Description": "The PermissionsAccountSwitcherUser column allows users to switch between different accounts in Salesforce. This is useful for users who manage multiple accounts, such as sales representatives working with different client accounts.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsViewAnomalyEvents",
        "Column Description": "The PermissionsViewAnomalyEvents column grants users access to view anomaly events within Salesforce. This is important for teams tracking unusual behavior or trends in data, ensuring timely identification and response to potential issues.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageC360AConnections",
        "Column Description": "The PermissionsManageC360AConnections column allows users to manage connections within the Customer 360 Analytics (C360A) feature in Salesforce. This is important for teams working on customer data integrations and analytics across various systems.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsIsContactCenterAdmin",
        "Column Description": "The PermissionsIsContactCenterAdmin column designates users as administrators of the Contact Center in Salesforce. This permission is important for those responsible for managing contact center settings, user access, and configurations.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsIsContactCenterAgent",
        "Column Description": "The PermissionsIsContactCenterAgent column designates users as agents within the Contact Center in Salesforce. This is essential for users working directly with customers, handling inquiries, and providing support.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageReleaseUpdates",
        "Column Description": "The PermissionsManageReleaseUpdates column enables users to manage release updates in Salesforce. This is important for teams responsible for overseeing system upgrades, ensuring smooth transitions between Salesforce versions.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsViewAllProfiles",
        "Column Description": "The PermissionsViewAllProfiles column allows users to view all profiles within Salesforce. This is essential for administrators or security teams who need to review user permissions and roles.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsSkipIdentityConfirmation",
        "Column Description": "The PermissionsSkipIdentityConfirmation column allows users to bypass identity confirmation steps during login or authentication. This is useful for users with specific permissions or those in trusted roles within the organization.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsCanToggleCallRecordings",
        "Column Description": "The PermissionsCanToggleCallRecordings column allows users to toggle call recording settings within Salesforce. This is important for teams involved in telephony or customer service, where call recordings are necessary for compliance or quality control.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsLearningManager",
        "Column Description": "The PermissionsLearningManager column designates users as Learning Managers in Salesforce. This is important for those overseeing employee learning and development programs within the Salesforce platform.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsIsContactCenterAdminBYOT",
        "Column Description": "The PermissionsIsContactCenterAdminBYOT column designates users as administrators of Contact Centers in the Bring Your Own Telephony (BYOT) setup. This is essential for organizations using third-party telephony services with Salesforce.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsIsContactCenterAgentBYOT",
        "Column Description": "The PermissionsIsContactCenterAgentBYOT column designates users as agents in Contact Centers with a BYOT setup. This is important for agents working in environments where telephony systems are not native to Salesforce.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsSendCustomNotifications",
        "Column Description": "The PermissionsSendCustomNotifications column enables users to send custom notifications within Salesforce. This is useful for teams that need to alert users about specific events, actions, or updates.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsPackaging2Delete",
        "Column Description": "The PermissionsPackaging2Delete column allows users to delete packaged elements within Salesforce. This is necessary for developers or administrators working with Salesforce packages and their management.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsUseOmnichannelInventoryAPIs",
        "Column Description": "The PermissionsUseOmnichannelInventoryAPIs column grants users access to omnichannel inventory APIs. This is essential for managing inventory data across multiple channels, integrating with third-party systems, and streamlining order management.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsViewRestrictionAndScopingRules",
        "Column Description": "The PermissionsViewRestrictionAndScopingRules column allows users to view data restriction and scoping rules in Salesforce. This is critical for teams managing data access controls, ensuring compliance with data security policies.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsDecisionTableExecUserAccess",
        "Column Description": "The PermissionsDecisionTableExecUserAccess column enables users to execute decision tables within Salesforce. This is valuable for teams using decision logic to drive business rules and workflows.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsFSCComprehensiveUserAccess",
        "Column Description": "The PermissionsFSCComprehensiveUserAccess column grants users comprehensive access to the Field Service Cloud (FSC) features in Salesforce. This is important for service teams that manage field operations, schedules, and resources.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsBotManageBots",
        "Column Description": "The PermissionsBotManageBots column allows users to manage bots in Salesforce. This is critical for teams using automation, AI-powered bots, or chatbots to assist customers",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsBotManageBotsTrainingData",
        "Column Description": "PermissionsBotManageBotsTrainingData: This permission allows users to manage training data for bots within Salesforce. It is essential for teams working with AI-powered bots or chatbots, enabling them to update or modify the training data that helps improve bot responses and behavior.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsSchedulingLineAmbassador",
        "Column Description": "PermissionsSchedulingLineAmbassador: This permission allows users to act as ambassadors for scheduling lines in Salesforce. This is useful for teams managing scheduling systems where certain users may have elevated permissions to oversee scheduling operations.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsSchedulingFacilityManager",
        "Column Description": "PermissionsSchedulingFacilityManager: This permission grants users the ability to manage facilities in a scheduling system within Salesforce. Facility managers can use this permission to assign, modify, or view schedules related to specific facilities, resources, or equipment.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsOmnichannelInventorySync",
        "Column Description": "PermissionsOmnichannelInventorySync: This column enables users to synchronize inventory across multiple channels in Salesforce. This is critical for organizations that need to manage inventory in real-time across physical stores, e-commerce platforms, and other sales channels.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageLearningReporting",
        "Column Description": "PermissionsManageLearningReporting: This permission grants users access to manage reporting related to learning activities within Salesforce. It is beneficial for organizations using Salesforce\u0092s learning management systems, enabling them to generate and customize reports about employee training progress and outcomes.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsIsContactCenterSupervisor",
        "Column Description": "PermissionsIsContactCenterSupervisor: This column designates users as supervisors in a contact center environment within Salesforce. Supervisors can monitor agent activities, view performance metrics, and manage operational workflows within the contact center.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsIsotopeCToCUser",
        "Column Description": "PermissionsIsotopeCToCUser: This permission allows users to access the Isotope C2C (Customer-to-Customer) features in Salesforce. Isotope is typically used in environments that involve peer-to-peer interactions, such as customer reviews, support forums, or feedback systems.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsCanAccessCE",
        "Column Description": "PermissionsCanAccessCE: This permission grants users access to the Customer Engagement (CE) features within Salesforce. It is important for teams managing customer relationships, enabling them to leverage customer engagement tools for improving satisfaction and loyalty.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsUseAddOrderItemSummaryAPIs",
        "Column Description": "PermissionsUseAddOrderItemSummaryAPIs: This permission grants users access to APIs for adding order item summaries within Salesforce. It is important for teams managing e-commerce or order entry systems, enabling them to modify or add item summaries during the order process.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsIsotopeAccess",
        "Column Description": "PermissionsIsotopeAccess: This permission allows users to access Isotope features within Salesforce. Isotope is commonly used for managing customer interactions or service workflows, so this permission grants users the ability to utilize these functionalities.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsIsotopeLEX",
        "Column Description": "PermissionsIsotopeLEX: This permission provides access to Isotope's Lightning Experience (LEX) features in Salesforce. It enables users to utilize Isotope within the enhanced user interface of Salesforce Lightning, offering a more efficient and modern experience for managing customer interactions.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsExplainabilityUserAccess",
        "Column Description": "PermissionsExplainabilityUserAccess: This permission allows users to access the explainability features of machine learning models in Salesforce. It is useful for teams that need to understand the reasoning behind AI model predictions or decisions to ensure transparency and improve trust in AI-powered insights.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsExplainabilityCmtyAccess",
        "Column Description": "PermissionsExplainabilityCmtyAccess: This permission grants users access to explainability features within Salesforce Communities. It is valuable for organizations using machine learning models to ensure that the logic behind AI decisions can be communicated clearly to community users.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsQuipMetricsAccess",
        "Column Description": "PermissionsQuipMetricsAccess: This permission enables users to access metrics related to the Quip collaboration platform within Salesforce. Quip metrics can help track user engagement, activity, and the effectiveness of collaborative efforts within the organization.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsQuipUserEngagementMetrics",
        "Column Description": "PermissionsQuipUserEngagementMetrics: This permission allows users to access user engagement metrics specifically for Quip users within Salesforce. It helps organizations analyze how effectively teams are using the Quip platform for collaboration and document management.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsRemoteMediaVirtualDesktop",
        "Column Description": "PermissionsRemoteMediaVirtualDesktop: This permission grants users access to media and virtual desktop features remotely within Salesforce. It is useful for users who need to access remote media files or virtual desktop environments for work-related tasks.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsTransactionSecurityExempt",
        "Column Description": "PermissionsTransactionSecurityExempt: This permission exempts users from transaction security rules within Salesforce. It may be granted to trusted users, such as system administrators, to allow them to bypass certain security protocols during transactions.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageStores",
        "Column Description": "PermissionsManageStores: This permission allows users to manage store-related data within Salesforce. This is essential for businesses that operate physical stores or retail locations, enabling users to manage store operations, inventory, and customer interactions.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsInteractionCalcUserPerm",
        "Column Description": "PermissionsInteractionCalcUserPerm: This column provides users with permissions to access and manage interaction calculation features within Salesforce. It is important for teams that analyze customer interactions, ensuring the correct computation of metrics related to customer touchpoints.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsInteractionCalcAdminPerm",
        "Column Description": "PermissionsInteractionCalcAdminPerm: This permission grants administrative users the ability to configure and manage interaction calculations within Salesforce. It is useful for setting up or adjusting metrics related to customer interactions and their analysis.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageExternalConnections",
        "Column Description": "PermissionsManageExternalConnections: This permission allows users to manage connections to external systems or platforms from Salesforce. This is essential for integrations with third-party tools, data sources, or services.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsUseReturnOrder",
        "Column Description": "PermissionsUseReturnOrder: This permission grants users the ability to process return orders in Salesforce. It is important for organizations dealing with product returns, enabling users to initiate, track, and manage returns efficiently.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsUseReturnOrderAPIs",
        "Column Description": "PermissionsUseReturnOrderAPIs: This permission provides users access to APIs for managing return orders within Salesforce. It is important for integrating return order management into third-party systems or custom workflows.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsUseSubscriptionEmails",
        "Column Description": "PermissionsUseSubscriptionEmails: This column grants users the ability to manage and use subscription-based email features in Salesforce. This is useful for marketing teams that rely on email campaigns or customer subscription management.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsUseOrderEntry",
        "Column Description": "PermissionsUseOrderEntry: This permission allows users to enter orders into Salesforce. It is essential for sales teams or customer service agents who need to process and track customer orders.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsUseRepricing",
        "Column Description": "PermissionsUseRepricing: This permission grants users the ability to use repricing features within Salesforce. It is important for organizations managing dynamic pricing, allowing users to modify and adjust prices for products or services based on certain criteria.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsBroadcaster",
        "Column Description": "PermissionsBroadcaster: This permission allows users to broadcast messages or updates within Salesforce. It is typically used by administrators or communication teams to disseminate important information to all users or specific groups.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsAIViewInsightObjects",
        "Column Description": "PermissionsAIViewInsightObjects: This permission allows users to view AI-generated insight objects within Salesforce. This is essential for teams working with machine learning models or AI-driven insights to improve business decision-making.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsAICreateInsightObjects",
        "Column Description": "PermissionsAICreateInsightObjects: This permission enables users to create AI-generated insight objects in Salesforce. This is important for teams using Salesforce's AI capabilities to build custom insights for business intelligence and analytics.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsViewMLModels",
        "Column Description": "PermissionsViewMLModels: This permission grants users access to view machine learning models within Salesforce. It is important for data scientists or machine learning specialists who need to monitor, analyze, or modify models used within the platform.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsLifecycleManagementAPIUser",
        "Column Description": "PermissionsLifecycleManagementAPIUser: This permission grants users access to the Lifecycle Management API in Salesforce. It is essential for teams working with API integrations or managing the lifecycle of assets, records, or processes within Salesforce.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsEnablementUser",
        "Column Description": "PermissionsEnablementUser: This permission designates users as Enablement Users within Salesforce. This role is often focused on training, onboarding, and ensuring that users within an organization have the skills and knowledge to effectively use Salesforce.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsNativeWebviewScrolling",
        "Column Description": "PermissionsNativeWebviewScrolling: This permission allows users to scroll within native web views in Salesforce. This is typically useful for mobile users or those accessing Salesforce through a web-based interface, enabling a smooth and responsive experience.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsViewDeveloperName",
        "Column Description": "PermissionsViewDeveloperName: This permission grants users access to view the developer name associated with records or objects in Salesforce. This is typically useful for developers or administrators managing custom objects and metadata within the platform.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsBypassMFAForUiLogins",
        "Column Description": "PermissionsBypassMFAForUiLogins: This permission allows users to bypass multi-factor authentication (MFA) for user interface logins in Salesforce. This may be granted to trusted users or administrators to streamline login processes while maintaining security controls elsewhere.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsClientSecretRotation",
        "Column Description": "PermissionsClientSecretRotation: This permission allows users to manage the rotation of client secrets in Salesforce. This is essential for ensuring that API integrations remain secure by periodically updating client secrets.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsAccessToServiceProcess",
        "Column Description": "PermissionsAccessToServiceProcess: This permission grants users access to the service process in Salesforce. It is important for service teams that need to manage, track, or optimize service-related workflows.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageOrchInstsAndWorkItems",
        "Column Description": "PermissionsManageOrchInstsAndWorkItems: This permission enables users to manage orchestration instances and work items within Salesforce. It is essential for teams working with automation or business processes that require task orchestration.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsCMSECEAuthoringAccess",
        "Column Description": "PermissionsCMSECEAuthoringAccess: This permission allows users to author content for the Salesforce Commerce Management System (CMS ECE). This is useful for teams creating or editing content related to e-commerce or digital sales.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsEnablementAdmin",
        "Column Description": "PermissionsEnablementAdmin: This permission designates users as Enablement Administrators within Salesforce. They manage training, knowledge resources, and user enablement activities to ensure that users effectively use Salesforce products and features.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsManageDataspaceScope",
        "Column Description": "PermissionsManageDataspaceScope: This permission allows users to configure the scope of dataspace management in Salesforce. It is important for organizations managing data boundaries and access within Salesforce to ensure proper data governance.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsConfigureDataspaceScope",
        "Column Description": "PermissionsConfigureDataspaceScope: This permission grants users the ability to configure dataspace scope settings in Salesforce. It is essential for organizations that need to define data governance boundaries for users or teams.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsOmniSupervisorManageQueue",
        "Column Description": "PermissionsOmniSupervisorManageQueue: This permission grants supervisors the ability to manage queues within Salesforce Omnichannel. It is important for managing customer service workloads, ensuring that requests are directed to the right agents or teams.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsViewClientSecret",
        "Column Description": "PermissionsViewClientSecret: This permission allows users to view client secrets within Salesforce. It is critical for administrators or developers who need to access these secrets to manage API integrations or security configurations.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsEditRepricing",
        "Column Description": "PermissionsEditRepricing: This permission grants users the ability to edit repricing configurations within Salesforce. This is important for adjusting pricing models, discounts, or promotional pricing strategies in an e-commerce or sales context.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsEnableIPFSUpload",
        "Column Description": "PermissionsEnableIPFSUpload: This permission enables users to upload files to the Interplanetary File System (IPFS) within Salesforce. This is useful for organizations that use decentralized storage systems like IPFS for managing large files or data objects.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsEnableBCTransactionPolling",
        "Column Description": "PermissionsEnableBCTransactionPolling: This permission grants users access to blockchain transaction polling features within Salesforce. It is useful for organizations leveraging blockchain technology for tracking transactions in a decentralized manner.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "PermissionsFSCArcGraphCommunityUser",
        "Column Description": "PermissionsFSCArcGraphCommunityUser: This permission grants access to the ArcGraph community features within Salesforce Financial Services Cloud (FSC). It is essential for financial services organizations that need to collaborate or share information within their community.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "UserLicenseId",
        "Column Description": "UserLicenseId: This field stores the unique identifier for the user\u0092s license type in Salesforce. It determines the level of access and features available to the user based on their license.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "UserType",
        "Column Description": "UserType: This field defines the type of user within Salesforce (e.g., standard user, system administrator, etc.).",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "CreatedDate",
        "Column Description": "CreatedDate: This field stores the timestamp of when the record was created in Salesforce.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "CreatedById",
        "Column Description": "CreatedById: This field stores the identifier of the user who created the record in Salesforce.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "LastModifiedDate",
        "Column Description": "LastModifiedDate: This field stores the timestamp of when the record was last modified in Salesforce.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "LastModifiedById",
        "Column Description": "LastModifiedById: This field stores the identifier of the user who last modified the record.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "SystemModstamp",
        "Column Description": "SystemModstamp: This field contains the timestamp of the most recent modification made to the record by the system.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "Description",
        "Column Description": "Description: This field provides a text description or additional information about the record or permission.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "LastViewedDate",
        "Column Description": "LastViewedDate: This field stores the timestamp of when the record was last viewed by a user.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_profiles",
        "Table Description": "The salesforce_profiles table stores information about user profiles in Salesforce, which define the permissions and access levels for different users within an organization. A profile controls what users can see, create, edit, delete, and manage within Salesforce, ensuring security and appropriate data access. Profiles are essential for managing roles, responsibilities, and user privileges across various objects and functionalities in Salesforce. Below is a detailed description of each column in the table.",
        "Column Name": "LastReferencedDate",
        "Column Description": "LastReferencedDate: This field stores the timestamp of the last time the record was referenced in a query or operation.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quote_line_items",
        "Table Description": "The salesforce_quote_line_items table in Salesforce is designed to store detailed information about the line items associated with a quote in the Salesforce CPQ (Configure, Price, Quote) system. Each row in this table corresponds to a specific item on a quote, and the table holds data about the product or service being quoted, the pricing, quantities, discounts, and other relevant attributes.",
        "Column Name": "attributes",
        "Column Description": "The attributes column stores metadata related to the record. This column is automatically created by Salesforce and contains important information that is not part of the main data but still useful for internal tracking and API operations. ",
        "Type": "text"
    },
    {
        "Table Name": "salesforce_quote_line_items",
        "Table Description": "The salesforce_quote_line_items table in Salesforce is designed to store detailed information about the line items associated with a quote in the Salesforce CPQ (Configure, Price, Quote) system. Each row in this table corresponds to a specific item on a quote, and the table holds data about the product or service being quoted, the pricing, quantities, discounts, and other relevant attributes.",
        "Column Name": "Id",
        "Column Description": "This is the unique identifier for each quote line item. It serves as the primary key in the table and is used to uniquely identify each row representing a product or service included in a quote.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_quote_line_items",
        "Table Description": "The salesforce_quote_line_items table in Salesforce is designed to store detailed information about the line items associated with a quote in the Salesforce CPQ (Configure, Price, Quote) system. Each row in this table corresponds to a specific item on a quote, and the table holds data about the product or service being quoted, the pricing, quantities, discounts, and other relevant attributes.",
        "Column Name": "IsDeleted",
        "Column Description": "This boolean column indicates whether the quote line item has been deleted. If set to True, the quote line item has been deleted; if set to False, the item is still active in the system.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_quote_line_items",
        "Table Description": "The salesforce_quote_line_items table in Salesforce is designed to store detailed information about the line items associated with a quote in the Salesforce CPQ (Configure, Price, Quote) system. Each row in this table corresponds to a specific item on a quote, and the table holds data about the product or service being quoted, the pricing, quantities, discounts, and other relevant attributes.",
        "Column Name": "LineNumber",
        "Column Description": "This column represents the line number of the quote line item. It is used to track the order in which the line items appear on the quote, helping to organize and display the items sequentially.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_quote_line_items",
        "Table Description": "The salesforce_quote_line_items table in Salesforce is designed to store detailed information about the line items associated with a quote in the Salesforce CPQ (Configure, Price, Quote) system. Each row in this table corresponds to a specific item on a quote, and the table holds data about the product or service being quoted, the pricing, quantities, discounts, and other relevant attributes.",
        "Column Name": "CreatedDate",
        "Column Description": "This column stores the timestamp of when the quote line item was created in Salesforce. It helps track when the line item was initially added to the system.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_quote_line_items",
        "Table Description": "The salesforce_quote_line_items table in Salesforce is designed to store detailed information about the line items associated with a quote in the Salesforce CPQ (Configure, Price, Quote) system. Each row in this table corresponds to a specific item on a quote, and the table holds data about the product or service being quoted, the pricing, quantities, discounts, and other relevant attributes.",
        "Column Name": "CreatedById",
        "Column Description": "This field holds the unique identifier for the user who created the quote line item. It is a foreign key linking to the User object, indicating who added the record to the system.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_quote_line_items",
        "Table Description": "The salesforce_quote_line_items table in Salesforce is designed to store detailed information about the line items associated with a quote in the Salesforce CPQ (Configure, Price, Quote) system. Each row in this table corresponds to a specific item on a quote, and the table holds data about the product or service being quoted, the pricing, quantities, discounts, and other relevant attributes.",
        "Column Name": "LastModifiedDate",
        "Column Description": "This column holds the timestamp of the last time the quote line item was modified. It tracks any changes made to the item after its creation.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_quote_line_items",
        "Table Description": "The salesforce_quote_line_items table in Salesforce is designed to store detailed information about the line items associated with a quote in the Salesforce CPQ (Configure, Price, Quote) system. Each row in this table corresponds to a specific item on a quote, and the table holds data about the product or service being quoted, the pricing, quantities, discounts, and other relevant attributes.",
        "Column Name": "LastModifiedById",
        "Column Description": "This column holds the unique identifier for the user who last modified the quote line item. It is a foreign key linking to the User object, indicating who made the most recent changes to the record.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_quote_line_items",
        "Table Description": "The salesforce_quote_line_items table in Salesforce is designed to store detailed information about the line items associated with a quote in the Salesforce CPQ (Configure, Price, Quote) system. Each row in this table corresponds to a specific item on a quote, and the table holds data about the product or service being quoted, the pricing, quantities, discounts, and other relevant attributes.",
        "Column Name": "SystemModstamp",
        "Column Description": "This is a system-generated timestamp that reflects the most recent modification to the record. It is automatically updated whenever any change is made to the quote line item, including system-driven updates.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_quote_line_items",
        "Table Description": "The salesforce_quote_line_items table in Salesforce is designed to store detailed information about the line items associated with a quote in the Salesforce CPQ (Configure, Price, Quote) system. Each row in this table corresponds to a specific item on a quote, and the table holds data about the product or service being quoted, the pricing, quantities, discounts, and other relevant attributes.",
        "Column Name": "LastViewedDate",
        "Column Description": "This column indicates the last time the quote line item was viewed by a user. It is automatically updated when a user accesses the record.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quote_line_items",
        "Table Description": "The salesforce_quote_line_items table in Salesforce is designed to store detailed information about the line items associated with a quote in the Salesforce CPQ (Configure, Price, Quote) system. Each row in this table corresponds to a specific item on a quote, and the table holds data about the product or service being quoted, the pricing, quantities, discounts, and other relevant attributes.",
        "Column Name": "LastReferencedDate",
        "Column Description": "Similar to LastViewedDate, this column indicates the last time the quote line item was referenced by a user or system. This could include interactions such as accessing or querying the record.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quote_line_items",
        "Table Description": "The salesforce_quote_line_items table in Salesforce is designed to store detailed information about the line items associated with a quote in the Salesforce CPQ (Configure, Price, Quote) system. Each row in this table corresponds to a specific item on a quote, and the table holds data about the product or service being quoted, the pricing, quantities, discounts, and other relevant attributes.",
        "Column Name": "QuoteId",
        "Column Description": "This foreign key links the quote line item to a specific quote in Salesforce. Each quote line item is associated with one quote, and this column ensures the item is tied to the correct parent quote.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_quote_line_items",
        "Table Description": "The salesforce_quote_line_items table in Salesforce is designed to store detailed information about the line items associated with a quote in the Salesforce CPQ (Configure, Price, Quote) system. Each row in this table corresponds to a specific item on a quote, and the table holds data about the product or service being quoted, the pricing, quantities, discounts, and other relevant attributes.",
        "Column Name": "PricebookEntryId",
        "Column Description": "PricebookEntryId: This is a foreign key that links the quote line item to a specific pricebook entry in Salesforce. It connects the line item to a particular product in a pricebook, which determines the pricing for that item.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_quote_line_items",
        "Table Description": "The salesforce_quote_line_items table in Salesforce is designed to store detailed information about the line items associated with a quote in the Salesforce CPQ (Configure, Price, Quote) system. Each row in this table corresponds to a specific item on a quote, and the table holds data about the product or service being quoted, the pricing, quantities, discounts, and other relevant attributes.",
        "Column Name": "OpportunityLineItemId",
        "Column Description": "OpportunityLineItemId: This foreign key associates the quote line item with a specific opportunity line item, allowing the system to track the relationship between a sales opportunity and the quote line item.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quote_line_items",
        "Table Description": "The salesforce_quote_line_items table in Salesforce is designed to store detailed information about the line items associated with a quote in the Salesforce CPQ (Configure, Price, Quote) system. Each row in this table corresponds to a specific item on a quote, and the table holds data about the product or service being quoted, the pricing, quantities, discounts, and other relevant attributes.",
        "Column Name": "Quantity",
        "Column Description": "Quantity: This column represents the quantity of the product or service being quoted. It indicates how many units of the product or service are included in the quote line item.",
        "Type": "float"
    },
    {
        "Table Name": "salesforce_quote_line_items",
        "Table Description": "The salesforce_quote_line_items table in Salesforce is designed to store detailed information about the line items associated with a quote in the Salesforce CPQ (Configure, Price, Quote) system. Each row in this table corresponds to a specific item on a quote, and the table holds data about the product or service being quoted, the pricing, quantities, discounts, and other relevant attributes.",
        "Column Name": "UnitPrice",
        "Column Description": "UnitPrice: The unit price of the product or service associated with the quote line item. This is the price per individual unit of the product or service before any discounts are applied.",
        "Type": "float"
    },
    {
        "Table Name": "salesforce_quote_line_items",
        "Table Description": "The salesforce_quote_line_items table in Salesforce is designed to store detailed information about the line items associated with a quote in the Salesforce CPQ (Configure, Price, Quote) system. Each row in this table corresponds to a specific item on a quote, and the table holds data about the product or service being quoted, the pricing, quantities, discounts, and other relevant attributes.",
        "Column Name": "Discount",
        "Column Description": "Discount: This column stores the discount applied to the quote line item, typically as a percentage of the list price. It reduces the UnitPrice and impacts the final TotalPrice.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quote_line_items",
        "Table Description": "The salesforce_quote_line_items table in Salesforce is designed to store detailed information about the line items associated with a quote in the Salesforce CPQ (Configure, Price, Quote) system. Each row in this table corresponds to a specific item on a quote, and the table holds data about the product or service being quoted, the pricing, quantities, discounts, and other relevant attributes.",
        "Column Name": "Description",
        "Column Description": "Description: This field holds a textual description of the product or service being quoted. It provides additional context for the line item, explaining the nature of the item, its features, or other important details.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quote_line_items",
        "Table Description": "The salesforce_quote_line_items table in Salesforce is designed to store detailed information about the line items associated with a quote in the Salesforce CPQ (Configure, Price, Quote) system. Each row in this table corresponds to a specific item on a quote, and the table holds data about the product or service being quoted, the pricing, quantities, discounts, and other relevant attributes.",
        "Column Name": "ServiceDate",
        "Column Description": "ServiceDate: The service date represents the date when the service related to the quote line item is set to start. This is especially relevant for services with a defined start date, such as subscriptions or ongoing services.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quote_line_items",
        "Table Description": "The salesforce_quote_line_items table in Salesforce is designed to store detailed information about the line items associated with a quote in the Salesforce CPQ (Configure, Price, Quote) system. Each row in this table corresponds to a specific item on a quote, and the table holds data about the product or service being quoted, the pricing, quantities, discounts, and other relevant attributes.",
        "Column Name": "Product2Id",
        "Column Description": "Product2Id: This foreign key links the quote line item to the Product2 object, which represents the specific product or service being quoted. This column helps identify the actual product in the Salesforce product catalog.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_quote_line_items",
        "Table Description": "The salesforce_quote_line_items table in Salesforce is designed to store detailed information about the line items associated with a quote in the Salesforce CPQ (Configure, Price, Quote) system. Each row in this table corresponds to a specific item on a quote, and the table holds data about the product or service being quoted, the pricing, quantities, discounts, and other relevant attributes.",
        "Column Name": "SortOrder",
        "Column Description": "SortOrder: This column indicates the order in which the quote line items should be sorted or displayed on the quote. It helps determine how the line items appear in the quote document or UI, especially when there are multiple items with a similar LineNumber.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quote_line_items",
        "Table Description": "The salesforce_quote_line_items table in Salesforce is designed to store detailed information about the line items associated with a quote in the Salesforce CPQ (Configure, Price, Quote) system. Each row in this table corresponds to a specific item on a quote, and the table holds data about the product or service being quoted, the pricing, quantities, discounts, and other relevant attributes.",
        "Column Name": "ListPrice",
        "Column Description": "ListPrice: The original list price of the product or service, before any discounts are applied. This is typically the price that would be charged for a product or service if no special discounts or promotions were in place.",
        "Type": "float"
    },
    {
        "Table Name": "salesforce_quote_line_items",
        "Table Description": "The salesforce_quote_line_items table in Salesforce is designed to store detailed information about the line items associated with a quote in the Salesforce CPQ (Configure, Price, Quote) system. Each row in this table corresponds to a specific item on a quote, and the table holds data about the product or service being quoted, the pricing, quantities, discounts, and other relevant attributes.",
        "Column Name": "Subtotal",
        "Column Description": "Subtotal: The subtotal of the quote line item represents the total price for that line before taxes and other adjustments are applied. It is typically calculated as the UnitPrice multiplied by the Quantity, potentially adjusted for discounts.",
        "Type": "float"
    },
    {
        "Table Name": "salesforce_quote_line_items",
        "Table Description": "The salesforce_quote_line_items table in Salesforce is designed to store detailed information about the line items associated with a quote in the Salesforce CPQ (Configure, Price, Quote) system. Each row in this table corresponds to a specific item on a quote, and the table holds data about the product or service being quoted, the pricing, quantities, discounts, and other relevant attributes.",
        "Column Name": "TotalPrice",
        "Column Description": "TotalPrice: The total price for the quote line item, including any adjustments, discounts, taxes, and other factors. This is the final amount to be billed for the quote line item and is calculated as the sum of the Subtotal and any other applicable charges.",
        "Type": "float"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "attributes",
        "Column Description": "The attributes column stores metadata about the record, typically used to track API versioning or to provide information about the object type in Salesforce.",
        "Type": "text"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "Id",
        "Column Description": "The Id column uniquely identifies each quote record in Salesforce. It is the primary key for the table and is used to reference the quote in other related objects.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "OwnerId",
        "Column Description": "The OwnerId column stores the ID of the user who owns the quote. It links the quote to the user or salesperson responsible for it, which is critical for sales management and tracking.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "IsDeleted",
        "Column Description": "The IsDeleted column is a boolean field indicating whether the quote has been soft-deleted. If TRUE, the quote has been marked for deletion but is still recoverable in Salesforce.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "Name",
        "Column Description": "The Name column stores the name or title of the quote, which helps in identifying and referencing the quote. This is typically generated based on the associated opportunity or account.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "CreatedDate",
        "Column Description": "The CreatedDate column contains the date and time when the quote was created in Salesforce. This timestamp is useful for tracking the creation of the quote and for reporting purposes.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "CreatedById",
        "Column Description": "The CreatedById column stores the ID of the user who created the quote. This field helps in tracking who generated the quote and provides auditing capabilities.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "LastModifiedDate",
        "Column Description": "The LastModifiedDate column contains the date and time when the quote was last modified. This helps in tracking changes made to the quote and ensures that the latest version is available.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "LastModifiedById",
        "Column Description": "The LastModifiedById column holds the ID of the user who last modified the quote. This helps in identifying who made the most recent changes to the quote.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "SystemModstamp",
        "Column Description": "The SystemModstamp column contains the timestamp when the quote was last updated by the system, such as through automated processes or workflows.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "LastViewedDate",
        "Column Description": "The LastViewedDate column stores the timestamp when the quote was last viewed by any user. This helps track user interaction with the quote.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "LastReferencedDate",
        "Column Description": "The LastReferencedDate column contains the date when the quote was last referenced by any related object or process in Salesforce, such as a report or workflow.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "OpportunityId",
        "Column Description": "The OpportunityId column links the quote to a specific sales opportunity. This relationship allows users to track which opportunity the quote corresponds to and aids in quoting for specific deals.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "Pricebook2Id",
        "Column Description": "The Pricebook2Id column stores the ID of the pricebook associated with the quote. A pricebook contains a list of products and their prices, which are used to generate quotes.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "ContactId",
        "Column Description": "The ContactId column contains the ID of the contact associated with the quote. This helps in identifying the individual customer or client for whom the quote is created.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "QuoteNumber",
        "Column Description": "The QuoteNumber column stores the unique identifier for the quote. This value can be auto-generated or set by the user and is typically used in communication and tracking.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "IsSyncing",
        "Column Description": "The IsSyncing column is a boolean field that indicates whether the quote is in sync with an external system or is actively being updated in real-time.",
        "Type": "varchar(5)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "ShippingHandling",
        "Column Description": "The ShippingHandling column stores the cost of shipping and handling associated with the quote. This value is often added to the total quote price and is important for accurate billing.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "Tax",
        "Column Description": "The Tax column contains the tax amount applied to the quote. It is used in calculating the total price and ensures that taxes are properly accounted for in the pricing.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "Status",
        "Column Description": "The Status column indicates the current state of the quote, such as \"Draft,\" \"Sent,\" \"Accepted,\" or \"Expired.\" It helps sales teams manage the progression of quotes.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "ExpirationDate",
        "Column Description": "The ExpirationDate column holds the date when the quote expires. After this date, the quote may no longer be valid, and a new quote may need to be generated.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "Description",
        "Column Description": "The Description column stores additional details or notes about the quote. It can include terms and conditions, special instructions, or any other relevant information about the proposal.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "Subtotal",
        "Column Description": "The Subtotal column contains the sum of all line items on the quote before taxes and discounts. It is used to calculate the total price of the quote.",
        "Type": "float"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "TotalPrice",
        "Column Description": "The TotalPrice column stores the final price of the quote, including all taxes, discounts, shipping, and handling. It represents the total amount that will be charged to the customer.",
        "Type": "float"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "LineItemCount",
        "Column Description": "The LineItemCount column indicates the total number of line items included in the quote. This is important for understanding the complexity or size of the quote.",
        "Type": "int"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "BillingStreet",
        "Column Description": "The BillingStreet column stores the street address for billing. This is part of the full billing address and ensures that the quote is associated with the correct billing location.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "BillingCity",
        "Column Description": "The BillingCity column stores the city for the billing address of the quote. This is part of the address information used for invoicing and tax calculations.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "BillingState",
        "Column Description": "The BillingState column contains the state or province for the billing address. It is important for tax calculations and proper invoicing.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "BillingPostalCode",
        "Column Description": "The BillingPostalCode column holds the postal or ZIP code for the billing address. This is essential for delivering invoices and determining sales tax.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "BillingCountry",
        "Column Description": "The BillingCountry column stores the country for the billing address. This helps to determine applicable taxes and shipping costs, especially for international transactions.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "BillingLatitude",
        "Column Description": "The BillingLatitude column contains the latitude coordinate for the billing address. It is used in geolocation and mapping features to locate the billing address accurately.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "BillingLongitude",
        "Column Description": "The BillingLongitude column contains the longitude coordinate for the billing address. This, together with the latitude, provides geospatial information about the location.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "BillingGeocodeAccuracy",
        "Column Description": "The BillingGeocodeAccuracy column indicates the accuracy level of the geocoding for the billing address. This is important for precise location data, especially when working with location-based services or analytics.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "BillingAddress",
        "Column Description": "The BillingAddress column contains the full billing address, combining the street, city, state, postal code, and country for the quote\u0092s billing information.",
        "Type": "text"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "ShippingStreet",
        "Column Description": "The ShippingStreet column stores the street address for the shipping location. It is a part of the full shipping address used for delivery and logistics.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "ShippingCity",
        "Column Description": "The ShippingCity column contains the city for the shipping address. It is used to ensure that the shipment is routed to the correct city for delivery.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "ShippingState",
        "Column Description": "The ShippingState column holds the state or province for the shipping address. This is used in shipping calculations and determining tax rates.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "ShippingPostalCode",
        "Column Description": "The ShippingPostalCode column contains the postal or ZIP code for the shipping address. This is necessary for accurate delivery and routing.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "ShippingCountry",
        "Column Description": "The ShippingCountry column stores the country for the shipping address. This is used to determine shipping costs, taxes, and international logistics.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "ShippingLatitude",
        "Column Description": "The ShippingLatitude column contains the latitude for the shipping address. This data is used for geolocation and mapping purposes to improve delivery route planning.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "ShippingLongitude",
        "Column Description": "The ShippingLongitude column contains the longitude for the shipping address. This, along with latitude, provides exact geospatial information about the location.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "ShippingGeocodeAccuracy",
        "Column Description": "The ShippingGeocodeAccuracy column indicates the accuracy of the geocoding for the shipping address. This field is helpful in understanding how precise the shipping location data is.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "ShippingAddress",
        "Column Description": "The ShippingAddress column contains the complete shipping address, including street, city, state, postal code, and country, which is necessary for accurate shipping.",
        "Type": "text"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "QuoteToStreet",
        "Column Description": "The QuoteToStreet column stores the street address for the \"quote to\" location, which might be different from the billing or shipping address.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "QuoteToCity",
        "Column Description": "The QuoteToCity column holds the city for the \"quote to\" address, important for specific deliveries or quote purposes that are not tied to the billing or shipping address.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "QuoteToState",
        "Column Description": "The QuoteToState column contains the state or province for the \"quote to\" address. It is used in cases where the quote is intended for a specific location other than billing or shipping.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "QuoteToPostalCode",
        "Column Description": "The QuoteToPostalCode column holds the postal or ZIP code for the \"quote to\" address, which is relevant when the delivery or quote needs to go to a specific location.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "QuoteToCountry",
        "Column Description": "The QuoteToCountry column stores the country for the \"quote to\" address, which is important for determining the correct shipping or delivery route.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "QuoteToLatitude",
        "Column Description": "The QuoteToLatitude column contains the latitude for the \"quote to\" address. It is used for mapping and geolocation purposes.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "QuoteToLongitude",
        "Column Description": "The QuoteToLongitude column contains the longitude for the \"quote to\" address, which, along with latitude, provides precise geospatial information.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "QuoteToGeocodeAccuracy",
        "Column Description": "The QuoteToGeocodeAccuracy column indicates the accuracy level of the geocoding for the \"quote to\" address. This helps in determining the precision of the address data.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "QuoteToAddress",
        "Column Description": "The QuoteToAddress column stores the full \"quote to\" address, including the street, city, state, postal code, and country. This address may be used for a specific location relevant to the quote.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "AdditionalStreet",
        "Column Description": "The AdditionalStreet column stores any additional street address details for the quote. This can be used if there are extra details about the location or if the address is split across different lines.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "AdditionalCity",
        "Column Description": "The AdditionalCity column holds additional city details for the quote, in case the location information requires further breakdown.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "AdditionalState",
        "Column Description": "The AdditionalState column contains additional state or province information for the quote address if necessary for clarity or accuracy.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "AdditionalPostalCode",
        "Column Description": "The AdditionalPostalCode column stores additional postal or ZIP code details for the quote location, useful in cases where multiple areas are involved.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "AdditionalCountry",
        "Column Description": "The AdditionalCountry column holds any additional country details if the quote involves multiple countries or locations.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "AdditionalLatitude",
        "Column Description": "The AdditionalLatitude column contains additional latitude information for geolocation purposes, useful when the quote involves more than one location.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "AdditionalLongitude",
        "Column Description": "The AdditionalLongitude column stores additional longitude information, used in conjunction with latitude for more precise mapping or location details.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "AdditionalGeocodeAccuracy",
        "Column Description": "The AdditionalGeocodeAccuracy column indicates the accuracy of the geocoding for any additional address information that might be involved in the quote.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "AdditionalAddress",
        "Column Description": "The AdditionalAddress column contains the full additional address information, including street, city, state, postal code, and country, for situations where more than one address is needed for a quote.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "BillingName",
        "Column Description": "The BillingName column stores the name associated with the billing address. This is typically the customer or account name linked to the billing location.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "ShippingName",
        "Column Description": "The ShippingName column contains the name associated with the shipping address, often the customer or recipient of the goods being shipped.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "QuoteToName",
        "Column Description": "The QuoteToName column holds the name associated with the \"quote to\" address, which can be a special location or customer linked to the quote.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "AdditionalName",
        "Column Description": "The AdditionalName column stores the name linked to any additional address, typically used for identifying a secondary or alternative location.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "Email",
        "Column Description": "The Email column stores the email address associated with the quote, often used for communication regarding the quote or for sending the quote to the customer.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "Phone",
        "Column Description": "The Phone column contains the phone number for the contact associated with the quote. This is essential for customer support and follow-ups.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "Fax",
        "Column Description": "The Fax column stores the fax number, if applicable, for the contact related to the quote. This is less common but may still be used in certain industries.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "ContractId",
        "Column Description": "The ContractId column links the quote to an existing contract in Salesforce. This relationship helps track the contractual agreements associated with the quote.",
        "Type": "varchar(10)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "AccountId",
        "Column Description": "The AccountId column stores the ID of the account associated with the quote. This helps in linking the quote to a particular customer account in Salesforce.",
        "Type": "varchar(255)"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "Discount",
        "Column Description": "The Discount column contains the discount amount applied to the quote, either as a fixed value or percentage. It affects the total quote price.",
        "Type": "float"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "GrandTotal",
        "Column Description": "The GrandTotal column stores the final total of the quote after discounts, taxes, and additional charges have been applied. This is the amount the customer is expected to pay.",
        "Type": "float"
    },
    {
        "Table Name": "salesforce_quotes",
        "Table Description": "The salesforce_quotes table in Salesforce represents the quote records associated with opportunities and accounts. A quote is a formal offer or proposal for goods or services, typically containing detailed pricing, product configurations, discounts, and terms that are associated with a sales opportunity or account. Quotes are often used by sales teams to communicate proposed terms and pricing to clients before closing a deal. The salesforce_quotes table stores the information related to these quotes.",
        "Column Name": "CanCreateQuoteLineItems",
        "Column Description": "The CanCreateQuoteLineItems column is a boolean field that indicates whether the quote can have associated line items created. This is essential for managing what can be added to the quote in terms of products or services.",
        "Type": "varchar(5)"
    }
    ]
    
NS_prompt_template = """
You are the FinanceTranslationAgent, specializing in converting business financial requests into precise SQL queries. Your primary role is to translate structured financial questions into database queries that accurately retrieve the requested data while adhering to financial data modeling best practices.

## Primary Responsibilities:

1. **SQL Query Generation**:
   - Convert business financial requests into syntactically correct SQL queries.
   - Ensure queries are optimized for performance and accuracy.
   - Align queries with the database schema and table structures.
   - Handle complex financial calculations and aggregations within SQL.

2. **Financial Data Modeling**:
   - Understand financial data relationships and dependencies.
   - Navigate complex financial data schemas and chart of accounts.
   - Apply appropriate joins between financial tables based on their relationships.
   - Implement correct date filtering for financial periods.

3. **Query Validation and Error Checking**:
   - Validate generated SQL queries for syntax errors and logical flaws.
   - Check for common SQL mistakes specific to financial data:
     - Incorrect joining of financial tables
     - Improper handling of NULL values in financial calculations
     - Date range issues in financial period comparisons
     - Aggregation errors in financial summaries
   - Verify that the query will return the expected financial data format.

4. **Financial Calculation Implementation**:
   - Implement standard financial calculations in SQL:
     - Revenue and expense aggregations
     - Profit margin calculations
     - Growth rate computations
     - Financial ratios and KPIs
   - Handle complex financial scenarios like:
     - Year-to-date calculations
     - Period-over-period comparisons
     - Rolling averages and trends

5. **SQL Query Optimization for Financial Data**:
   - Optimize queries for financial reporting performance.
   - Implement efficient filtering for large financial datasets.
   - Use appropriate indexing strategies for financial queries.
   - Balance query complexity with performance considerations.

## SQL Query Validation Checklist:

Always validate SQL queries against these common issues:

1. **Syntax Issues**:
   - Correct SQL dialect syntax
   - Proper quoting of identifiers
   - Correct function usage and parameter count

2. **Logical Errors**:
   - Using NOT IN with NULL values
   - Using UNION when UNION ALL is appropriate
   - Using BETWEEN incorrectly for date ranges
   - Data type mismatches in predicates

3. **Financial Data Specifics**:
   - Correct handling of debits and credits
   - Proper balance sheet equation validation
   - Accurate income statement calculations
   - Correct cash flow statement structure

4. **Performance Considerations**:
   - Limiting result sets appropriately
   - Using indexes effectively
   - Avoiding unnecessary JOINs
   - Proper subquery placement

## SQL Query Templates for Financial Reports:

1. **Income Statement**:
```sql
SELECT 
    category,
    subcategory,
    SUM(amount) as total_amount
FROM financial_transactions
WHERE transaction_date BETWEEN [start_date] AND [end_date]
    AND category IN ('Revenue', 'Cost of Goods Sold', 'Operating Expenses')
GROUP BY category, subcategory
ORDER BY 
    CASE 
        WHEN category = 'Revenue' THEN 1
        WHEN category = 'Cost of Goods Sold' THEN 2
        WHEN category = 'Operating Expenses' THEN 3
    END, 
    subcategory;
```

2. **Balance Sheet**:
```sql
SELECT 
    account_type,
    account_category,
    account_name,
    SUM(CASE WHEN transaction_type = 'Debit' THEN amount ELSE -amount END) as balance
FROM general_ledger
WHERE transaction_date <= [balance_date]
GROUP BY account_type, account_category, account_name
ORDER BY 
    CASE 
        WHEN account_type = 'Asset' THEN 1
        WHEN account_type = 'Liability' THEN 2
        WHEN account_type = 'Equity' THEN 3
    END,
    account_category,
    account_name;
```

3. **Cash Flow Statement**:
```sql
SELECT 
    cash_flow_activity,
    cash_flow_category,
    SUM(amount) as amount
FROM cash_flow_transactions
WHERE transaction_date BETWEEN [start_date] AND [end_date]
GROUP BY cash_flow_activity, cash_flow_category
ORDER BY 
    CASE 
        WHEN cash_flow_activity = 'Operating' THEN 1
        WHEN cash_flow_activity = 'Investing' THEN 2
        WHEN cash_flow_activity = 'Financing' THEN 3
    END,
    cash_flow_category;
```

## Process Flow:

1. Receive structured financial request from BusinessFunctionAgent
2. Analyze the database schema for relevant tables and relationships
3. Construct appropriate SQL query based on the financial request
4. Validate the query against common SQL errors and financial data modeling best practices
5. Optimize the query for performance
6. Return the validated SQL query to the SupervisorAgent

### Table Info:
{ns_table_info}

### Examples:
{retrieved_content}

### Context:
{chat_history}

Generate SQL for:
{input_text}
"""
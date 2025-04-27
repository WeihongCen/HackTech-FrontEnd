from agents import Agent, Runner, function_tool
from openai import OpenAI
from openai.types.responses import ResponseTextDeltaEvent
import time
import requests
from dotenv import load_dotenv
load_dotenv()

client_openai = OpenAI()
SCHEMA_DESCRIPTION = """
We have a procurement database with the following tables:

**Table 1: dispatch_parameters**
Description: This table contains information about the minimum stock levels, reorder quantities, and reorder intervals for different parts.
Columns:
- part_id
- min_stock_level
- reorder_quantity
- reorder_interval_days

**Table 2: material_master**
Description: This table provides detailed information about each part, including its name, type, models it is used in, dimensions, weight, and any related parts.
Columns:
- part_id
- part_name
- part_type
- used_in_models
- weight
- blocked_parts
- successor_parts
- comment

**Table 3: material_orders**
Description: This table records purchase orders for parts, including order details, supplier information, and delivery status.
Columns:
- order_id
- part_id
- quantity_ordered
- order_date
- expected_delivery_date
- supplier_id
- status
- actual_delivered_at

**Table 4: sales_orders**
Description: This table contains information about sales orders, including the model, version, quantity, order type, and dates related to the order process.
Columns:
- sales_order_id
- model
- version
- quantity
- order_type
- requested_date
- created_at
- accepted_request_date

**Table 5: stock_levels**
Description: This table provides the current inventory levels of parts in different warehouse locations.
Columns:
- part_id
- part_name
- location
- quantity_available

**Table 6: stock_movements**
Description: This table records transactions related to inventory movements, including inbound and outbound quantities.
Columns:
- date
- part_id
- type
- quantity

**Table 7: suppliers**
Description: This table contains information about suppliers, including pricing, lead times, minimum order quantities, and reliability ratings for different parts.
Columns:
- supplier_id
- part_id
- price_per_unit
- lead_time_days
- min_order_qty
- reliability_rating

**Table 7: specs**
Description: This table contains information about the required parts to assemble a product, including the part name and the quantity required.
Columns:
- product_id
- product_name
- part_id
- quantity
"""


@function_tool
def modify_database(user_input: str) -> str:
    try:
        response = requests.post(
            "http://localhost:5000/modify",
            json={"user_input": user_input},
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            return f"Success: Changed {result.get('modified_rows', 0)} rows."
        else:
            return f"Failed: {response.text}"
    except Exception as e:
        return f"Error contacting database server: {str(e)}"

# def find_relevant_tables(client_openai, user_input):


@function_tool
def query_database(user_input: str) -> str:
    print("Finding relevant tables")
    prompt = f"""
    {SCHEMA_DESCRIPTION}

    Based on the schema above and the user input below:
    {user_input}

    Your task is to:
    - Identify which tables from the schema are relevant to answer the user's request.
    - For each relevant table, output:
      - `table_name`: the exact name of the table
      - `reason`: a short explanation (1-2 sentences) why this table is relevant

    Important rules:
    - Only pick tables defined in the schema.
    - If no table fits, return an empty list.
    - Do not invent or guess missing tables.
    - Keep your reasoning clear and concise.

    Format your final response as a list of objects, like:
    [
      {"table_name": "material_master", "reason": "Contains information about materials and parts."},
      {"table_name": "suppliers", "reason": "Lists suppliers which may be needed for material sourcing."}
    ]
    """
    print("finished1")
    completion = client_openai.chat.completions.create(
        model="gpt-4-1-2025-04-14",
        response_format="json",
        messages=[
            {
                "role": "system",
                "content": """
                You are a database assistant. Your job is to accurately map user queries to existing database tables based on a given schema description. 
                Only use the provided tables, and explain relevance clearly.
                """
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    print("finished")
    tables = completion.choices[0].message.content
    print(tables)
    return tables


agent = Agent(
    name="Database agent",
    instructions="You are a database agent.",
    tools=[query_database],
)

def database_agent(user_input: str):
    result = Runner.run(agent, input=user_input)
    print(result.final_output)
    return "result.final_output"
    # async for event in result.stream_events():
    #     if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
    #         if event.data.delta:
    #             yield event.data.delta
    # # result = await Runner.run(agent, input=user_input)
    # # return result.final_output
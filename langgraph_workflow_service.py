from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
import os
from dotenv import load_dotenv

load_dotenv()

class LeadResponseState(TypedDict):
    lead_name: str
    budget: int
    service_type: str
    last_message: str
    history: List[dict]
    generated_reply: str

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.7,
    api_key=os.getenv("GROQ_API_KEY")
)

def generate_conversation_reply(state: LeadResponseState) -> LeadResponseState:
    is_new_lead = len(state['history']) == 0
    
    formatted_history = "\n".join([
        f"{m.get('sender', 'Unknown').upper()}: {m.get('message', '')}" 
        for m in state['history']
    ])
    
    system_prompt = f"""
    You are a professional Senior Sales Executive for a premium AI Automation Agency.
    Your goal is to be helpful, concise, and book a discovery meeting.
    
    LEAD CONTEXT:
    - Name: {state['lead_name']}
    - Project: {state['service_type']}
    - Budget: ${state['budget']:,}
    
    INSTRUCTIONS:
    {"This is your FIRST outreach. Introduce our agency and mention how we can help with their project." if is_new_lead else "This is a REPLY to an ongoing conversation. Answer their specific points using the history."}
    
    RULES:
    - Keep it under 4 sentences.
    - If budget > $10,000, offer a direct link for a 1-on-1 strategy call.
    - Always end with a clear next step (Question or Meeting request).
    """

    human_content = f"""
    Conversation History:
    {formatted_history if not is_new_lead else "None - This is the start of the relationship."}
    
    {"The lead just said: " + state['last_message'] if not is_new_lead else "Generate a personalized opening email based on their interest."}
    
    Write the email now:
    """

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_content)
    ]
    
    response = llm.invoke(messages)
    state['generated_reply'] = response.content
    return state

def create_response_workflow():
    workflow = StateGraph(LeadResponseState)
    workflow.add_node("generate_reply", generate_conversation_reply)
    workflow.set_entry_point("generate_reply")
    workflow.add_edge("generate_reply", END)
    return workflow.compile()

def process_lead_reply(lead_data: dict, history: List[dict]) -> str:
    workflow = create_response_workflow()
    
    initial_state: LeadResponseState = {
        "lead_name": lead_data.get("name", "Valued Client"),
        "budget": lead_data.get("budget", 0),
        "service_type": lead_data.get("service_type", "AI Services"),
        "last_message": lead_data.get("last_message", ""),
        "history": history,
        "generated_reply": ""
    }
    
    result = workflow.invoke(initial_state)
    return result["generated_reply"]
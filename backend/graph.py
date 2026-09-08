from langgraph.graph import END, START, StateGraph

from backend.agents import planning_agent, reasoning_agent, retrieval_agent, risk_agent


workflow = StateGraph(dict)
workflow.add_node("planning", planning_agent)
workflow.add_node("retrieval", retrieval_agent)
workflow.add_node("reasoning", reasoning_agent)
workflow.add_node("risk", risk_agent)

workflow.add_edge(START, "planning")
workflow.add_edge("planning", "retrieval")
workflow.add_edge("retrieval", "reasoning")
workflow.add_edge("reasoning", "risk")
workflow.add_edge("risk", END)

orca_agent = workflow.compile()

__all__ = ["orca_agent"]

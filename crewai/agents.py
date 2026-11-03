from crewai import Agent, Crew, Task, Process, LLM
from config import OLLAMA_BASE_URL, MODEL_MAIN, MODEL_CODER, MODEL_LIGHT
from tools import n8n_webhook_tool, qdrant_search_tool, database_query_tool


def _llm(model: str) -> LLM:
    return LLM(model=f"ollama/{model}", base_url=OLLAMA_BASE_URL)


planning_agent = Agent(
    role="Planner",
    goal="Turn the user's goal (a project, a busy week, a build) into a short, doable plan",
    backstory=("You are CHAR9000's planner: a friendly organizer who breaks big things into small steps, "
               "spots deadlines and dependencies, and always ends with one clear next action."),
    llm=_llm(MODEL_MAIN),
    verbose=True,
)

research_agent = Agent(
    role="Researcher",
    goal="Find accurate information in the user's personal knowledge base and explain it simply",
    backstory=("You search the user's own documents (Qdrant collection 'my_documents') and cite which file "
               "each fact came from. If the answer isn't there, you say so instead of guessing."),
    llm=_llm(MODEL_MAIN),
    tools=[qdrant_search_tool, database_query_tool],
    verbose=True,
)

coding_agent = Agent(
    role="Build Partner",
    goal="Help with technical builds: code, scripts, electronics and AI projects, explained step by step",
    backstory=("You are a patient engineer and teacher. You write clean, commented code, explain why it works, "
               "suggest how to test it, and flag safety issues (mains power, batteries, tools)."),
    llm=_llm(MODEL_CODER),
    tools=[database_query_tool],
    verbose=True,
)

execution_agent = Agent(
    role="Executor",
    goal="Run the user's n8n automations, only after she has approved the specific action",
    backstory=("You trigger n8n workflows for reminders, routines and projects. You never run a workflow that "
               "changes, deletes, sends or buys anything unless the request explicitly says she approved it."),
    llm=_llm(MODEL_LIGHT),
    tools=[n8n_webhook_tool],
    verbose=True,
)


def build_crew(user_message: str) -> Crew:
    task = Task(
        description=user_message,
        expected_output="A clear, friendly answer or plan, ending with the next step.",
        agent=planning_agent,
    )
    return Crew(
        agents=[planning_agent, research_agent, coding_agent, execution_agent],
        tasks=[task],
        process=Process.hierarchical,
        manager_llm=_llm(MODEL_MAIN),
        verbose=True,
    )

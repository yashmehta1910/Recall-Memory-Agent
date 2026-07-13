"""Graphs that extract memories on a schedule."""
import asyncio
import logging
from datetime import datetime
from typing import cast

from langgraph.graph import END, StateGraph
from langgraph.runtime import Runtime
from langgraph.store.base import BaseStore

from memory_agent import tools, utils
from memory_agent.context import Context
from memory_agent.state import State

logger = logging.getLogger(__name__)


async def call_model(state: State, runtime: Runtime[Context]) -> dict:
    """Extract the user's state from the conversation and update the memory."""
    user_id = runtime.context.user_id
    model = runtime.context.model
    system_prompt = runtime.context.system_prompt

    # Retrieve the most recent memories for context
    memories = await cast(BaseStore, runtime.store).asearch(
        ("memories", user_id),
        query=str([m.content for m in state.messages[-3:]]),
        limit=10,
    )

    # Format memories for inclusion in the prompt
    formatted = "\n".join(
        f"[{mem.key}]: {mem.value} (similarity: {mem.score})" for mem in memories
    )
    if formatted:
        formatted = f"""
<memories>
{formatted}
</memories>"""

    # Prepare the system prompt with user memories and current time
    # This helps the model understand the context and temporal relevance
    sys = system_prompt.format(user_info=formatted, time=datetime.now().isoformat())

    # Load the chat model from the runtime context
    llm = utils.load_chat_model(model)

    msg = await llm.bind_tools([
        tools.upsert_memory,
        tools.play_music_on_youtube,
        tools.get_weather,
        tools.web_search,
        tools.tell_joke,
        tools.add_reminder,
        tools.list_reminders,
        tools.get_news,
        tools.convert_currency,
    ]).ainvoke(
        [{"role": "system", "content": sys}, *state.messages]
    )
    return {"messages": [msg]}

async def store_memory(state: State, runtime: Runtime[Context]):
    tool_calls = getattr(state.messages[-1], "tool_calls", [])

    async def run_tool(tc):
        name = tc["name"]
        args = tc["args"]
        user_id = runtime.context.user_id
        store = cast(BaseStore, runtime.store)

        if name == "upsert_memory":
            return await tools.upsert_memory(**args, user_id=user_id, store=store)
        elif name == "add_reminder":
            return await tools.add_reminder(**args, user_id=user_id, store=store)
        elif name == "list_reminders":
            return await tools.list_reminders(user_id=user_id, store=store)
        elif name == "play_music_on_youtube":
            return await asyncio.to_thread(tools.play_music_on_youtube, **args)
        elif name == "get_weather":
            return await asyncio.to_thread(tools.get_weather, **args)
        elif name == "web_search":
            return await asyncio.to_thread(tools.web_search, **args)
        elif name == "tell_joke":
            return await asyncio.to_thread(tools.tell_joke)
        elif name == "get_news":
            return await asyncio.to_thread(tools.get_news, **args)
        elif name == "convert_currency":
            return await asyncio.to_thread(tools.convert_currency, **args)
        else:
            return f"Unknown tool: {name}"

    saved_results = await asyncio.gather(*(run_tool(tc) for tc in tool_calls))

    results = [
        {
            "role": "tool",
            "content": result,
            "tool_call_id": tc["id"],
        }
        for tc, result in zip(tool_calls, saved_results)
    ]
    return {"messages": results}


def route_message(state: State):
    """Determine the next step based on the presence of tool calls."""
    msg = state.messages[-1]
    if getattr(msg, "tool_calls", None):
        # If there are tool calls, we need to store memories
        return "store_memory"
    # Otherwise, finish; user can send the next message
    return END


# Create the graph + all nodes
builder = StateGraph(State, context_schema=Context)

# Define the flow of the memory extraction process
builder.add_node(call_model)
builder.add_edge("__start__", "call_model")
builder.add_node(store_memory)
builder.add_conditional_edges("call_model", route_message, ["store_memory", END])
# Right now, we're returning control to the user after storing a memory
# Depending on the model, you may want to route back to the model
# to let it first store memories, then generate a response
builder.add_edge("store_memory", "call_model")
graph = builder.compile()
graph.name = "MemoryAgent"


__all__ = ["graph"]

"""Define he agent's tools."""

import uuid
from typing import Annotated

from langchain_core.tools import InjectedToolArg
from langgraph.store.base import BaseStore
import re
import requests
import webbrowser
import json
import xml.etree.ElementTree as ET


def get_news(topic: str = "world") -> str:
    """Get top news headlines for a topic using Google News RSS (free, no key)."""
    try:
        url = f"https://news.google.com/rss/search?q={topic}&hl=en-IN&gl=IN&ceid=IN:en"
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        root = ET.fromstring(resp.content)
        items = root.findall(".//item")[:5]

        if not items:
            return f"No news found for '{topic}'."

        headlines = [item.find("title").text for item in items]
        return f"Top headlines for '{topic}':\n" + "\n".join(f"- {h}" for h in headlines)
    except Exception as e:
        return f"Couldn't fetch news: {e}"


def convert_currency(amount: float, from_currency: str, to_currency: str) -> str:
    """Convert an amount from one currency to another using free Frankfurter API."""
    try:
        url = f"https://api.frankfurter.dev/v1/latest?base={from_currency.upper()}&symbols={to_currency.upper()}"
        resp = requests.get(url, timeout=15)
        data = resp.json()
        rate = data["rates"][to_currency.upper()]
        converted = amount * rate
        return f"{amount} {from_currency.upper()} = {converted:.2f} {to_currency.upper()}"
    except Exception as e:
        return f"Couldn't convert currency: {e}"


def get_weather(city: str) -> str:
    """Get current weather for a city using Open-Meteo (free, no API key)."""
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
        geo_resp = requests.get(geo_url, headers=headers, timeout=15)

        if geo_resp.status_code != 200 or not geo_resp.text.strip():
            return f"Weather service returned an empty response (status {geo_resp.status_code}). Try again."

        geo = geo_resp.json()
        if not geo.get("results"):
            return f"Couldn't find location '{city}'."

        lat = geo["results"][0]["latitude"]
        lon = geo["results"][0]["longitude"]
        place_name = geo["results"][0]["name"]

        weather_url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}&current_weather=true"
        )
        weather_resp = requests.get(weather_url, headers=headers, timeout=15)

        if weather_resp.status_code != 200 or not weather_resp.text.strip():
            return f"Weather service returned an empty response (status {weather_resp.status_code}). Try again."

        weather = weather_resp.json()
        temp = weather["current_weather"]["temperature"]
        wind = weather["current_weather"]["windspeed"]

        return f"Weather in {place_name}: {temp}°C, wind {wind} km/h."

    except Exception as e:
        return f"Couldn't fetch weather: {e}"

def web_search(query: str) -> str:
    """Quick fact lookup using DuckDuckGo's free instant answer API."""
    try:
        url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1"
        data = requests.get(url, timeout=10).json()
        abstract = data.get("AbstractText")
        if abstract:
            return abstract
        related = data.get("RelatedTopics")
        if related and isinstance(related, list) and len(related) > 0:
            first = related[0]
            if isinstance(first, dict) and "Text" in first:
                return first["Text"]
        return f"No quick answer found for '{query}'."
    except Exception as e:
        return f"Search failed: {e}"


def tell_joke() -> str:
    """Fetch a random joke from a free public API."""
    try:
        data = requests.get(
            "https://official-joke-api.appspot.com/random_joke", timeout=10
        ).json()
        return f"{data['setup']} ... {data['punchline']}"
    except Exception as e:
        return f"Couldn't fetch a joke: {e}"

async def add_reminder(
    task: str,
    *,
    user_id: Annotated[str, InjectedToolArg],
    store: Annotated[BaseStore, InjectedToolArg],
) -> str:
    """Save a reminder/to-do item for the user.

    Args:
        task: The reminder text, e.g. "Submit assignment by Friday".
    """
    from uuid import uuid4

    namespace = ("reminders", user_id)
    key = str(uuid4())
    await store.aput(namespace, key, {"task": task})
    return f"Added reminder: {task}"


async def list_reminders(
    *,
    user_id: Annotated[str, InjectedToolArg],
    store: Annotated[BaseStore, InjectedToolArg],
) -> str:
    """List all saved reminders for the user."""
    namespace = ("reminders", user_id)
    items = await store.asearch(namespace)
    if not items:
        return "You have no reminders saved."
    tasks = [item.value["task"] for item in items]
    return "Your reminders:\n" + "\n".join(f"- {t}" for t in tasks)

def play_music_on_youtube(song_name: str) -> str:
    """Search YouTube for a song and play the first result in the browser."""
    query = song_name.replace(" ", "+")
    search_url = f"https://www.youtube.com/results?search_query={query}"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    try:
        html = requests.get(search_url, headers=headers, timeout=10).text
    except Exception as e:
        return f"Error reaching YouTube: {e}"

    video_ids = re.findall(r"\"videoId\":\"(.{11})\"", html)

    if not video_ids:
        return f"Couldn't find '{song_name}' on YouTube."

    video_url = f"https://www.youtube.com/watch?v={video_ids[0]}"
    webbrowser.open(video_url)
    return f"Now playing '{song_name}' on YouTube."


async def upsert_memory(
    content: str,
    context: str,
    *,
    memory_id: uuid.UUID | None = None,
    # Hide these arguments from the model.
    user_id: Annotated[str, InjectedToolArg],
    store: Annotated[BaseStore, InjectedToolArg],
):
    """Upsert a memory in the database.

    If a memory conflicts with an existing one, then just UPDATE the
    existing one by passing in memory_id - don't create two memories
    that are the same. If the user corrects a memory, UPDATE it.

    Args:
        content: The main content of the memory. For example:
            "User expressed interest in learning about French."
        context: Additional context for the memory. For example:
            "This was mentioned while discussing career options in Europe."
        memory_id: ONLY PROVIDE IF UPDATING AN EXISTING MEMORY.
        The memory to overwrite.
    """
    mem_id = memory_id or uuid.uuid4()
    await store.aput(
        ("memories", user_id),
        key=str(mem_id),
        value={"content": content, "context": context},
    )
    return f"Stored memory {mem_id}"

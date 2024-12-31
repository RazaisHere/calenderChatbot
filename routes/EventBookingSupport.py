from flask import Blueprint, request, jsonify
import requests
from datetime import datetime
from openai import AzureOpenAI
from Helpers.PromptHelper import PromptHelper
from Helpers.OpenAIDocSearch.Approaches.Approach import Approach
from config.ExternalConfiguration import ExternalConfiguration

import logging
import requests

class EventBookingSupport(Approach):
    config = ExternalConfiguration()

    prompt_prefix = """
        You are a helpful assistant for event bookings.
        If the user asks about their events or schedule, you should provide them with the upcoming events from the system.
        Please note, the information is fetched from the event API, and your task is to summarize the events clearly.
        If the question is not related to events, proceed with the normal conversation flow.
    """

    result_prompt = """
        You are assisting with event bookings. The result of the user's query is provided in JSON format.
        {result}
        Please respond with a human-friendly summary of the events or relevant response.
    """

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_eventList",
                "description": "Fetch the list of scheduled events for the user.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                    "additionalProperties": False,
                },
            }
        }
    ]

    def __init__(self, chatgpt_deployment: str, gpt_deployment: str, content_field: str):
        self.chatgpt_deployment = chatgpt_deployment
        self.gpt_deployment = gpt_deployment
        self.content_field = content_field
        self.client = AzureOpenAI(azure_endpoint=self.config.OPENAI_ENDPOINT, api_key=self.config.OPENAI_APIKEY, api_version=self.config.OPENAI_VERSION)
        self.config = ExternalConfiguration()

    def run(self, summary, overrides: dict) -> any:
        use_semantic_captions = True if overrides.get("semantic_captions") else False
        exclude_category = overrides.get("exclude_category") or None
        filter = (
            "category ne '{}'".format(exclude_category.replace("'", "''"))
            if exclude_category
            else None
        )
        history = self.get_chat_history_as_text(summary, include_last_turn=False)

        completion = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": history},
                      {"role": "system", "content": self.prompt_prefix},
                      {"role": "user", "content": summary[-1].user_message}],
            tools=self.tools
        )
        response = {"answer": completion.choices[0].message.content}
        response["data_points"] = self.get_chat_history_as_text(summary, include_last_turn=False)
        
        return response

    def get_chat_history_as_text(self, history, include_last_turn=True, approx_max_tokens=2000) -> str:
        history_text = ""
        for h in reversed(history if include_last_turn else history[:-1]):
            history_text += """<|im_start|>""" + "\n" + str(h.user_message) + "\n" + """<|im_end|>""" + "\n" + """<|im_start|>""" + "\n" + (h.bot_message if h.bot_message is not None else "") + "\n"
            if len(history_text) > approx_max_tokens * 4:
                break
        return history_text

    def get_event_list(self) -> list:
        try:
            # Update with the correct Flask URL
            response = requests.get('http://127.0.0.1:5000/api/get_eventList')  # Use actual URL
            if response.status_code == 200:
                events = response.json().get('data', [])
                return events
            else:
                return {"error": f"Failed to fetch events: {response.status_code}"}
        except Exception as e:
            logging.error(f"Failed to fetch events: {str(e)}")
            return {"error": f"Failed to fetch events: {str(e)}"}

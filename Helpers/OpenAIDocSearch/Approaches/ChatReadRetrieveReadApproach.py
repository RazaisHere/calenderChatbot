from datetime import datetime, timedelta
import pytz
import os
import requests
from openai import AzureOpenAI
from config.ExternalConfiguration import ExternalConfiguration
import re
import json

class ChatReadRetrieveReadApproach:
    config = ExternalConfiguration()

    prompt_prefix = """
        You are a helpful assistant for appointment booking. When the user asks for events, try to understand the specific request.
        If the user asks for upcoming events, fetch events that are scheduled for the future.
        If the user asks for events tomorrow, fetch events scheduled for the next day.
        If the user asks for events next week, fetch events scheduled within the next 7 days.
        
        Additionally, if a user wants to create an event, ask for the necessary details such as:
        - Summary
        - Description
        - Start time (in 'YYYY-MM-DD hh:mm AM/PM' format)
        - End time (in 'YYYY-MM-DD hh:mm AM/PM' format)
        save the same time as it is provided from user. i mean if he provides the 09:00 AM time from any time zone save the same time for the calender time zone i.e 09:00 AM
        Respond in a conversational format, for example:
        - "You have the following upcoming events: Event 1, Event 2, Event 3"
        - "Here are the events scheduled for tomorrow: Event 1 at 3:00 PM"
        - "These are the events happening next week: Event 1 on Monday, Event 2 on Thursday"
        - "Creating an event titled 'Meeting' starting on '2024-12-18 10:00 AM' and ending at '2024-12-18 11:00 AM'."
        
        Avoid showing raw JSON data. Format the events clearly.
    """

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_event_list",
                "description": "Fetch the list of events from Google Calendar API",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_events_by_date_range",
                "description": "Fetch the events from Google Calendar API within a specified date range",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "start_date": {
                            "type": "string",
                            "description": "The start date in ISO 8601 format (e.g., '2024-12-18T00:00:00Z')."
                        },
                        "end_date": {
                            "type": "string",
                            "description": "The end date in ISO 8601 format (e.g., '2024-12-25T23:59:59Z')."
                        }
                    },
                    "required": ["start_date", "end_date"]
                }
            }
        },
        {
    "type": "function",
    "function": {
        "name": "create_event",
        "description": "Create an event in Google Calendar.",
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "The event summary."
                },
                "description": {
                    "type": "string",
                    "description": "The event description."
                },
                "start": {
                    "type": "string",
                    "description": "The start time in 'YYYY-MM-DD hh:mm AM/PM' format . use pakistan time zone"
                },
                "end": {
                    "type": "string",
                    "description": "The end time in 'YYYY-MM-DD hh:mm AM/PM' format. use pakistan time zone"
                }
            },
            "required": ["summary", "start", "end"]
        }
    }
}
    ]

    def __init__(self, chatgpt_deployment: str, gpt_deployment: str, content_field: str):
        self.chatgpt_deployment = chatgpt_deployment
        self.gpt_deployment = gpt_deployment
        self.content_field = content_field
        self.client = AzureOpenAI(
            azure_endpoint=self.config.OPENAI_ENDPOINT,
            api_key=self.config.OPENAI_APIKEY,
            api_version=self.config.OPENAI_VERSION
        )

    def run(self, summary, overrides: dict) -> any:
        history = self.get_chat_history_as_text(summary, include_last_turn=False)

        # Chat completion request with tools
        completion = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": self.prompt_prefix},
                {"role": "system", "content": history},
                {"role": "user", "content": summary[-1].user_message},
            ],
            tools=self.tools,
        )

        response = {"answer": ""}
        tool_calls = completion.choices[0].message.tool_calls

        # Debugging line to inspect tool_calls
        print("Tool Calls:", tool_calls)

        if tool_calls:
            for tool in tool_calls:
                function_name = tool.function.name
                
                if function_name == "get_event_list":
                    events_response = self.get_event_list()
                    response["answer"] = f"{events_response}"

                elif function_name == "get_events_by_date_range":
                    start_date, end_date = self.extract_dates(summary[-1].user_message)
                    if start_date and end_date:
                        events_response = self.get_events_by_date_range(start_date, end_date)
                        response["answer"] = f"{events_response}"
                    else:
                        single_date = self.extract_single_date(summary[-1].user_message)
                        if single_date:
                            events_response = self.get_events_by_single_date(single_date)
                            response["answer"] = f"{events_response}"
                        else:
                            response["answer"] = "Please provide a valid date range or a specific date."

                elif function_name == "create_event":
                    # Accessing parameters directly
                    parameters = tool.function.arguments  # This contains the JSON string
                    event_data = json.loads(parameters)  # Parse the JSON string

                    summary = event_data.get('summary')
                    if summary:
                        # Validate required fields
                        if all(event_data.get(key) for key in ['summary', 'start', 'end']):
                            event_creation_response = self.create_event(event_data)
                            response["answer"] = event_creation_response
                        else:
                            response["answer"] = "Summary, start, and end times are required to create an event."
                    else:
                        response["answer"] = "Event summary is required."

        else:
            response["answer"] = completion.choices[0].message.content

        return response
    @staticmethod
    def extract_dates(question):
        """
        Extracts the start and end dates from the user's question.
        Returns the dates as strings in ISO 8601 format (YYYY-MM-DD).
        """
        date_pattern = r"(\b(?:\w{3,9}\s\d{1,2},\s\d{4})\b)"
        dates = re.findall(date_pattern, question)

        if len(dates) >= 2:
            try:
                start_date = datetime.strptime(dates[0], "%b %d, %Y").date()
                end_date = datetime.strptime(dates[1], "%b %d, %Y").date()
                return start_date.isoformat(), end_date.isoformat()
            except ValueError:
                return None, None
        return None, None

    def get_event_list(self):
        try:
            response = requests.get("http://localhost:5000/api/get_eventList")
            if response.status_code == 200:
                events = response.json().get("data", [])
                if isinstance(events, list): 
                    return self.format_events(events)
                else:
                    return "Invalid data format received."
            else:
                return f"Failed to fetch events. Status code: {response.status_code}"
        except Exception as e:
            return f"Error fetching events: {str(e)}"

    def format_events(self, events):
        if not events:
            return "No events found."
        formatted_events = ", ".join(
            f"{event.get('summary', 'No Title')} on {self.format_date(event.get('start', {}).get('dateTime', 'No Date'))}"
            for event in events
        )
        return f"You have the following events: {formatted_events}"

    def format_date(self, date_string):
        try:
            date_obj = datetime.fromisoformat(date_string)
            return date_obj.strftime("%B %d, %Y")
        except ValueError:
            return date_string

    def get_upcoming_events(self):
        events = self.get_event_list_from_api()
        upcoming_events = [event for event in events if self.is_upcoming(event)]
        return self.format_events(upcoming_events)

    def get_events_for_tomorrow(self):
        events = self.get_event_list_from_api()
        tomorrow_events = [event for event in events if self.is_tomorrow(event)]
        return self.format_events(tomorrow_events)

    def get_events_next_week(self):
        events = self.get_event_list_from_api()
        next_week_events = [event for event in events if self.is_next_week(event)]
        return self.format_events(next_week_events)

    def get_event_list_from_api(self):
        try:
            response = requests.get("http://localhost:5000/api/get_eventList")
            if response.status_code == 200:
                return response.json().get("data", [])
            else:
                return []
        except Exception as e:
            return []

    def is_upcoming(self, event):
        start_date = event.get('start', {}).get('dateTime', None)
        if start_date:
            start_date = datetime.fromisoformat(start_date)
            return start_date > datetime.now(pytz.utc)
        return False

    def is_tomorrow(self, event):
        start_date = event.get('start', {}).get('dateTime', '')
        tomorrow = datetime.now() + timedelta(days=1)
        return self.is_same_day(start_date, tomorrow)

    def is_next_week(self, event):
        start_date = event.get('start', {}).get('dateTime', '')
        next_week = datetime.now() + timedelta(weeks=1)
        return self.is_same_week(start_date, next_week)

    def is_same_day(self, date_str, date_to_check):
        try:
            event_date = datetime.fromisoformat(date_str)
            return event_date.date() == date_to_check.date()
        except:
            return False

    def is_same_week(self, date_str, date_to_check):
        try:
            event_date = datetime.fromisoformat(date_str)
            return event_date.isocalendar()[1] == date_to_check.isocalendar()[1]
        except:
            return False

    def get_chat_history_as_text(self, history, include_last_turn=True, approx_max_tokens=2000) -> str:
        history_text = ""
        for h in reversed(history if include_last_turn else history[:-1]):
            history_text = (
                """<|im_start|>"""
                + "\n"
                + str(h.user_message)
                + "\n"
                + """<|im_start|>assistant"""
                + "\n"
                + (h.bot_message if h.bot_message is not None else "")
                + "\n"
                + history_text
            )
            if len(history_text) > approx_max_tokens * 4:
                break
        return history_text

    def get_events_by_date_range(self, start_date, end_date):
        try:
            response = requests.get("http://localhost:5000/api/get_eventList")
            if response.status_code == 200:
                events = response.json().get("data", [])
                filtered_events = [
                    event for event in events
                    if self.is_event_within_range(event, start_date, end_date)
                ]
                return self.format_events(filtered_events)
            else:
                return f"Failed to fetch events. Status code: {response.status_code}"
        except Exception as e:
            return f"Error fetching events by date range: {str(e)}"

    def is_event_within_range(self, event, start_date, end_date):
        event_start = event.get("start", {}).get("dateTime", "")
        if event_start:
            event_start_date = datetime.fromisoformat(event_start)

            # Ensure start_date and end_date are datetime objects with UTC timezone (offset-aware)
            start_date_obj = datetime.fromisoformat(start_date) if isinstance(start_date, str) else start_date
            end_date_obj = datetime.fromisoformat(end_date) if isinstance(end_date, str) else end_date

            # Convert to UTC if they are naive
            if start_date_obj.tzinfo is None:
                start_date_obj = pytz.utc.localize(start_date_obj)
            if end_date_obj.tzinfo is None:
                end_date_obj = pytz.utc.localize(end_date_obj)

            # Check if the event is within the given date range
            return start_date_obj <= event_start_date <= end_date_obj
        return False 
    
    def create_event(self, data):
        try:
            # Construct the payload
            payload = {
                "summary": data['summary'],
                "description": data.get('description', ""),
                "start": data['start'],  # 'YYYY-MM-DD hh:mm AM/PM'
                "end": data['end']  # 'YYYY-MM-DD hh:mm AM/PM'
            }
            print("start time ----------------------",payload['start'])

            # Send a POST request to the create_event endpoint
            response = requests.post("http://localhost:5000/api/create_event", json=payload)

            if response.status_code == 201:
                return "Event created successfully!"
            else:
                return f"Failed to create event. Status code: {response.status_code}, Error: {response.json().get('error', 'No error message')}"
        except Exception as e:
            return f"Error creating event: {str(e)}"
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os
from datetime import datetime
import pytz
from flask import Flask, Blueprint, request, jsonify

SCOPES = ['https://www.googleapis.com/auth/calendar']
API_KEY = 'AIzaSyDe9oizvZouhDxVD3jmK2LQ-3bugIzb9v4'  # Use your API key here

# Function to convert user input to datetime in 'yyyy-mm-dd hh:mm AM/PM' format
def convert_to_datetime(user_input):
    try:
        # Convert the string input to a datetime object
        event_time = datetime.strptime(user_input, '%Y-%m-%d %I:%M %p')

        # Specify the timezone (you can change this to your local timezone)
        timezone = pytz.timezone('America/Los_Angeles')

        # Convert the datetime to the desired timezone
        event_time = timezone.localize(event_time)

        # Return the ISO 8601 format for Google Calendar API
        return event_time.isoformat()
    except ValueError:
        print("Invalid time format. Please use 'yyyy-mm-dd hh:mm AM/PM'.")
        return None

# Function to authenticate and get credentials for OAuth
def authenticate():
    """Authenticate and return valid Google Calendar API credentials."""
    creds = None
    current_dir = os.path.dirname(os.path.abspath(__file__))
    client_secret_path = os.path.join(current_dir, 'client_secret.json')
    token_path = os.path.join(current_dir, 'token.json')

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    # Refresh or get new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(client_secret_path):
                raise FileNotFoundError(f"client_secret.json not found at: {client_secret_path}")
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
            creds = flow.run_local_server(port=8080)

        # Save the new token
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    return creds

# Function to initialize the Google Calendar API service for API Key
def get_calendar_service_with_apikey():
    """Initialize and return Google Calendar API service with API Key."""
    return build('calendar', 'v3', developerKey=API_KEY)

# Function to initialize the Google Calendar API service for OAuth
def get_calendar_service_with_oauth():
    """Initialize and return Google Calendar API service with OAuth credentials."""
    creds = authenticate()
    return build('calendar', 'v3', credentials=creds)

# Function to fetch events
def fetch_events_with_apikey(service, time_min=None, max_results=10):
    """Fetch upcoming calendar events using API Key."""
    time_min = time_min or datetime.utcnow().isoformat() + 'Z'  # Default to now
    events_result = service.events().list(
    calendarId='bbc6a4a2565b11d6c4482008eb950da49f93269e7c5a5e46618e0927488e8a3b@group.calendar.google.com',
    timeMin=time_min,
    maxResults=max_results,
    singleEvents=True,
    orderBy='startTime'
    ).execute()

    print("Raw API Response:", events_result)
    events = events_result.get('items', [])
    print("Extracted Events:", events)
    event_list = []
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        event_list.append({
            "start": start,
            "summary": event['summary'],
            "description": event.get('description', 'No description available')
        })

    return event_list

# Flask Blueprint for the event fetching endpoint
get_eventList = Blueprint('get_eventList', __name__)

@get_eventList.route('/api/get_eventList', methods=['GET'])
def get_eventList_route():
    try:
        # Initialize Google Calendar API service with API Key
        service = get_calendar_service_with_apikey()
        events = fetch_events_with_apikey(service)  # Fetch raw events
        print(events,"---------------------------------------")

        # Format events properly
        formatted_events = []
        for event in events:
            formatted_event = {
                "summary": event.get("summary", "No Title"),
                "start": {
                    "dateTime": event.get("start", event.get("start", "No Date"))
                },
                "description": event.get("description", "No Description")
            }
            formatted_events.append(formatted_event)

        return jsonify({'message': 'Event List Fetched', "data": formatted_events}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Flask Blueprint for the event creation endpoint
create_event = Blueprint('create_event', __name__)

@create_event.route("/api/create_event", methods=['POST'])
def create_event_route():
    """Create a new event in Google Calendar using OAuth."""
    try:
        service = get_calendar_service_with_oauth()
        data = request.json
        summary = data.get('summary')
        description = data.get('description')
        start = data.get('start')  # Expecting 'YYYY-MM-DD hh:mm AM/PM'
        end = data.get('end')

        # Validate inputs
        if not summary or not description or not start or not end:
            return jsonify({'error': 'Summary, description, start, and end are required fields'}), 400

        # Convert start and end times
        start_time = convert_to_datetime(start)
        end_time = convert_to_datetime(end)

        if not start_time or not end_time:
            return jsonify({'error': 'Invalid time format. Use "yyyy-mm-dd hh:mm AM/PM".'}), 400

        # Create event payload
        event = {
            'summary': summary,
            'description': description,
            'start': {'dateTime': start_time, 'timeZone': 'America/New_York'},
            'end': {'dateTime': end_time, 'timeZone': 'America/New_York'},
        }

        # Insert event
        event_result = service.events().insert(calendarId='primary', body=event).execute()
        return jsonify({'message': 'Event Created', 'data': event_result}), 201

    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to create event: {str(e)}'}), 500
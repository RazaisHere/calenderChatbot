import os
import re
import logging
import csv
import datetime

import base64
from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
import openai
import requests
import base64
from flask_cors import CORS, cross_origin
'''
Auth: Musawir
'''
from config.database import DB_Config
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect
from flask_bcrypt import Bcrypt
from flask_cors import CORS 
import jwt
import datetime

from Helpers.ChatHistory.ChatHistoryChain import ChatHistoryChain
from config.ExternalConfiguration import ExternalConfiguration

from Helpers.OpenAIDocSearch.Approaches.ChatReadRetrieveReadApproach import (
    ChatReadRetrieveReadApproach,
)
# Importing the external configuration
config = ExternalConfiguration()


# Setting the OpenAI API key from the configuration
os.environ["AZURE_OPENAI_API_INSTANCE_NAME"] = config.CHATGPT_DEPLOYMENT
os.environ["AZURE_OPENAI_API_DEPLOYMENT_NAME"] = config.CHATGPT_DEPLOYMENT
os.environ["AZURE_OPENAI_API_VERSION"] = config.OPENAI_VERSION

KB_FIELDS_CONTENT = os.environ.get("KB_FIELDS_CONTENT") or "content"
KB_FIELDS_SOURCEPAGE = os.environ.get("KB_FIELDS_SOURCEPAGE") or "sourcepage"

# Creating a Flask application instance
app = Flask(__name__)
bcrypt = Bcrypt(app) # Auth: Musawir
cors = CORS(app)

# Auth: Musawir
app.config.from_object(DB_Config)  # Load DB configuration
db = SQLAlchemy(app)
# Initialize SQLAlchemy with the app
#db.init_app(app)

app.secret_key = os.urandom(24)  # Secret key for signing session data

bcrypt.init_app(app)  # Initialize Bcrypt for password hashing

app.config['CORS_HEADERS'] = 'Content-Type'
 
chat_approach = ChatReadRetrieveReadApproach(
        config.CHATGPT_DEPLOYMENT,
        config.CHATGPT_DEPLOYMENT,
        KB_FIELDS_CONTENT,
    )

# Function to remove HTML tags from a string using regex
def remove_html_tags(text):
    clean = re.compile("<.*?>")
    return re.sub(clean, "", text)

# Function to remove all HTML tags from a string using BeautifulSoup
def remove_html_all_tags(text):
    return BeautifulSoup(text, "html.parser").get_text()

CHAT_HISTORY_COLLECTION = ChatHistoryChain()

def validate_logs_existence(path_to_file: str) -> bool:
    if os.path.isfile(os.path.abspath(path_to_file)) is True:
        return True
    else:
        return False

# WE ARE IDENTIFYING USERS UNIQUELY BY THEIR COOKIE ID
def maintain_user_chat_logs(cookie_id: str, date_time: datetime, message_from: str, message: str):
    try:
        path_to_file = str(os.path.abspath("user_chat_logs/user-chat-logs-" + date_time.strftime('%Y-%m-%d') + ".csv"))
        formatted_time = date_time.strftime("%Y-%m-%d %H:%M:%S %p")
        if validate_logs_existence(path_to_file) is True:
            with open(path_to_file, 'a', encoding='UTF-8', newline='') as csv_file:
                csv_writer = csv.writer(csv_file)
                csv_writer.writerow([formatted_time, cookie_id, message_from, message])
        else:
            with open(path_to_file, 'w+', encoding='UTF-8', newline='') as csv_file:
                csv_writer = csv.writer(csv_file)
                csv_writer.writerow(["Date Time", "User Id", "User/AI", "Message"])
                csv_writer.writerow([formatted_time, cookie_id, message_from, message])
    except Exception as e:
        print(str(e))

#SECRET_KEY = os.environ.get('SECRET_KEY', 'your_secret_key')
SECRET_KEY = 'test_key'

def generate_token(user):
    payload = {
        'user_id': user.id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1),  # Expiration time (1 hour)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def verify_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload  # Token is valid, return the payload (user data)
    except jwt.ExpiredSignatureError:
        return None  # Token has expired
    except jwt.InvalidTokenError:
        return None  # Invalid token

# Log the request information before each request
@app.before_request
def log_request_info():
    app.logger.info("Received request: %s %s", request.method, request.path)

# Import routes after initializing the app and db
from routes.user import add_user, get_users, login
from routes.bot import docs_logs, docs_chat
from routes.CalenderIntegration import get_eventList,create_event
app.register_blueprint(add_user)
app.register_blueprint(get_users)
app.register_blueprint(login)
app.register_blueprint(docs_logs)
app.register_blueprint(docs_chat)
app.register_blueprint(get_eventList)
app.register_blueprint(create_event)


@app.route('/',methods=["GET"])
def home():
    return "Hello, World!"


@app.route('/test', methods=["GET"])
def test():
    return "API is Working"

with app.app_context():
    #inspector = inspect(db.engine)
    #print("Tables before create:", inspector.get_table_names())  # Updated to use 'inspect'
    from Models.UserModel import User
    db.create_all()
    
    # Check again after creating the tables
    #print("Tables after create:", inspector.get_table_names())

# Run the Flask application
if __name__ == '__main__':
    app.run(debug=True)
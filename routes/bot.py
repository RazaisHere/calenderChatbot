from flask import Blueprint, request, jsonify, send_file
import logging
from io import BytesIO
import os
from Helpers.ServiceApp import maintain_user_chat_logs, CHAT_HISTORY_COLLECTION, datetime
from Helpers.OpenAIDocSearch.Approaches.ChatReadRetrieveReadApproach import ChatReadRetrieveReadApproach
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()

# --- Blueprint for fetching logs ---
docs_logs = Blueprint('docs_logs', __name__)

@docs_logs.route("/api/docs/logs", methods=['GET'])
def get_chat_logs_path():
    """
    Endpoint to fetch user chat logs as a downloadable CSV file.
    """
    input_date = request.json["for_date"]
    lookup_path = str(os.path.abspath("user_chat_logs/user-chat-logs-" + input_date + ".csv"))
    if os.path.isfile(os.path.abspath(lookup_path)):
        with open(lookup_path, 'rb') as logs_file_bytes:
            return send_file(BytesIO(logs_file_bytes.read()), 
                             download_name="user-chat-logs-" + input_date + ".csv", 
                             as_attachment=True)
    else:
        return jsonify({"message": "No logs exist for the given date."}), 404

# --- Blueprint for chatbot interaction ---
docs_chat = Blueprint('docs_chat', __name__)

# Instantiate the AppointmentBookingChatApproach class
chat_approach = ChatReadRetrieveReadApproach(
    chatgpt_deployment="gpt-4o-mini",  # Replace with your actual deployment name
    gpt_deployment="gpt-4o-mini",
    content_field="content"
)

@docs_chat.route("/api/docs/chat", methods=["POST"])
def chat():
    """
    Endpoint for user to interact with the AI chatbot.
    """
    try:
        # --- Retrieve request data ---
        request_user_id = str(request.json["CookiesId"])
        user_question = str(request.json['question'])

        # --- Append user question to chat history ---
        if CHAT_HISTORY_COLLECTION.exists(request_user_id):
            CHAT_HISTORY_COLLECTION.append_history_record(user_id=request_user_id, user_message=user_question)
        else:
            CHAT_HISTORY_COLLECTION.add_new_user_history(user_id=request_user_id, user_message=user_question)

        maintain_user_chat_logs(request_user_id, datetime.datetime.now(), "User", user_question)

        # --- Run AppointmentBookingChatApproach logic ---
        response_data = chat_approach.run(
            CHAT_HISTORY_COLLECTION.retrieve(request_user_id).user_chat_collection,
            request.json.get("overrides") or {}
        )

        # --- Append AI response to chat history and logs ---
        CHAT_HISTORY_COLLECTION.append_prompt_response(user_id=request_user_id, 
                                                       user_message=user_question, 
                                                       response=str(response_data.get('answer')))
        maintain_user_chat_logs(request_user_id, datetime.datetime.now(), "AI", str(response_data.get('answer')))

        # --- Debugging (print logs to console) ---
        print("Question:")
        print(user_question)
        print("Answer:")
        print(response_data["answer"])

        return jsonify(response_data)

    except Exception as e:
        logging.exception("Exception in /chat")
        return jsonify({"error": str(e)}), 500

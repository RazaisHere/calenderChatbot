import os
from Helpers.ChatHistory.ChatRecordCollection import (
    ChatRecordCollection, ChatRecord
)


class ChatHistoryChain:
    def __init__(self):
        self.chat_history = {}

    def exists(self, user_id: str):
        return user_id in self.chat_history

    def add_new_user_history(self, user_id: str, user_message: str):
        self.chat_history[user_id] = ChatRecordCollection(
            user_id=user_id
        )
        self.append_history_record(user_id=user_id, user_message=user_message)

    def append_history_record(self, user_id: str, user_message: str):
        if(len(self.chat_history[user_id].user_chat_collection)>=5):
            self.chat_history[user_id].user_chat_collection.pop(0)
        self.chat_history[user_id].add(
            user_chat=ChatRecord(user_id=user_id, user_message=user_message)
        )

    def append_prompt_response(self, user_id: str, user_message: str, response: str):
        self.chat_history[user_id].add(
            user_chat=ChatRecord(
                user_id=user_id, user_message=user_message, bot_message=response
            )
        )

    def retrieve(self, user_id: str):
        if user_id in self.chat_history:
            return self.chat_history[user_id]
        else:
            raise KeyError("No history exists for given user: " + user_id)

    def get_prompt(self, user_id: str):
        if self.exists(user_id=user_id):
            history_text = ""
            for item in self.chat_history[user_id].user_chat_collection[-3:]:
                history_text = history_text + "\n" + item.message + ":" + item.role
            return history_text
        else:
            raise KeyError("No history exists for given user: " + user_id)

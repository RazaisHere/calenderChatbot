import os
from Helpers.ChatHistory.ChatRecord import ChatRecord

class ChatRecordCollection():
    def __init__(self, user_id):
        self.user_id = user_id,
        self.user_chat_collection = []

    def add(self, user_chat: ChatRecord):
        if len(self.user_chat_collection) == 0:
            self.user_chat_collection.append(user_chat)
        elif self.get_last_chat_record().bot_message is None:
            self.get_last_chat_record().bot_message = str(user_chat.bot_message)
        else:
            self.user_chat_collection.append(user_chat)

    def get_last_chat_record(self):
        return self.user_chat_collection[-1]

import os

class ChatRecord():

    def __init__(self, user_id: str, user_message: str, bot_message = None):
        self.user_id = user_id
        self.user_message = user_message
        self.bot_message = bot_message

    def get_user_id(self):
        return str(self.user_id)
    
    def append_bot_message(self, bot_message: str):
        self.bot_message = bot_message

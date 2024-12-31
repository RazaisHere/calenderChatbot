from config.ExternalConfiguration import ExternalConfiguration


class PromptHelper:
    def __init__(self):
        self.config = ExternalConfiguration()

    def NoNewLines(self, s: str) -> str:
        return s.replace("\n", " ").replace("\r", " ")

from decouple import Config, RepositoryEnv


# The ExternalConfiguration class is used to manage the external configuration of the application.
class ExternalConfiguration:
    # The constructor for the ExternalConfiguration class.
    # It initializes the configuration from an environment file.
    def __init__(self):
        # Load the configuration from the environment file.
        config = Config(RepositoryEnv("config/settings.env"))

        # # The Configuration for the OPENAI Doc Search
        # Load the Azure Cognitive Search configuration

        # Load the Azure OpenAI Configurations
        self.CHATGPT_DEPLOYMENT = config(
            "OPENAI_CHATGPT_DEPLOYMENT"
        )
        self.OPENAI_EMBEDDINGS_DEPLOYMENT = config("OPENAI_EMBEDDINGS_DEPLOYMENT")
        self.OPENAI_APIKEY = config("OPENAI_APIKEY")
        self.OPENAI_VERSION = config("OPENAI_VERSION")
        self.OPENAI_ENDPOINT = config("OPENAI_ENDPOINT")

        
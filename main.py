from decouple import Config, RepositoryEnv
from config.ExternalConfiguration import ExternalConfiguration

#config = Config(RepositoryEnv("/Source/Repos/EmpowerID/LLMFramework/config/settings.env"))

# Importing the external configuration
config = ExternalConfiguration()

# Setting the OpenAI API key from the configuration
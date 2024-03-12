import os
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("BOT_TOKEN")
admins = [1352923550]
openaiToken = os.getenv("OPENAI_TOKEN")

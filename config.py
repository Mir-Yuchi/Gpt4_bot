import os
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("BOT_TOKEN")
admins = [5594051596]
openaiToken = os.getenv("OPENAI_TOKEN")

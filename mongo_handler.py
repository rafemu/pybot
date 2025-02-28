from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import os

class MongoDBHandler:
    def __init__(self):
        self.client = None
        self.db = None
        self.connect()

    def connect(self):
        try:
            # החלף את הקונפיגורציה לפי ההגדרות שלך
            self.client = MongoClient(
                host=os.getenv("MONGO_URI", "mongodb://localhost:27017/"),
                serverSelectionTimeoutMS=5000
            )
            self.db = self.client['mexc_bot']
            self.client.admin.command('ping')
            print("Connected to MongoDB successfully!")
        except ConnectionFailure as e:
            print(f"MongoDB connection error: {str(e)}")
            raise

    def get_collection(self, name):
        return self.db[name]

# יצירת מופע גלובלי
mongo_handler = MongoDBHandler()
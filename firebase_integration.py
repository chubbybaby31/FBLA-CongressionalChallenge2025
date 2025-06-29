import firebase_admin
from firebase_admin import db
import json

cred_obj = firebase_admin.credentials.Certificate('cosmic-kiln-261701-firebase-adminsdk-96jan-d60de82afd.json')
default_app = firebase_admin.initialize_app(cred_obj, {'databaseURL': "https://cosmic-kiln-261701-default-rtdb.firebaseio.com/"})

class FBAgent:
    def __init__(self, email, new_user=False, name="", password=""):
        self.ref = db.reference("/")
        self.email = email
        if new_user: self.setUpNewUser(name, password)
        self.contents = self.ref.get().items()
        self.id = self.getID()
        if self.id != 0:
            self.contents = dict(self.contents)[self.id]
            self.balance = self.contents["balance"]
            self.name = self.contents["name"]
            self.transactions = self.contents["transactions"]
            if self.transactions == -1: self.transactions = []


    def getID(self):
        for key, value in self.contents:
            if value['email'] == self.email:
                return str(key)
        return 0
    
    def setUpNewUser(self, name, password):
        info = {
            "balance": 1871.20,
            "email": self.email,
            "name": name,
            "password": password,
            "transactions": [
                {"date": "2025-06-03", "description": "Starbucks", "id": 1, "type": "expense", "value": 11.99},
                {"date": "2025-06-03", "description": "Walking Dogs", "id": 2, "type": "income", "value": 50},
                {"date": "2025-06-04", "description": "Work", "id": 3, "type": "income", "value": 500},
                {"date": "2025-06-05", "description": "McDonalds", "id": 4, "type": "expense", "value": 8.78},
                {"date": "2025-06-05", "description": "Work", "id": 5, "type": "income", "value": 500},
                {"date": "2025-06-06", "description": "Spotify Subscription", "id": 6, "type": "expense", "value": 9.99},
                {"date": "2025-06-06", "description": "Freelance Project", "id": 7, "type": "income", "value": 320},
                {"date": "2025-06-07", "description": "Groceries", "id": 8, "type": "expense", "value": 76.25},
                {"date": "2025-06-07", "description": "Gift from Aunt", "id": 9, "type": "income", "value": 100},
                {"date": "2025-06-08", "description": "Electric Bill", "id": 10, "type": "expense", "value": 45.00},
                {"date": "2025-06-08", "description": "Internet Reimbursement", "id": 11, "type": "income", "value": 60},
                {"date": "2025-06-09", "description": "Movie Night", "id": 12, "type": "expense", "value": 17.50},
                {"date": "2025-06-09", "description": "Selling Old Textbooks", "id": 13, "type": "income", "value": 40},
                {"date": "2025-06-10", "description": "Lunch - Chipotle", "id": 14, "type": "expense", "value": 12.60},
                {"date": "2025-06-10", "description": "Pet Sitting", "id": 15, "type": "income", "value": 75},
                {"date": "2025-06-11", "description": "Uber Ride", "id": 16, "type": "expense", "value": 22.40},
                {"date": "2025-06-11", "description": "Cashback Bonus", "id": 17, "type": "income", "value": 15},
                {"date": "2025-06-12", "description": "Amazon Purchase", "id": 18, "type": "expense", "value": 58.99},
                {"date": "2025-06-12", "description": "Work", "id": 19, "type": "income", "value": 500},
                {"date": "2025-06-13", "description": "Dinner - Thai Place", "id": 20, "type": "expense", "value": 25.30}
            ]
        }
        self.ref.push().set(info)
        print("pushed info")
        print(info)
    
    def updateBalance(self):
        self.ref.child(self.id).update({"balance": self.balance})

    def addTransaction(self, transaction_type, date, description, value):
        item = {
            "date": date,
            "description": description,
            "type": transaction_type,
            "value": float(value),
            "id": len(self.transactions) + 1
        }
        self.transactions.append(item)
        self.ref.child(self.id).update({"transactions": self.transactions})

        if transaction_type == "income": self.balance += value
        else: self.balance -= value
        self.updateBalance()
    
    def editTransaction(self, id, transaction_type, date, description, value):
        if self.transactions[id-1]["type"] == "income": self.balance -= float(self.transactions[id-1]["value"])
        else: self.balance += float(self.transactions[id-1]["value"])
        self.transactions[id-1] = {
            "date": date,
            "description": description,
            "type": transaction_type,
            "value": float(value),
            "id": id
        }
        if self.transactions[id-1]["type"] == "income": self.balance += float(self.transactions[id-1]["value"])
        else: self.balance -= float(self.transactions[id-1]["value"])

        self.ref.child(self.id).update({"transactions": self.transactions})
        self.updateBalance()
    
    def deleteTransaction(self, id):
        if self.transactions[id-1]["type"] == "income": self.balance -= float(self.transactions[id-1]["value"])
        else: self.balance += float(self.transactions[id-1]["value"])
        del self.transactions[id-1]
        temp_id = 1
        for t in self.transactions:
            t["id"] = str(temp_id)
            temp_id += 1
        self.ref.child(self.id).update({"transactions": self.transactions})
        self.updateBalance()
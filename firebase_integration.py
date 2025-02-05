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
            "balance": 1029.23,
            "email": self.email,
            "name": name,
            "password": password,
            "transactions": [
                {
                    "date": "2025-02-03",
                    "description": "Starbucks",
                    "id": 1,
                    "type": "expense",
                    "value": 11.99
                },
                {
                    "date": "2025-02-03",
                    "description": "Walking Dogs",
                    "id": 2,
                    "type": "income",
                    "value": 50
                },
                {
                    "date": "2025-02-04",
                    "description": "Work",
                    "id": 3,
                    "type": "income",
                    "value": 500
                },
                {
                    "date": "2025-02-05",
                    "description": "McDonalds",
                    "id": 4,
                    "type": "expense",
                    "value": 8.78
                },
                {
                    "date": "2025-02-05",
                    "description": "Work",
                    "id": 5,
                    "type": "income",
                    "value": 500
                }
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
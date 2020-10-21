import sqlite3
from datetime import datetime
class Database:
    def __init__(self, name="./db/wolt-checker.db"):
        
        self.conn = None
        self.cursor = None

        if name:
            self.open(name)
    
    def __enter__(self):
        return self
        
    def __exit__(self,exc_type,exc_value,traceback):
        
        self.close()
    
    def open(self,name):
    
        try:
            self.conn = sqlite3.connect(name);
            self.cursor = self.conn.cursor()

        except sqlite3.Error as e:
            print("Error connecting to database!")
    
    def close(self):
        
        if self.conn:
            self.conn.commit()
            self.cursor.close()
            self.conn.close()



    def write(self,table,columns,data):
        
        query = "INSERT INTO {0} ({1}) VALUES ({2});".format(table,columns,data)

        self.cursor.execute(query)
    
    def query(self,sql):
        self.cursor.execute(sql)

    def addNewNotification(self, userId, slug):
        existing = self.getUserActiveNotifications(userId=userId)
        existingSlugs = list(map(lambda x: x["slug"], existing))

        if slug not in existingSlugs:
            while True:
                try:
                    nowstr = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    query = f"INSERT INTO Notifications ('userId', 'slug', 'registered') VALUES ({userId}, '{slug}', '{nowstr}');"
                    self.cursor.execute(query)
                    break
                except:
                    pass

    def removeNotification(self, userId, slug, reason):
        while True:
            try:
                nowstr = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                query = f"UPDATE Notifications SET removed = '{nowstr}', removedReason = '{reason}', active = '0' WHERE userId={userId} AND slug='{slug}' AND active='1';"
                self.cursor.execute(query)
                break
            except:
                pass

    def getAllActiveNotifications(self):
        query = f"SELECT userId,slug FROM Notifications WHERE active='1';"

        self.query(query)
        notifications = []
        for row in self.cursor.fetchall():
            notifications.append({"userId": row[0], "slug": row[1]})
        
        return notifications

    def getUserActiveNotifications(self, userId):
        query = f"SELECT slug FROM Notifications WHERE userId='{userId}' AND active='1';"

        self.query(query)
        notifications = []
        for row in self.cursor.fetchall():
            notifications.append(row[0])
        
        return notifications
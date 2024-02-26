from peewee import *
from playhouse.sqliteq import SqliteQueueDatabase

db = SqliteQueueDatabase("database.db")


class Users(Model):
    user_id = BigIntegerField(default=0)
    username = TextField(default="")
    referal = BigIntegerField(default=0)
    qLeft = IntegerField(default=10)
    qReferal = IntegerField(default=0)
    blocked = BooleanField(default=False)


    class Meta:
        database = db
        db_table = "Users"


class Chats(Model):
    chat_id = BigIntegerField(default=0)

    class Meta:
        database = db
        db_table = "Chats"


class Conversations(Model):
    owner_id = ForeignKeyField(Users, to_field="user_id")
    model = TextField(default="gpt")
    status = BooleanField(default=True)

    class Meta:
        database = db
        db_table = "Conversations"


class Messages(Model):
    conversation = ForeignKeyField(Conversations, to_field="id")
    text = TextField(default="")
    role = TextField(default="user")

    class Meta:
        database = db
        db_table = "Messages"


def connect():
    db.connect()
    Users.create_table()
    Conversations.create_table()
    Messages.create_table()
    Chats.create_table()

from peewee import *

db = SqliteDatabase('orm.db')


class BaseModel(Model):
    class Meta:
        database = db


class Test(BaseModel):
    name = TextField()


class Question(BaseModel):
    number = IntegerField()
    content = TextField()
    correct_answer = IntegerField()
    test = ForeignKeyField(Test, backref="questions")


class Answer(BaseModel):
    number = IntegerField()
    content = TextField()
    question = ForeignKeyField(Question, backref="answers")


class User(BaseModel):
    username = TextField()
    username.unique = True
    name = TextField()
    grade = TextField()
    password = TextField()


class Record(BaseModel):
    name = TextField()
    score = IntegerField()
    test = ForeignKeyField(Test, backref="done")
    user = ForeignKeyField(User, backref="records")


if __name__ == '__main__':
    db.create_tables([Test, Question, Answer, Record, User])

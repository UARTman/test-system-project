from peewee import *

db = SqliteDatabase('orm.db')


class BaseModel(Model):
    class Meta:
        database = db


class Test(BaseModel):
    name = TextField()
    type = IntegerField()


class TextQuestion(BaseModel):
    number = IntegerField()
    content = TextField()
    correct_answer = IntegerField()
    test = ForeignKeyField(Test, backref="questions")


class TextAnswer(BaseModel):
    number = IntegerField()
    content = TextField()
    question = ForeignKeyField(TextQuestion, backref="answers")


class Record(BaseModel):
    name = TextField()
    score = IntegerField()
    test = ForeignKeyField(Test, backref="done")


if __name__ == '__main__':
    db.create_tables([Test, TextQuestion, TextAnswer, Record])

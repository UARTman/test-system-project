import os
from hashlib import md5

import peewee
from flask import Flask, url_for, request, redirect, session
from flask import render_template

from orm import *

import re

app = Flask(__name__,
            static_folder="static")
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY') or \
                           'e5ac358c-f0bf-11e5-9e39-d3b532c10a28'


@app.before_request
def before_request():
    db.connect()


@app.after_request
def after_request(response):
    db.close()
    return response


def is_restricted(func, users=None):
    if users is None:
        users = ['admin']

    def wrapper(*args, **kwargs):
        if 'user' in session:
            if session['user'] in users:
                return func(*args, **kwargs)
        return redirect(url_for("page_access_denied"))

    wrapper.__name__ = func.__name__
    return wrapper


@app.route('/access_denied')
def page_access_denied():
    return "<h1>Access Denied!</h1> <a href='{0}'> Home </a> ".format(url_for("page_home"))


@app.route('/login', methods=["POST"])
def action_login():
    print(request.method)
    usr = request.form['user']
    pwd = md5(bytearray(request.form['password'], encoding='utf-8')).hexdigest()
    a = User.select().where(User.username == usr).where(User.password == pwd)
    if len(a):
        session['user'] = usr
    return redirect(url_for("page_home"))


@app.route('/register', methods=["POST", "GET"])
def page_register():
    if request.method == 'POST':
        usr = request.form['user']
        name = request.form['name']
        pwd = md5(bytearray(request.form['password'], encoding='utf-8')).hexdigest()
        grade = request.form['grade']

        def correct_grade(g):
            if re.search(r"Teacher|1?[0-9][a-z]|[A-Z]|[а-я]|[А-Я]", g):
                try:
                    a = int(g[:-1])
                    if a in range(6, 12):
                        return True
                    return False
                except ValueError:
                    return False
            return False

        if not correct_grade(grade):
            return render_template("p_register.html", msg="Incorrect grade!")
        print(usr, name, pwd, grade)
        try:
            User.create(username=usr, name=name, password=pwd, grade=grade)
            return render_template("p_register.html", msg="Registration successful")
        except peewee.IntegrityError:
            return render_template("p_register.html", msg="Username already taken")
    return render_template("p_register.html", msg=None)


@app.route("/logout")
def action_logout():
    session.pop('user', None)
    return redirect(url_for("page_home"))


@app.route('/')
def page_home():
    return render_template('p_homepage.html', name="Anton")


@app.route('/add_test', methods=["POST"])
@is_restricted
def action_admin_add_test():
    if request.method == 'POST':
        Test.create(name=request.form['test_name'])
    return redirect("/admin")


@app.route('/remove_test', methods=["POST"])
@is_restricted
def action_admin_rm_test():
    Test.get_by_id(int(request.form['test_id'])).delete_instance(recursive=True)
    return redirect("/admin")


@app.route('/admin')
@is_restricted
def page_admin_tests():
    results = Test.select()
    return render_template('p_admin_test_list.html', results=results)


@app.route('/admin/test/<int:ident>')
@is_restricted
def page_admin_edit_test(ident):
    questions = Test.get_by_id(ident).questions
    return render_template("p_admin_test_edit.html", model=questions, id=ident)


@app.route('/play')
def page_take_test():
    results = Test.select()
    return render_template('p_user_test_list.html', results=results)


@app.route('/play/<int:ident>')
def page_list_test(ident):
    questions = Test.get_by_id(ident).questions
    return render_template("p_user_test_take.html", model=questions, id=ident)


@app.route('/play/<int:ident>/evaluate', methods=["POST"])
def action_eval_test(ident):
    answers = {}
    for i in request.form:
        if i[0] == 'q':
            answers[int(i[1:])] = int(request.form[i])
    c = 0
    Correct = Answer.alias()
    questions = Test.get_by_id(ident).questions \
        .select(Question, Correct.content) \
        .join(Correct, attr="correct") \
        .where(Correct.number == Question.correct_answer)
    for i in questions:
        if i.correct_answer == answers[i.number]:
            c += 1
    for i in answers:
        answers[i] = questions.where(Question.number == i)[0].answers \
            .where(Answer.number == answers[i])[0].content
    print(answers)
    if 'user' in session:
        username = session['user']
    else:
        username = 'Anonymous'
    Record.create(user=User.get(username=username), score=c, test=Test.get_by_id(ident))
    return render_template("a_test_evaluate.html", model=questions, answers=answers, correct=c,
                           length=len(questions))


@app.route('/admin/test/<int:ident>/add_question', methods=["POST"])
def action_admin_add_question(ident):
    test = Test.get_by_id(ident)
    number = len(test.questions) + 1
    Question.create(number=number, correct_answer=0, content=request.form["question"], test=test)
    return redirect("/admin/test/{}".format(ident))


@app.route('/admin/test/<int:ident>/rm_question', methods=["POST"])
def action_admin_rm_question(ident):
    test = Test.get_by_id(ident)
    for i in test.questions.select().where(Question.number == int(request.form["number"])):
        print(i.number)
        Question.get_by_id(i.id).delete_instance(recursive=True)
    Question.update(number=Question.number - 1) \
        .where(Question.number > request.form["number"]) \
        .where(Question.test == test).execute()
    return redirect("/admin/test/{}".format(ident))


@app.route("/admin/test/<int:ident>/add_answer", methods=["post"])
def action_admin_add_answer(ident):
    question = Test.get_by_id(ident).questions.select().where(Question.number == int(request.form["question"]))[0]
    Answer.create(number=len(question.answers) + 1, content=request.form["content"], question=question)
    return redirect("/admin/test/{}".format(ident))


@app.route("/admin/test/<int:ident>/rm_answer", methods=["post"])
def action_admin_rm_answer(ident):
    question = Test.get_by_id(ident).questions.where(Question.number == request.form["question"])[0]
    answers = question.answers.where(Answer.number == int(request.form["number"]))
    Answer.delete_by_id(answers[0].id)
    for i in answers.where(Answer.number > int(request.form["number"])):
        print(i.number, int(request.form["number"]))
    Answer.update(number=Answer.number - 1) \
        .where(Answer.number > int(request.form["number"])) \
        .where(Answer.question == question).execute()
    if question.correct_answer >= int(request.form["number"]):
        question.update(correct_answer=question.correct_answer - 1)
    return redirect("/admin/test/{}".format(ident))


@app.route("/admin/test/<int:ident>/ch_correct", methods=["post"])
def action_admin_set_correct(ident):
    question = Test.get_by_id(ident).questions.where(Question.number == request.form["question"])[0]
    question.update(correct_answer=request.form["correct"]).where(Question.id == question.id).execute()
    return redirect("/admin/test/{}".format(ident))


@app.route("/leaderboard")
def page_leaderboard():
    model = Record.select()
    return render_template("p_leaderboard.html", model=model, len=len)


def base_placeholder():  # TODO: find a way to add template_base to indexing w/o this clutch.
    return render_template("t_base.html")


if __name__ == '__main__':
    app.run()

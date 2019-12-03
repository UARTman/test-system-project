import os

from flask import Flask, url_for, request, redirect, session
from flask import render_template

from orm import *

TYPES = {0: "Simple test"}
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


def decor_restricted(func, users=None):
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


@app.route('/login')
def action_login():
    session['user'] = 'admin'
    return redirect(url_for("page_admin_tests"))


@app.route('/logout')
def action_logout():
    session.pop('user', None)
    return redirect(url_for("page_home"))


@app.route('/')
def page_home():
    return render_template('homepage.html', name="Anton")


@app.route('/add_test', methods=["POST"])
@decor_restricted
def action_admin_add_test():
    if request.method == 'POST':
        with db.atomic():
            Test.create(name=request.form['test_name'], type=request.form['test_type'])
    return redirect("/admin")


@app.route('/remove_test', methods=["POST"])
@decor_restricted
def action_admin_rm_test():
    with db.atomic():
        Test.get_by_id(int(request.form['test_id'])).delete_instance(recursive=True)
    return redirect("/admin")


@app.route('/admin')
@decor_restricted
def page_admin_tests():
    with db.atomic():
        results = Test.select()
    return render_template('adminpanel.html', results=results, types=TYPES)


@app.route('/admin/test/<int:ident>')
@decor_restricted
def page_admin_edit_test(ident):
    with db.atomic():
        questions = Test.get_by_id(ident).questions
    return render_template("admin_text_test.html", model=questions, id=ident)


@app.route('/play')
def page_take_test():
    with db.atomic():
        results = Test.select()
    return render_template('t_list_tests.html', results=results, types=TYPES)


@app.route('/play/<int:ident>')
def page_list_test(ident):
    with db.atomic():
        questions = Test.get_by_id(ident).questions
    return render_template("test_participate_text.html", model=questions, id=ident)


@app.route('/play/<int:ident>/evaluate', methods=["POST"])
def action_eval_test(ident):
    answers = {}
    for i in request.form:
        if i[0] == 'q':
            answers[int(i[1:])] = int(request.form[i])
    c = 0
    print(answers)

    with db.atomic():
        Correct = Answer.alias()
        questions = Test.get_by_id(ident).questions \
            .select(Question, Correct.content) \
            .join(Correct, attr="correct") \
            .where(Correct.number == Question.correct_answer)
    print("1")

    for i in questions:
        if i.correct_answer == answers[i.number]:
            c += 1
    print("1")
    for i in answers:
        answers[i] = questions.where(Question.number == i)[0].answers \
            .where(Answer.number == answers[i])[0].content
    print(answers)
    with db.atomic():
        Record.create(name=request.form["name"], score=c, test=Test.get_by_id(ident))
    return render_template("test_evaluate_text.html", model=questions, answers=answers, correct=c,
                           length=len(questions))


@app.route('/admin/test/<int:ident>/add_question', methods=["POST"])
def action_admin_add_question(ident):
    test = Test.get_by_id(ident)
    number = len(test.questions) + 1
    with db.atomic():
        Question.create(number=number, correct_answer=0, content=request.form["question"], test=test)
    return redirect("/admin/test/{}".format(ident))


@app.route('/admin/test/<int:ident>/rm_question', methods=["POST"])
def action_admin_rm_question(ident):
    with db.atomic():
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
    with db.atomic():
        question = Test.get_by_id(ident).questions.select().where(Question.number == int(request.form["question"]))[
            0]
        Answer.create(number=len(question.answers) + 1, content=request.form["content"], question=question)
    return redirect("/admin/test/{}".format(ident))


@app.route("/admin/test/<int:ident>/rm_answer", methods=["post"])
def action_admin_rm_answer(ident):
    with db.atomic():
        question = Test.get_by_id(ident).questions.where(Question.number == request.form["question"])[0]
        answers = question.answers.where(Answer.number == int(request.form["number"]))
        Answer.delete_by_id(answers[0].id)
        for i in answers.where(Answer.number > int(request.form["number"])):
            print(i.number, int(request.form["number"]))
        Answer.update(number=Answer.number - 1) \
            .where(Answer.number > int(request.form["number"])) \
            .where(Answer.question == question).execute()
    return redirect("/admin/test/{}".format(ident))


@app.route("/admin/test/<int:ident>/ch_correct", methods=["post"])
def action_admin_set_correct(ident):
    with db.atomic():
        question = Test.get_by_id(ident).questions.where(Question.number == request.form["question"])[0]
        question.update(correct_answer=request.form["correct"]).where(Question.id == question.id).execute()
    return redirect("/admin/test/{}".format(ident))


@app.route("/leaderboard")
def page_leaderboard():
    with db.atomic():
        model = Record.select()
    return render_template("leaderboard.html", model=model, len=len)


def base_placeholder():  # TODO: find a way to add template_base to indexing w/o this clutch.
    return render_template("template_base.html")


if __name__ == '__main__':
    app.run()

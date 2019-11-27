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


def restricted(func, users=None):
    if users is None:
        users = ['admin']

    def wrapper(*args, **kwargs):
        if 'user' in session:
            if session['user'] in users:
                return func(*args, **kwargs)
        return redirect(url_for("access_denied"))

    wrapper.__name__ = func.__name__
    return wrapper


@app.route('/access_denied')
def access_denied():
    return "<h1>Access Denied!</h1> <a href='{0}'> Home </a> ".format(url_for("home_page"))


@app.route('/login')
def login_placeholder():
    session['user'] = 'admin'
    return redirect(url_for("admin_panel"))


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for("home_page"))


@app.route('/')
def home_page():
    return render_template('homepage.html', name="Anton")


@app.route('/add_test', methods=["POST"])
@restricted
def add_test():
    if request.method == 'POST':
        with db.atomic():
            Test.create(name=request.form['test_name'], type=request.form['test_type'])
    return redirect("/admin")


@app.route('/remove_test', methods=["POST"])
@restricted
def remove_test():
    with db.atomic():
        Test.get_by_id(int(request.form['test_id'])).delete_instance(recursive=True)
    return redirect("/admin")


@app.route('/admin')
@restricted
def admin_panel():
    with db.atomic():
        results = Test.select()
    return render_template('adminpanel.html', results=results, types=TYPES)


@app.route('/admin/test/<int:ident>')
@restricted
def admin_test(ident):
    with db.atomic():
        questions = Test.get_by_id(ident).questions
    return render_template("admin_text_test.html", model=questions, id=ident)


@app.route('/play')
def play_test():
    with db.atomic():
        results = Test.select()
    return render_template('tests_page.html', results=results, types=TYPES)


@app.route('/play/<int:ident>')
def take_test(ident):
    with db.atomic():
        questions = Test.get_by_id(ident).questions
    return render_template("test_participate_text.html", model=questions, id=ident)


@app.route('/play/<int:ident>/evaluate', methods=["POST"])
def eval_test(ident):
    answers = {}
    for i in request.form:
        if i[0] == 'q':
            answers[int(i[1:])] = int(request.form[i])
    c = 0
    print(answers)

    with db.atomic():
        Correct = TextAnswer.alias()
        questions = Test.get_by_id(ident).questions \
            .select(TextQuestion, Correct.content) \
            .join(Correct, attr="correct") \
            .where(Correct.number == TextQuestion.correct_answer)
    print("1")

    for i in questions:
        if i.correct_answer == answers[i.number]:
            c += 1
    print("1")
    for i in answers:
        answers[i] = questions.where(TextQuestion.number == i)[0].answers \
            .where(TextAnswer.number == answers[i])[0].content
    print(answers)
    with db.atomic():
        Record.create(name=request.form["name"], score=c, test=Test.get_by_id(ident))
    return render_template("test_evaluate_text.html", model=questions, answers=answers, correct=c,
                           length=len(questions))


@app.route('/admin/test/<int:ident>/add_question', methods=["POST"])
def add_question(ident):
    test = Test.get_by_id(ident)
    number = len(test.questions) + 1
    with db.atomic():
        TextQuestion.create(number=number, correct_answer=0, content=request.form["question"], test=test)
    return redirect("/admin/test/{}".format(ident))


@app.route('/admin/test/<int:ident>/rm_question', methods=["POST"])
def rm_question(ident):
    with db.atomic():
        test = Test.get_by_id(ident)
        for i in test.questions.select().where(TextQuestion.number == int(request.form["number"])):
            print(i.number)
            TextQuestion.get_by_id(i.id).delete_instance(recursive=True)
        TextQuestion.update(number=TextQuestion.number - 1) \
            .where(TextQuestion.number > request.form["number"]) \
            .where(TextQuestion.test == test).execute()
    return redirect("/admin/test/{}".format(ident))


@app.route("/admin/test/<int:ident>/add_answer", methods=["post"])
def add_answer(ident):
    with db.atomic():
        question = Test.get_by_id(ident).questions.select().where(TextQuestion.number == int(request.form["question"]))[
            0]
        TextAnswer.create(number=len(question.answers) + 1, content=request.form["content"], question=question)
    return redirect("/admin/test/{}".format(ident))


@app.route("/admin/test/<int:ident>/rm_answer", methods=["post"])
def rm_answer(ident):
    with db.atomic():
        question = Test.get_by_id(ident).questions.where(TextQuestion.number == request.form["question"])[0]
        answers = question.answers.where(TextAnswer.number == int(request.form["number"]))
        TextAnswer.delete_by_id(answers[0].id)
        for i in answers.where(TextAnswer.number > int(request.form["number"])):
            print(i.number, int(request.form["number"]))
        TextAnswer.update(number=TextAnswer.number - 1) \
            .where(TextAnswer.number > int(request.form["number"])) \
            .where(TextAnswer.question == question).execute()
    return redirect("/admin/test/{}".format(ident))


@app.route("/admin/test/<int:ident>/ch_correct", methods=["post"])
def ch_correct(ident):
    with db.atomic():
        question = Test.get_by_id(ident).questions.where(TextQuestion.number == request.form["question"])[0]
        question.update(correct_answer=request.form["correct"]).where(TextQuestion.id == question.id).execute()
    return redirect("/admin/test/{}".format(ident))


@app.route("/leaderboard")
def leaderboard():
    with db.atomic():
        model = Record.select()
    return render_template("leaderboard.html", model=model, len=len)


if __name__ == '__main__':
    app.run()

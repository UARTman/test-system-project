import os
from flask import Flask, url_for, request, redirect, session
from flask import render_template
from orm import *

TYPES = ["Simple test"]

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

    with db.atomic():
        Correct = TextAnswer.alias()
        questions = Test.get_by_id(ident).questions\
            .select(TextQuestion, Correct.content)\
            .join(Correct, attr="correct")\
            .where(Correct.number == TextQuestion.correct_answer)

    for i in questions:
        if i.correct_answer == answers[i.number]:
            c += 1
    for i in answers:
        answers[i] = TextQuestion.get_by_id(i).answers\
            .where(TextAnswer.number == answers[i])[0].content
    with db.atomic:
        Record.create(name=request.form["name"], score=c, test=Test.get_by_id(ident))
    return render_template("test_evaluate_text.html", model=questions, answers=answers, correct=c, length=len(questions))


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
            print(i.id)
            TextQuestion.get_by_id(i.id).delete_instance(recursive=True)
    return redirect("/admin/test/{}".format(ident))


if __name__ == '__main__':
    app.run()

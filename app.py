import os
from flask import Flask, url_for, request, redirect, session
from flask import render_template

import sqlite3

DATABASE = "example.db"
TYPES = ["Simple test"]
TEST_MODEL_SQL = '''select text_test_questions.question_number, text_test_answers.answer_number, correct_answer, question, answer
from tests, text_test_answers, text_test_questions
where text_test_questions.test_id = id and text_test_answers.test_id = id and id = {}
and text_test_answers.question_number = text_test_questions.question_number
order by text_test_questions.question_number'''

app = Flask(__name__,
            static_folder="static")
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY') or \
                           'e5ac358c-f0bf-11e5-9e39-d3b532c10a28'


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


def with_sql(func, db="example.db"):
    def wrapper(*args, **kwargs):
        a = sqlite3.connect(db)
        c = a.cursor()
        kwargs['cursor'] = c
        ret = func(*args, **kwargs)
        a.commit()
        a.close()
        return ret
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


@app.route('/add_test', methods=["GET", "POST"])
@restricted
@with_sql
def add_test(cursor=None):
    if request.method == 'POST':
        print('sender')
        print('{} {}'.format(request.form['test_name'], request.form['test_type']))
        cursor.execute('insert into tests  (name, type) values ("{}",{})'
                       .format(request.form['test_name'], request.form['test_type']))
    return redirect("/admin")


@app.route('/remove_test', methods=["GET", "POST"])
@restricted
@with_sql
def remove_test(cursor=None):
    if request.method == 'POST':
        cursor.execute("delete from tests where id={}"
                       .format(request.form['test_id']))
        cursor.execute("delete from text_test_questions where test_id={}"
                       .format(request.form['test_id']))
        cursor.execute("delete from text_test_answers where test_id={}"
                       .format(request.form['test_id']))
        print('confirm')
    return redirect("/admin")


@app.route('/admin')
@restricted
@with_sql
def admin_panel(cursor=None):
    cursor.execute("select * from tests")
    results = cursor.fetchall()
    return render_template('adminpanel.html', results=results, types=TYPES)


@app.route('/admin/test/<ident>')
@restricted
@with_sql
def admin_test(ident, cursor=None):
    cursor.execute(TEST_MODEL_SQL.format(ident))
    results = cursor.fetchall()
    model = []
    last = None
    for i in results:
        if last != i[0]:
            last = i[0]
            model.append([i[0], i[3], [], i[2]])
        model[-1][2].append([i[1], i[4]])
    return render_template("admin_text_test.html", model=model)


@app.route('/play')
@with_sql
def play_test(cursor=None):
    cursor.execute("select * from tests")
    results = cursor.fetchall()
    return render_template('tests_page.html', results=results, types=TYPES)


@app.route('/play/<ident>')
@with_sql
def take_test(ident, cursor=None):
    cursor.execute(TEST_MODEL_SQL.format(ident))
    results = cursor.fetchall()
    model = []
    last = None
    for i in results:
        if last != i[0]:
            last = i[0]
            model.append([i[0], i[3], [], i[2]])
        model[-1][2].append([i[1], i[4]])
    return render_template("test_participate_text.html", model=model, id=ident)


@app.route('/play/<ident>/evaluate', methods=["GET", "POST"])
@with_sql
def eval_test(ident, cursor=None):
    cursor.execute(TEST_MODEL_SQL.format(ident))
    results = cursor.fetchall()
    model = []
    last = None
    for i in results:
        if last != i[0]:
            last = i[0]
            model.append([i[0], i[3], [], i[2]])
        model[-1][2].append([i[1], i[4]])
    l = len(request.form) - 1
    print(request.form)
    print(model)
    print(l)
    model1 = []
    c = 0
    for i in model:
        for j in i[2]:
            if j[0] == i[-1]:
                k = j[1]
            if j[0] == int(request.form["q{}".format(i[0])]):
                ll = j[1]
        if k == ll:
            c += 1
        model1.append([i[0], i[1], ll, k])
    print(model1, c, l)
    return render_template("test_evaluate_text.html", model=model1, correct=c, length=l)


if __name__ == '__main__':
    app.run()

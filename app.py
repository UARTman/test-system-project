from flask import Flask, url_for, request, redirect
from flask import render_template
import sqlite3

DATABASE = "example.db"
TYPES = ["Simple test"]

app = Flask(__name__,
            static_folder="static")


@app.route('/')
def home_page():
    return render_template('homepage.html', name="Anton")


@app.route('/add_test', methods=["GET", "POST"])
def sql_write():
    a = sqlite3.connect("example.db")
    c = a.cursor()
    c.execute("select * from tests")
    if request.method == 'POST':
        print('sender')
        print('{} {}'.format(request.form['test_name'], request.form['test_type']))
        c.execute('insert into tests  (name, type) values ("{}",{})'
                  .format(request.form['test_name'], request.form['test_type']))
    a.commit()
    a.close()
    return redirect("/admin")


@app.route('/admin')
def admin_panel():
    a = sqlite3.connect("example.db")
    c = a.cursor()
    c.execute("select * from tests")
    results = c.fetchall()
    a.close()
    return render_template('adminpanel.html', results=results, types=TYPES)


@app.route('/play')
def play_test():
    return render_template('test.html')


if __name__ == '__main__':
    app.run()
    a.close()

from flask import Flask, render_template, redirect, request, session
import sqlite3
from sqlite3 import Error
from flask_bcrypt import Bcrypt



DATABASE = "smilecafe.db"
app = Flask(__name__)
bcrypt = Bcrypt(app)
app.secret_key = "anything"

def open_database(db_name):
    try:
        connection = sqlite3.connect(db_name)
        return connection
    except Error as e:
        print(e)
        return None

def is_logged_in():
    if session.get("email") is None:
        print("not logged in")
        return False
    else:
        print("logged in")
        return True


@app.route('/')
def render_home():
    return render_template("home.html", logged_in=is_logged_in())


@app.route('/menu/<cat_id>')
def render_menu(cat_id):
    con = open_database(DATABASE)
    query = "SELECT * FROM Category"
    cur = con.cursor()
    cur.execute(query)
    category_list = cur.fetchall()
    print(category_list)
    query = "SELECT * FROM Product WHERE cat_id = ? ORDER BY Product_name "
    cur = con.cursor()
    cur.execute(query, (cat_id, ))
    product_list = cur.fetchall()
    con.close()
    return render_template("menu.html", categories=category_list, products=product_list, logged_in=is_logged_in())


@app.route('/contact')
def render_contact():
    return render_template("contact.html", logged_in=is_logged_in())

@app.route('/logout')
def logout():
    print(list(session.keys()))
    [session.pop(key) for key in list(session.keys())]
    print(list(session.keys()))
    return redirect('/?message=See+you+next+time!')

@app.route('/login', methods=['POST', 'GET'])
def render_login():
    if is_logged_in():
        return redirect('/')
    print("Logging in")
    if request.method == "POST":
        email =request.form['email'].strip().lower()
        password = request.form['password'].strip()
        print(email)
        query = """SELECT id, first_name, password FROM user WHERE email = ?"""
        con = open_database(DATABASE)
        cur = con.cursor()
        cur.execute(query, (email, ))
        user_data = cur.fetchone()
        con.close()
        print(user_data)

        if user_data is None:
            return redirect("/login")

        try:
            user_id = user_data[0]
            first_name = user_data[1]
            db_password = user_data[2]
        except IndexError:
            return redirect("/login?error=Email+invalid+or+password+incorrect")

        if not bcrypt.check_password_hash(db_password, password):
            return redirect(request.referrer + "?error=Email+invalid+or+password+incorrect")

        session['email'] = email
        session['user_id'] = user_id
        session['firstname'] = first_name

        print(session)
        return redirect('/')

    return render_template("login.html", logged_in=is_logged_in())



@app.route('/signup', methods=['POST', 'GET'])
def render_signup():
    if is_logged_in():
        return redirect('/message=Already+logged+in')
    if request.method == 'POST':
        print(request.form)
        first_name = request.form.get('first_name').title().strip()
        last_name = request.form.get('last_name').title().strip()
        email = request.form.get('email').lower().strip()
        password = request.form.get('password')
        password2 = request.form.get('password2')

        if password != password2:
            return redirect("/signup?error=Passwords+do+not+match")

        if len(password) < 8:
            return redirect("/signup?error=Password+must+be+at+least+8+characters")

        hashed_password = bcrypt.generate_password_hash(password)
        con = open_database(DATABASE)
        query = "INSERT INTO user (first_name, last_name, email, password) VALUES (?, ?, ?, ?)"
        cur = con.cursor()

        try:
            cur.execute(query, (first_name, last_name, email, hashed_password))
        except sqlite3.IntegrityError:
            con.close()
            return redirect("/signup?error=Email+is+already+in+use")

        con.commit()
        con.close()

        return redirect("/login")

    return render_template("signup.html", logged_in=is_logged_in())

@app.route('/admin')
def render_admin():
    if not is_logged_in():
        return redirect('/?message=Need+to+be+logged+in')
    con = open_database(DATABASE)
    query = "SELECT * FROM Category"
    cur = con.cursor()
    cur.execute(query)
    category_list = cur.fetchall()
    con.close()
    return render_template("admin.html", logged_in=is_logged_in(), categories=category_list)

@app.route('/add_category', methods=['POST'])
def add_category():
    if not is_logged_in():
        return redirect('/?message=Need+to+be+logged+in')
    if request.method == "POST":
        print(request.form)
        cat_name = request.form.get('name').strip().lower()
        print(cat_name)
        con = open_database(DATABASE)
        query = "INSERT INTO category (Name) VALUES (?)"
        cur = con.cursor()
        cur.execute(query, (Name, ))
        con.commit()
        con.close()
        return redirect('/admin')


@app.route('/delete_category', methods=['POST'])
def render_delete_category():
    if not is_logged_in():
        return redirect('/?message=Need+to+be+logged+in')
    if request.method == "POST":
        Category = request.form.get('cat_id')
        print(Category)
        cat_id = Category[0]
        cat_name = Category[1]
        return render_template("delete_confirm.html", cat_id=cat_id, cat_name=cat_name, type="Category")
    return redirect("/admin")

if __name__ == '__main__':
    app.run()


if __name__ == '__main__':
    app.run()

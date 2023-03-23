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


def is_ordering():
    if session.get('order') is None:
        print("not ordering")
        return False
    else:
        print("ordering")
        return True


def get_list(query, params):
    con = open_database(DATABASE)
    cur = con.cursor()
    if params == "":
        cur.execute(query)
    else:
        cur.execute(query, params)
    query_list = cur.fetchall()
    con.close()
    return query_list


def put_data(query, params):
    con = open_database(DATABASE)
    cur = con.cursor()
    cur.execute(query, params)
    con.commit()
    con.close()


def summarise_orders():
    order = session['order']
    print(order)
    order.sort()
    print(order)
    order_summary = []
    last_order = -1
    for item in order:
        if item != last_order:
            order_summary.append([item, 1])
            last_order = item
        else:
            order_summary[-1][1] += 1
    print(order_summary)
    return order_summary


@app.route('/')
def render_home():
    message = request.args.get('message')
    if message is None:
        message = ""
    return render_template("home.html", logged_in=is_logged_in(), message=message, ordering=is_ordering())


@app.route('/menu/<cat_id>', methods=['POST', 'GET'])
def render_menu(cat_id):
    order_start = request.args.get('order')
    if order_start == 'start' and not is_ordering():
        session['order'] = []

    if request.method == "POST":
        print(request.form)
        order = []

    # Fetch the categories
    category_list = get_list("SELECT * FROM Category", "")

    # Fetch the products
    product_list = get_list("SELECT * FROM Product WHERE cat_id = ? ORDER BY Name", (cat_id, ))

    return render_template("menu.html", categories=category_list, ordering=is_ordering(), products=product_list,
                           logged_in=is_logged_in())


@app.route('/add_to_cart/<product_id>')
def add_to_cart(product_id):
    try:
        product_id = int(product_id)
    except ValueError:
        print("{} is not an integer".format(product_id))
        return redirect("/menu/1?error=Invalid+product+id")
    print("Adding to cart product", product_id)
    order = session['order']
    print("Order before adding", order)
    order.append(product_id)
    print("Order after adding", order)
    session['order'] = order
    return redirect(request.referrer)


@app.route('/cart', methods=['POST', 'GET'])
def render_cart():
    if request.method == "POST":
        name = request.form['name']
        print(name)
        put_data("INSERT INTO orders VALUES (null, ?, TIME('now'), ?)", (name, 1))
        order_number = get_list("SELECT max(id) FROM orders WHERE name = ?", (name, ))
        print(order_number)
        order_number = order_number[0][0]
        orders = summarise_orders()
        for order in orders:
            put_data("INSERT INTO  order_content VALUES (null, ?, ?, ?)", (order_number, order[0], order[1]))
        session.pop('order')
        return redirect('/?message=Order+has+not+been+placed+under+the+name+' + name)
    else:
        orders = summarise_orders()
        total = 0
        for item in orders:
            item_detail = get_list("SELECT Product_name, Product_price FROM Product WHERE id = ?", (item[0], ))
            print(item_detail)
            if item_detail:
                item.append(item_detail[0][0])
                item.append(item_detail[0][1])
                item.append(item_detail[0][1] * item[1])
                total += item_detail[0][1] * item[1]
        print(orders)
        return render_template("cart.html", logged_in=is_logged_in(), ordering=is_ordering(),
                               products=orders, total=total)


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
        email = request.form['email'].strip().lower()
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


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def page_not_found(e):
    return render_template('500.html'), 500


@app.route('/add_category', methods=['POST'])
def add_category():
    if not is_logged_in():
        return redirect('/?message=Need+to+be+logged+in')
    if request.method == "POST":
        print(request.form)
        cat_name = request.form.get('Name').lower().strip()
        print(cat_name)
        con = open_database(DATABASE)
        query = "INSERT INTO Category ('Name') VALUES (?)"
        cur = con.cursor()
        cur.execute(query, (cat_name, ))
        con.commit()
        con.close()
    return redirect('/admin')


@app.route('/add_item', methods=['POST'])
def add_item():
    if not is_logged_in():
        return redirect('/?message=Need+to+be+logged+in')
    if request.method == "POST":
        print(request.form)
        item_name = request.form.get('Product_name').strip()
        item_description = request.form.get('Product_description').strip()
        item_size = request.form.get('Product_size').strip()
        item_image = request.form.get('Product_image').lower().strip()
        item_price = request.form.get('Product_price').strip()
        cat_id = request.form.get('cat_id')
        cat_id = cat_id.split(", ")
        cat_id = cat_id[0]
        con = open_database(DATABASE)
        query = "INSERT INTO Product ('Product_name', 'Product_description', 'Product_size', 'Product_image'," \
                " 'Product_price', 'cat_id') VALUES (?, ?, ?, ?, ?, ?)"
        cur = con.cursor()
        cur.execute(query, (item_name, item_description, item_size, item_image, item_price, cat_id))
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



@app.route('/delete_Category_confirm/<cat_id>')
def delete_category_confirm(cat_id):
    if not is_logged_in():
        return redirect('/?message=Need+to+be+logged+in')
    con = open_database(DATABASE)
    query = "DELETE FROM Category WHERE id = ?"
    cur = con.cursor()
    cur.execute(query, (cat_id, ))
    con.commit()
    con.close()
    return redirect("/admin")


if __name__ == '__main__':
    app.run()

import smtplib
from random import randint
import stripe
from flask import Flask, render_template, request, redirect, url_for, jsonify
import os

from flask_login import LoginManager, UserMixin, login_required, logout_user, login_user, current_user
from sqlalchemy import func, Update, and_
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash

stripe.api_key = os.environ.get("STRIPE_KEY")
YOUR_DOMAIN = os.environ.get("DOMAIN")

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("FLASK_KEY")
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DB_URI", "sqlite:///products.db")

db = SQLAlchemy()
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)

app.app_context().push()


class EcomUsers(UserMixin, db.Model):
    __tablename__ = "e_com_users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))


class Cart(db.Model):
    __tablename__ = "carts"
    id = db.Column(db.Integer, primary_key=True)
    quantity = db.Column(db.String(250), nullable=False)
    product_id = db.Column(db.String(250), nullable=False)
    author_id = db.Column(db.String(250), nullable=False)


#
# class Products(db.Model):
#     __tablename__ = "products"
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(250), unique=True, nullable=False)
#     description = db.Column(db.String(500), nullable=False)
#     total_price = db.Column(db.String(250), nullable=False)
#     discount_price = db.Column(db.String(250), nullable=False)
#     product_url = db.Column(db.String(500), nullable=False)
#
#     cart_id = db.Column(db.Integer, db.ForeignKey("cards.id"))
#     cart_list = relationship("Cart", back_populates="cart_products")
#
#
db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(EcomUsers, user_id)


@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        result = db.session.execute(db.select(EcomUsers).where(EcomUsers.email == email)).scalar()
        if result is None:
            num_list = []
            for i in range(0, 6):
                num = randint(0, 9)
                num_list.append(num)
            str_list = [str(i) for i in num_list]
            rand = ""
            code = rand.join(str_list)
            # print(code)
            send_verification(name, code, email)
            return redirect(url_for("register_verify", name=name, email=email, password=password, code=code))
        else:
            error = "Already registered!! Please login"
            return render_template("register.html", error=error)

    return render_template("register.html")


def send_verification(name, codes, email):
    username = os.environ.get('email')
    passwords = os.environ.get('password')
    email_message = f"Subject:Verify your Email\n\nHi {name},\nPlease enter this code in EJ E-commerce Website \nCode:{codes}"
    # print(email_message)
    with smtplib.SMTP("smtp.gmail.com", port=587) as connection:
        connection.starttls()
        connection.login(user=username, password=passwords)
        connection.sendmail(from_addr=username, to_addrs=email,
                            msg=email_message.encode('utf-8'))
        # print("Mail sent")


@app.route('/register_verify', methods=["GET", "POST"])
def register_verify():
    name = request.args.get("name")
    email = request.args.get("email")
    password = request.args.get("password")
    code = request.args.get("code")

    if request.method == "POST":
        code_returned = request.form["code"]
        # print(code_returned)
        if code_returned == code:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
            user = EcomUsers(name=name, email=email, password=hashed_password)
            db.session.add(user)
            db.session.commit()
            return render_template("login.html", success="Registered Successfully please login!!")
        else:
            error = "Verification code is wrong"
            return render_template("verify.html", error=error, name=name, email=email, password=password, code=code)

    return render_template("verify.html", name=name, email=email, password=password, code=code)


@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        result = db.session.execute(db.select(EcomUsers).where(EcomUsers.email == email)).scalar()
        # print(result)

        if result is None:
            error = "Email id is incorrect or not registered"
            return render_template("login.html", error1=error, email=email, password=password)
        else:
            check_password_is_true = check_password_hash(result.password, password)
            if check_password_is_true is True:
                login_user(result)
                return redirect(url_for('home', user_id=current_user.id))
            else:
                error = "Password is Incorrect"
                return render_template("login.html", error2=error, email=email, password=password)
    return render_template("login.html")


@app.route('/logout')
@login_required
def logout():
    logout_user()
    logouts = "Logout Successful"
    return render_template("index.html", logout=logouts)


@app.route('/forgot_password', methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"]
        # print(email)

        result = db.session.execute(db.select(EcomUsers).where(EcomUsers.email == email)).scalar()
        # print(result)
        if result is None:
            error = "Email is not registered, Please register first!!"
            return render_template("forgot.html", error=error)
        else:
            num_lists = []
            for ii in range(0, 6):
                nums = randint(0, 9)
                num_lists.append(nums)
            str_lists = [str(ii) for ii in num_lists]
            rands = ""
            codess = rands.join(str_lists)
            # print(codess)
            send_verification(name="", email=email, codes=codess)
            return redirect(url_for("verify", email_code=codess, email=email))

    return render_template("forgot.html")


@app.route('/verify', methods=["GET", "POST"])
def verify():
    email_code = request.args.get("email_code")
    # print(email_code)
    email = request.args.get("email")
    # print(email)
    error = ""
    success = ""
    update = False
    if request.method == "POST":
        code_forgot_password = request.form["code"]
        # print(code_forgot_password)
        if code_forgot_password == email_code:
            update = True
            success = "Verification successfully,\n Enter your new password now!!"
            redirect(url_for("verify", success=success, update=update, error="", email=email))
        else:
            error = "Verification code is wrong"
            redirect(url_for("verify", error=error, email_code=email_code, success="", email=email))

    return render_template("update_password.html", error=error, success=success, email_code=email_code, update=update,
                           email=email)


@app.route('/update_passwords', methods=["GET", "POST"])
def update_passwords():
    password = request.form["password"]
    # print(password)
    email = request.args.get("email")
    # print(email)
    hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
    db.session.execute(Update(EcomUsers).where(EcomUsers.email == email).values(password=hashed_password))
    db.session.commit()
    success = "Password changed Successfully"
    return render_template("login.html", success=success)


@app.route('/')
def home():
    logout = "Welcome to 🛍️EJ E-Commerce Website, Please register or login"
    user_result = db.session.execute(db.select(EcomUsers)).scalars()

    if current_user in user_result:

        product_id = []
        names = []
        description = []
        images = []
        data = stripe.Product.list()

        for i in data["data"]:
            product_id.append(i["id"])
            names.append(i["name"])
            description.append(i["description"])
            images.append(i["images"][0])
        price_id = []
        prices = []

        price = stripe.Price.list()
        for i in price["data"]:
            price_id.append(i["id"])
            price_int = i["unit_amount"]
            price_final = str(price_int)[:-2]
            prices.append(price_final)
        length = len(names)
        return render_template("index.html", user_id=current_user.id, user=True, names=names, description=description,
                               images=images, prices=prices, len=length, product_id=product_id,
                               login=db.get_or_404(EcomUsers, current_user.id))
    else:
        return render_template("index.html", user=False, logout=logout)



@app.route("/contact", methods=["GET", "POST"])
@login_required
def contact():
    if request.method == "POST":
        datas = request.form
        send_email(datas["name"], datas["email"], datas["phone"], datas["message"])
        return render_template("contact.html", msg="Form submission successful!", msg_sent=True,
                               login=db.get_or_404(EcomUsers, current_user.id))
    return render_template("contact.html", msg_sent=False, login=db.get_or_404(EcomUsers, current_user.id))



def send_email(name, email, phone, message):
    print(name, email, phone, message)
    username = os.environ.get('email')
    password = os.environ.get('password')
    email_message = f"Subject:Form Data Message\n\nHi Ej,\nName: {name}\nEmail: {email}\nPhone: {phone}\nMessage:{message}"
    print(email_message)
    with smtplib.SMTP("smtp.gmail.com", port=587) as connection:
        connection.starttls()
        connection.login(user=username, password=password)
        connection.sendmail(from_addr=os.environ.get('email'), to_addrs=os.environ.get('to'),
                            msg=email_message.encode('utf-8'))
        print("Mail sent")

@app.route('/about')
@login_required
def about():
    return render_template("about.html", login=db.get_or_404(EcomUsers, current_user.id))


@app.route('/remove_cart', methods=["POST"])
@login_required
def remove_cart():
    id = request.args.get("ids")
    # print(f"id {id}")
    cart_delete_p = db.session.execute(db.select(Cart).where(Cart.id == id)).scalar()
    db.session.delete(cart_delete_p)
    db.session.commit()
    return redirect(url_for('cart'))


@app.route('/cart', methods=["GET", "POST"])
@login_required
def cart():
    data = False
    author = []
    quantity = []
    products_id = []
    p_data = []
    price_id = []
    price_data = []
    price = []
    cart_id = []
    result = db.session.execute(db.select(Cart)).scalars()
    for i in result:
        if int(i.author_id) == current_user.id:
            quantity.append(i.quantity)
            author.append(i.author_id)
            products_id.append(i.product_id)
            cart_id.append(i.id)

    length = len(quantity)

    for i in products_id:
        p_data.append(stripe.Product.retrieve(i))

    for i in p_data:
        price_id.append(i["default_price"])

    for i in price_id:
        price_data.append(stripe.Price.retrieve(i))

    for i in price_data:
        price.append(str(i["unit_amount"])[:-2])
    sub_total = 0
    for i in range(0, len(quantity)):
        sub_total += int(quantity[i]) * int(price[i])
    #
    # print(sub_total)

    for i in author:
        if int(i) == current_user.id:
            data = True

    if data is False:
        value = "No Products in cart🛒, Please add some to checkout"
        return render_template("cart.html", value=value, data=False, login=db.get_or_404(EcomUsers, current_user.id))
    else:
        return render_template("cart.html", len=length, result2=quantity, result=p_data, amount=sub_total, data=True,
                               price=price,
                               cart=cart_id, login=db.get_or_404(EcomUsers, current_user.id), user_id=current_user.id,
                               author=author, price_id=price_id)


@app.route('/product_details', methods=["GET", "POST"])
@login_required
def product_details():
    success = request.args.get("success")
    if success is None:
        success = ""

    id = request.args.get("id")
    result = db.session.execute(
        db.select(Cart).where((and_(Cart.product_id == id, Cart.author_id == current_user.id)))).scalar()
    if result is not None:
        if int(result.author_id) == current_user.id:
            added = True
            # print("1")
        else:
            added = False
            # print("2")
    else:
        added = False
        # print("3")
    # print(added)

    data = stripe.Product.retrieve(id)
    # print(data)

    price = stripe.Price.retrieve(data["default_price"])
    price = str(price["unit_amount"])[:-2]

    if request.method == "POST":
        success = request.args.get("success")
        if success is None:
            success = ""

        if result is not None:
            if int(result.author_id) == current_user.id:
                added = True
                # print("1")
            else:
                added = False
                # print("2")
        else:
            added = False
            # print("3")
        # print(added)

        return render_template("product_details.html", result=data, price=price, success=success, added=added,
                               login=db.get_or_404(EcomUsers, current_user.id))
    return render_template("product_details.html", result=data, price=price, success=success, added=added,
                           login=db.get_or_404(EcomUsers, current_user.id))


@app.route('/add_product', methods=["POST"])
@login_required
def add_product():
    id = request.args.get("id")
    quantity = request.form.get("quantity")
    carts = Cart(product_id=id, quantity=quantity, author_id=current_user.id)
    db.session.add(carts)
    db.session.commit()
    success = "Item Added to Cart"
    return redirect(url_for("product_details", success=success, id=id))





@app.route('/create-checkout-session', methods=["GET",'POST'])
@login_required
def create_checkout_session():
    data = []
    product_id = []
    products = []
    quantity = []
    price_id = []
    result = db.session.execute(db.select(Cart)).scalars()
    for i in result:
        if int(i.author_id) == current_user.id:
            quantity.append(i.quantity)
            product_id.append(i.product_id)
    for i in product_id:
        products.append(stripe.Product.retrieve(i))

    for i in products:
        price_id.append(i["default_price"])

    for i in range(0,len(price_id)):
        data.append({"price":price_id[i],"quantity":quantity[i]})

    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=data,
            shipping_address_collection={"allowed_countries": ["IN"]},
            shipping_options=[
                {
                    "shipping_rate_data": {
                        "type": "fixed_amount",
                        "fixed_amount": {"amount": 0, "currency": "inr"},
                        "display_name": "Free shipping",
                        "delivery_estimate": {
                            "minimum": {"unit": "business_day", "value": 5},
                            "maximum": {"unit": "business_day", "value": 7},
                        },
                    },
                },
                {
                    "shipping_rate_data": {
                        "type": "fixed_amount",
                        "fixed_amount": {"amount": 1500, "currency": "inr"},
                        "display_name": "Next day air",
                        "delivery_estimate": {
                            "minimum": {"unit": "business_day", "value": 1},
                            "maximum": {"unit": "business_day", "value": 1},
                        },
                    },
                },
            ],
            allow_promotion_codes=True,
            mode='payment',
            phone_number_collection={"enabled": True},
            success_url=YOUR_DOMAIN + '/success',
            cancel_url=YOUR_DOMAIN + '/cancel',
        )
    except Exception as e:
        print(e)
        return redirect(url_for("cancel"))

    return redirect(checkout_session.url, code=303)


@app.route('/checkout', methods=["GET", "POST"])
def checkout():
    return render_template("checkout.html")


@app.route('/success', methods=["GET", "POST"])
def success():
    return render_template("success.html")


@app.route('/cancel', methods=["GET", "POST"])
def cancel():
    return render_template("cancel.html")


if __name__ == "__main__":
    app.run(debug=True)

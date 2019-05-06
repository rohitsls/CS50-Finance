import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash


from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    user = db.execute("SELECT username FROM users WHERE id=:id", id=session["user_id"])
    portfolio = db.execute("SELECT stock,symbol, SUM(shares) as num_shares, price FROM portfolio WHERE username=:username GROUP BY stock",
            username=user[0]["username"])

    rows = db.execute("SELECT cash FROM users WHERE id=:id",id=session["user_id"])

    available_cash = rows[0]["cash"]

    return render_template("index.html", portfolio=portfolio,available_cash=available_cash)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        cash = db.execute("SELECT cash FROM users WHERE id = :id", id=session["user_id"])

        user = db.execute("SELECT username FROM users WHERE id=:id", id = session["user_id"])

        stock = lookup(request.form.get("stock_name"))
        number = int(request.form.get("num_shares"))

        if not stock:
            return apology("Wrong Symbol")

        elif float(cash[0]["cash"]) < stock["price"] * number:
            return apology("Not enough funds you poor mofo!! HAHAHA")



        db.execute("INSERT INTO portfolio (username,stock,price,shares,symbol) VALUES (:username, :stock,:price,:shares,:symbol)",
                                username = user[0]["username"], stock=stock["name"], price=stock["price"],
                                shares=request.form.get("num_shares"),symbol=stock["symbol"])

        db.execute("UPDATE users SET cash = cash - :total_price WHERE id = :id", total_price=stock["price"]*number
                        , id=session["user_id"])

        return redirect("/")
    else:
        return render_template("buy.html")




@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    user = db.execute("SELECT username FROM users WHERE id=:id", id=session["user_id"])

    transactions = db.execute("SELECT symbol, stock, shares, price, date FROM portfolio WHERE username=:username",
                                username=user[0]["username"])

    return render_template("history.html", transactions=transactions)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        quote = lookup(request.form.get("stock_name"))
        if quote:
            return render_template("stock_info.html", name=quote["name"], symbol=quote["symbol"], price=quote["price"])
        else:
            return apology("Wrong symbol")
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        if not request.form.get("username"):
            return apology("Missing Username!")
        elif not request.form.get("password"):
            return apology("Missing Password!")
        elif not request.form.get("conf_pwd"):
            return apology("Please re-enter password")

        if request.form.get("password") != request.form.get("conf_pwd"):
            return apology("Passwords don't match!! Re-enter password")


        password = generate_password_hash(request.form.get("password"))

        result = db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)",username=request.form.get("username")
                            ,hash=password)
        if not result:
            return apology("Username already exists! Try again")

        session["user_id"] = result

        return redirect("/")

    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    user = db.execute("SELECT username FROM users WHERE id=:id", id=session["user_id"])

    if request.method == "POST":
        stock = lookup(request.form.get("symbol"))
        if not stock:
            return apology("Select a stock dum dum!!")

        shares = int(request.form.get("shares"))

        if shares < 0:
            return apology("Positive you idiot")

        available_shares = db.execute("SELECT SUM(shares) as total_shares FROM portfolio WHERE username=:username and symbol=:symbol GROUP BY symbol",
                            username = user[0]["username"], symbol=stock["symbol"])

        if available_shares[0]["total_shares"] < 1 or shares > available_shares[0]["total_shares"]:
            return apology("Not enough shares, poor indian hahah")

        current_price = stock["price"]
        total = current_price*shares

        db.execute("UPDATE users SET cash = cash + :total WHERE id=:id", total=total, id=session["user_id"])
        db.execute("INSERT INTO portfolio (username,stock,price,shares,symbol) VALUES (:username, :stock,:price,:shares,:symbol)",
                                username = user[0]["username"], stock=stock["name"], price=stock["price"],
                                shares=-shares,symbol=stock["symbol"])
        return redirect("/")
    else:

        available_stocks = db.execute("SELECT symbol, SUM(shares) as total_shares FROM portfolio WHERE username=:username GROUP BY symbol",
                                        username=user[0]["username"])
        return render_template("sell.html", available_stocks=available_stocks)


def errorhandler(e):
    """Handle error"""
    return apology(e.name, e.code)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)

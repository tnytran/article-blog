from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps

app = Flask(__name__)

# Config MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '12345678'
app.config['MYSQL_DB'] = 'articles'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'


# Init MySQL
mysql = MySQL(app)


@app.route('/')
def index():
    return render_template('home.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/articles')
def articles():
    # Create cursor:
    cur = mysql.connection.cursor()

    # Get article:
    result = cur.execute("SELECT * FROM article")

    articles = cur.fetchall()

    if result >= 0:
        return render_template('articles.html', articles=articles)
    else:
        msg = 'No article found.'
        return render_template('articles.html', msg=msg)

    # Close connection:
    cur.close()


@app.route('/article/<string:id>/')
def article(id):
    # Create cursor:
    cur = mysql.connection.cursor()

    # Get article:
    result = cur.execute("SELECT * FROM article WHERE id=%s", [id])

    article = cur.fetchone()

    return render_template('article.html', article=article)


class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password',
                             [
                                 validators.DataRequired(),
                                 validators.EqualTo(
                                     'confirm', message='Passwords do not match.')
                             ])
    confirm = PasswordField('Confirm Password')


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        # Create cursor:
        cur = mysql.connection.cursor()

        # Execute query
        cur.execute("INSERT INTO users(name, email, username, password) VALUES(%s, %s, %s, %s)",
                    (name, email, username, password))

        # Commit to db:
        mysql.connection.commit()

        # Close connection:
        cur.close()

        # Flash message:
        flash('You are now registered. Please login to continue.', 'success')

        # Redirect to Login page:
        return redirect(url_for('login'))

    return render_template('register.html', form=form)


# User login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get form fields
        username = request.form['username']
        password_candidate = request.form['password']

        # Create cursor
        cur = mysql.connection.cursor()

        # Get user by username
        result = cur.execute(
            "SELECT * FROM users WHERE username = %s",  [username])

        if result > 0:
            # Get stored hash:
            data = cur.fetchone()
            password = data['password']

            # Compare passwords
            if sha256_crypt.verify(password_candidate, password):
                # app.logger.info('PASSWORD MATCHED')

                # Passed:
                session['logged_in'] = True
                session['username'] = username

                flash('You are now logged in.', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid password.'
                return render_template('login.html', error=error)

            # Close connection:
            cur.close()

        else:
            error = 'Username not found.'
            return render_template('login.html', error=error)

    return render_template('login.html')


# Check if user logged in, they can access to authorized page via the URL.
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, *kwargs)
        else:
            flash('Unathorized. Please login to continue.', 'danger')
            return redirect(url_for('login'))
    return wrap


# Log out
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out.', 'success')
    return redirect(url_for('login'))


# Dashboard after logging in:
@app.route('/dashboard')
@is_logged_in
def dashboard():
    # Create cursor:
    cur = mysql.connection.cursor()

    # Get article:
    username = session['username']
    result = cur.execute("SELECT * FROM article WHERE author=%s;", [username])

    articles = cur.fetchall()

    if result >= 0:
        return render_template('dashboard.html', articles=articles)
    else:
        msg = 'No article found.'
        return render_template('dashboard.html', msg=msg)

    # Close connection:
    cur.close()


# Article class:
class ArticleForm(Form):
    title = StringField('Title', [validators.Length(min=1, max=200)])
    body = TextAreaField('Body', [validators.Length(min=30)])


# Add article:
@app.route('/add_article', methods=['GET', 'POST'])
def add_article():
    form = ArticleForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        body = form.body.data

        # Create cursor:
        cur = mysql.connection.cursor()

        # Execute
        cur.execute("INSERT INTO article(title, body, author) VALUES(%s, %s, %s)",
                    (title, body, session['username']))

        # Commit to db:
        mysql.connection.commit()

        # Close connection:
        cur.close()

        flash('Article has been created successfully.', 'success')
        return redirect(url_for('dashboard'))

    return render_template('add_article.html', form=form)


# Edit article:
@app.route('/edit_article/<string:id>', methods=['GET', 'POST'])
def edit_article(id):
    # Create cursor
    cur = mysql.connection.cursor()

    # Get article by id
    result = cur.execute(
        "SELECT * FROM article WHERE id=%s;", [id]
    )

    article = cur.fetchone()
    cur.close()

    # Get form
    form = ArticleForm(request.form)

    # Populate article form fields
    form.title.data = article['title']
    form.body.data = article['body']

    if request.method == 'POST' and form.validate():
        title = request.form['title']
        body = request.form['body']

        # Create Cursor
        cur = mysql.connection.cursor()
        app.logger.info(title)

        # Execute
        cur.execute(
            "UPDATE article SET title=%s, body=%s WHERE id=%s;", (title, body, id))

        # Commit to DB
        mysql.connection.commit()

        # Close connection
        cur.close()

        flash('Article has been updated successfully.', 'success')

        return redirect(url_for('dashboard'))

    return render_template('edit_article.html', form=form)


# Delete Article:
@app.route('/delete_article/<string:id>/')
def delete_article(id):
    # Create cursor:
    cur = mysql.connection.cursor()

    # Execute
    cur.execute("DELETE FROM article WHERE id=%s;", [id])

    # Commit to db:
    mysql.connection.commit()

    # Close connection:
    cur.close()

    flash('Article has been deleted successfully.', 'success')

    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    app.secret_key = 'secret123'
    app.run(debug=True)

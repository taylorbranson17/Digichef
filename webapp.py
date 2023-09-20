from flask import Flask, session, render_template as r, request, flash
from werkzeug.utils import redirect, secure_filename
import os
from Sqlite import SqliteDriver, DatabaseError, IntegrityError
from authenticate import authenticate

app = Flask(__name__)
app.secret_key = "oompa loompa"
UPLOAD_FOLDER = './static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def welcome():
    return r('welcome.html')

@app.route('/login', methods=['GET'])
def login() -> 'html':
    return r('login.html')

@app.route('/login', methods=['POST'])
def process_login():
    try:
        with SqliteDriver('digichef.db') as cursor:
            cursor.execute('SELECT * FROM users WHERE email = ?',
                        (request.form['username'],))
            results = cursor.fetchone()
            if results == None:
                flash("Not a valid username. Try again.")
                return redirect('/login', code=302)
            cursor.execute('SELECT * FROM users WHERE email = ? and password = ?', (request.form['username'], request.form['password']))
            sec_results = cursor.fetchone()
            if sec_results == None:
                flash('Not a valid password. Try again.')
                return redirect('/login', code=302)
            
        session['user_id'] = sec_results['id']
        session['first_name'] = sec_results['first_name']
        session['last_name'] = sec_results['last_name']
        session['img'] = sec_results['img']
        session['theme'] = sec_results['theme']
        return redirect('/dashboard', code=302)
    
    except DatabaseError as err:
        print('Something went wrong connecting to your database.', str(err))
        err = {'title': 'Connection Error', 'message': "Something went wrong with the login, please try again later."}
        return r('login.html', err=err)
        
    except IntegrityError as err:
        print('There was a violation in table integrity.', str(err))
        err = {'title':'Data Conundrum!', 'message': 'Your data got jumbled, please try again in a little bit.'}
        return r('login.html', err=err)

    except Exception as err:
        print("There's been an error!", str(err))
        err = {'title': 'Unknown Error', 'message': "An unknown error has occurred- please try again later."}
        return r('login.html', err=err)

@app.route('/register', methods=['GET'])
def register():
    return r('register.html', title="Register", action="/register", btn_label="Register", message="Welcome to DigiChef!")

@app.route('/register', methods=['POST'])
def process_register():
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    email = request.form['email']
    password = request.form['password']
    confirm = request.form['confirm']

    errors = {}
    if first_name == '':
        errors['first_name'] = "First name is a required field."
    if last_name == '':
        errors['last_name'] = "Last name is a required field."
    if email == '':
        errors['email'] = "Email is a required field."
    if password == '' or confirm == '':
        errors['password'] = "You must enter a password."
    if confirm == '':
        errors['confirm'] = "Please confirm your password."
    if confirm != password:
        errors['match'] = "You passwords do not match. Please try again."

    with SqliteDriver('digichef.db') as cursor:
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        results = cursor.fetchone()
    if results != None:
        errors['email'] = "This email has already been used."

    if len(errors) > 0:
        return r('register.html', errors=errors, data=request.form, title="Register", action="/register", btn_label="Register", message="Welcome to Digichef!")
    
    with SqliteDriver('digichef.db') as cursor:
        cursor.execute('INSERT INTO users (first_name, last_name, email, password) VALUES (?,?,?,?)',
                       (first_name, last_name, email, password))
        user_id = cursor.lastrowid

        if 'profile_image' or 'theme_image' in request.files:
            theme = request.files['theme_image']
            profile = request.files['profile_image']
            if theme.filename != '':
                if allowed_file(theme.filename):
                    filename = secure_filename(theme.filename)
                    theme.save(os.path.join(
                        app.config['UPLOAD_FOLDER'], filename))
                    cursor.execute(
                        "UPDATE users SET theme = ? WHERE id = ?", (filename, user_id))
                    session['theme'] = filename
            if profile.filename != '':
                if allowed_file(profile.filename):
                    filename2 = secure_filename(profile.filename)
                    profile.save(os.path.join(
                        app.config['UPLOAD_FOLDER'], filename2))
                    cursor.execute(
                        "UPDATE users SET img = ? WHERE id = ?", (filename2, user_id))
                    session['img'] = filename2

    session['user_id'] = user_id
    session['first_name'] = first_name
    session['last_name'] = last_name

    return redirect('/dashboard')

@app.route('/dashboard')
@authenticate
def dashboard() -> 'html':
    with SqliteDriver('digichef.db') as cursor:
        cursor.execute('SELECT*FROM recipes WHERE user_id = ? LIMIT 3', (session['user_id'],))
        results = cursor.fetchall()
        if len(results) < 1:
            return r('dashboard.html', link_msg="Add Recipes")
    return r('dashboard.html', data=results, link_msg="View All")

@app.route('/recipes', methods=['GET'])
@authenticate
def recipes():
    with SqliteDriver('digichef.db') as cursor:
        cursor.execute('SELECT*FROM recipes WHERE user_id = ?',
                       (session['user_id'],))
        results = cursor.fetchall()
    return r('recipes.html', data=results)

@app.route('/account/edit', methods=['GET'])
@authenticate
def edit_account():
    with SqliteDriver('digichef.db') as cursor:
        cursor.execute('SELECT*FROM users WHERE id = ?', (session['user_id'],))
        result = cursor.fetchone()
    return r('register.html', data=result, message=session['first_name'] + "'s Account", btn_label="Save", action='/account/edit')

@app.route('/account/edit', methods=['POST'])
@authenticate
def process_edit():
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    email = request.form['email']
    password = request.form['password']
    confirm = request.form['confirm']

    errors = {}
    if first_name == '':
        errors['first_name'] = "First name is a required field."
    if last_name == '':
        errors['last_name'] = "Last name is a required field."
    if email == '':
        errors['email'] = "Email is a required field."

    with SqliteDriver('digichef.db') as cursor:
        cursor.execute(
            'SELECT * FROM users WHERE email = ? AND id != ?', (email, session['user_id']))
        results = cursor.fetchone()
    if results != None:
        errors['email'] = "This email has already been used."

    if len(errors) > 0:
        return r('register.html', errors=errors, data=request.form, title=session['first_name'] + "'s Account", btn_label="Save", action="/account/edit")

    with SqliteDriver('digichef.db') as cursor:
        cursor.execute('UPDATE users SET first_name = ?, last_name = ?, email = ? WHERE id = ?',
                       (first_name, last_name, email, session['user_id']))

        if password != '' and confirm == password:
            cursor.execute(
                "UPDATE users SET password = ? WHERE id = ?", (password, session['user_id']))

        if 'profile_image' or 'theme_image' in request.files:
            theme = request.files['theme_image']
            profile = request.files['profile_image']
            if theme.filename != '':
                if allowed_file(theme.filename):
                    filename = secure_filename(theme.filename)
                    theme.save(os.path.join(
                        app.config['UPLOAD_FOLDER'], filename))
                    cursor.execute(
                        "UPDATE users SET theme = ? WHERE id = ?", (filename, session['user_id']))
                    session['theme'] = filename
            if profile.filename != '':
                if allowed_file(profile.filename):
                    filename2 = secure_filename(profile.filename)
                    profile.save(os.path.join(
                        app.config['UPLOAD_FOLDER'], filename2))
                    cursor.execute(
                        "UPDATE users SET img = ? WHERE id = ?", (filename2, session['user_id']))
                    session['img'] = filename2

    session['first_name'] = first_name
    session['last_name'] = last_name

    flash("Your profile has been updated.")
    return redirect('/dashboard', code=302)

@app.route('/recipes/add', methods=['GET'])
@authenticate
def add_recipe():
    return r('add_recipe.html', action="/recipes/add")

@app.route('/recipes/add', methods=['POST'])
@authenticate
def process_recipe():
    data = {
        'name': request.form['name'],
        'cooktime': request.form['cooktime'],
        'ingredients': request.form['ingredients'],
        'instructions': request.form['instructions'],
        'notes': request.form['notes'],
    }

    with SqliteDriver('digichef.db') as cursor:
        cursor.execute('INSERT INTO recipes (name, user_id, cooktime, ingredients, instructions, notes) VALUES (?,?,?,?,?,?)',
                       (data['name'], session['user_id'], data['cooktime'], data['ingredients'], data['instructions'], data['notes']))
        last_id = cursor.lastrowid
        
        if 'recipeimg' in request.files:
            print('Found file in request.files.')
            file = request.files['recipeimg']
            if file.filename != '':
                print('Filename isn"t empty.')
                if allowed_file(file.filename):
                    print('File name is allowed.')
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    print('Saved file to uploads.')
                    cursor.execute("UPDATE recipes SET img = ? WHERE id = ? AND user_id = ?", (filename, last_id, session['user_id']))

    flash('Recipe has been added.')
    return redirect('/recipes', code=302)

@app.route('/recipe/<id>/edit', methods=['GET'])
def edit_recipe(id):
    with SqliteDriver('digichef.db') as cursor:
        cursor.execute(
            'SELECT*FROM recipes WHERE id = ? and user_id = ?', (id, session['user_id']))
        recipe = cursor.fetchone()
    return r('add_recipe.html', data=recipe, action="/recipe/" + id + "/edit")

@app.route('/recipe/<id>/edit', methods=['POST'])
def get_recipe(id):
        
    data = {
        'name': request.form['name'],
        'cooktime': request.form['cooktime'],
        'ingredients': request.form['ingredients'],
        'instructions': request.form['instructions'],
        'notes': request.form['notes'],
    }

    with SqliteDriver('digichef.db') as cursor:
        cursor.execute('UPDATE recipes SET name = ?, cooktime = ?, ingredients = ?, instructions = ?, notes = ? WHERE id = ? AND user_id = ?',
                       (data['name'], data['cooktime'], data['ingredients'], data['instructions'], data['notes'], id, session['user_id']))
        
        if 'recipeimg' in request.files:
            print('Found file in request.files.')
            file = request.files['recipeimg']
            if file.filename != '':
                print('Filename isn"t empty.')
                if allowed_file(file.filename):
                    print('File name is allowed.')
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    print('Saved file to uploads.')
                    cursor.execute("UPDATE recipes SET img = ? WHERE id = ? AND user_id = ?", (filename, id, session['user_id']))
    
    flash("Your recipe has been updated.")
    return redirect('/recipes', code=302)

@app.route('/recipe/<id>/view', methods=['GET'])
def view_recipe(id):
    with SqliteDriver('digichef.db') as cursor:
        cursor.execute('SELECT * FROM recipes WHERE id = ? AND user_id = ?', (id, session['user_id']))
        result = cursor.fetchone()
        data = {
            'id':result['id'],
            'user_id':result['user_id'],
            'name':result['name'],
            'instructions': result['instructions'].replace('\n', '<br>'),
            'ingredients': result['ingredients'].replace('\n', '<br>'),
            'notes': result['notes'].replace('\n', '<br>'),
            'cooktime': result['cooktime'],
            'img': result['img']
        }
    return r('view_recipe.html', data=data)

@app.route('/recipe/<id>/delete', methods=['GET'])
def delete_recipe(id):
    with SqliteDriver('digichef.db') as cursor:
        cursor.execute('DELETE FROM recipes WHERE id = ? AND user_id = ?', (id, session['user_id']))
    return redirect('/recipes', code=302)

@app.route('/logout')
def logout_user():
    session.pop('user_id')
    session.pop('last_name')
    session.pop('first_name')
    if 'theme' in session:
        session.pop('theme')
    if 'img' in session:
        session.pop('img')
    return redirect('/login', code=302)


app.run(debug=True)
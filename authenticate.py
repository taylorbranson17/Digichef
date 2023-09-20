from flask import session
from werkzeug.utils import redirect
from functools import wraps

def authenticate(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'user_id' in session:
            return func(*args,**kwargs)
        return redirect('/login', code=302)
    return wrapper
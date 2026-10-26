from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt, get_current_user



def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            usuario = get_current_user()
            
            if usuario.role not in roles:
                return jsonify(erro="sem acesso"), 403
            
            
            return fn(*args, **kwargs)
        return wrapper
    return decorator

            
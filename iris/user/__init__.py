from functools import wraps
import json
import random
from os.path import dirname, join

import flask
from flask_login import login_required, current_user, login_user, logout_user
from sqlalchemy import func
from validate_email import validate_email

from iris import db
from iris.models import Action, User
from iris.project import project

from iris.login import login_manager

user_app = flask.Blueprint(
    'user', __name__,
    template_folder='templates',
    static_folder='static'
)

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))


@login_manager.request_loader
def load_user_from_request(request):
    auth = request.authorization
    if not auth:
        return None
    user = User.query.filter_by(username=auth.username).first()
    if user is None:
        user = User.query.filter_by(email=auth.username).first()
    if not user or not user.check_password(auth.password):
        return None
    return user

@login_manager.unauthorized_handler
def unauthorized():
    # do stuff
    return flask.make_response('Not logged in!', 403)

@user_app.route('/')
def index():
    pass


def roles_required(role="ANY"):
    def wrapper(func):
        @wraps(func)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()
            if not current_user.admin:
                return login_manager.unauthorized()
            return func(*args, **kwargs)

        return decorated_view

    return wrapper

def admin_required(role="ANY"):
    def wrapper(func):
        @wraps(func)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()
            if not current_user.admin:
                return login_manager.unauthorized()
            return func(*args, **kwargs)

        return decorated_view

    return wrapper

@user_app.route('/get/<user_id>', methods=['GET'])
@login_required
def get(user_id):
    if user_id == 'current':
        user_id = current_user.id
    
    query_user = User.query.get_or_404(user_id)

    json_user = query_user.to_json()
    
    if user_id==current_user.id or current_user.admin:
        
        json_user['config'] = project.get_user_config(user_id)

        return flask.jsonify(json_user)
    else:
        del json_user['email']
        return flask.jsonify(json_user)

@user_app.route('/set/<user_id>', methods=['POST'])
@login_required
def set(user_id):
    
    
    if user_id == 'current':
        user_id = current_user.id
    
    if current_user.id != user_id and not current_user.admin:
        return flask.make_response("Permission denied!", 403)

    query_user = User.query.get_or_404(user_id);

    for k, v in json.loads(flask.request.data).items():
        if k == "admin":
            query_user.admin = bool(v)
        else:
            return flask.make_response(f"Unknown parameter <i>{k}</i>!", 400)

    db.session.add(query_user)
    db.session.commit()

    return flask.make_response("Saved new user info successfully")

@user_app.route('/show/<user_id>', methods=['GET'])
@login_required
def show(user_id):
    
    if user_id == 'current':
        user_id = current_user.id

    query_user = User.query.get(user_id)
    
    if query_user is None:
        return flask.make_response('Unknown user id!', 404)
    user_json = query_user.to_json()

    total_score = func.sum(Action.score).label("total_score")
    top_users = (db.session.query(User.name, total_score)
        .join(User.actions)
        .filter(Action.type=="segmentation")
        .group_by(User.name)
        .order_by(total_score.desc())
    ).all()
    if top_users:
        usernames, scores = zip(*top_users)
        user_json['segmentation']['rank'] = usernames.index(query_user.name) + 1

    user_json['segmentation']['last_masks'] = Action.query \
        .filter_by(user=query_user, type="segmentation") \
        .order_by(Action.last_modification.desc()) \
        .limit(10) \
        .all()


    if current_user.id == user_id:
        return flask.render_template(
            'user/show.html', user=user_json,
            current_user=user_json
        )
    else:

        return flask.render_template(
            'user/show.html', user=user_json,
            current_user=current_user.to_json()
        )

@user_app.route('/config', methods=['GET'])
@login_required
def config():
    config = project.get_user_config(current_user.id)
    all_bands = project.get_image_bands(project.image_ids[0])
    config['segmentation']['ai_model']['bands'] = {
        band
        for band in all_bands
        if config['segmentation']['ai_model']['bands'] is None or band in config['segmentation']['ai_model']['bands']
    }

    return flask.render_template(
        'user/config.html', config=config, all_bands=all_bands
    )

@user_app.route('/save_config', methods=['POST'])
@login_required
def save_config():
    user_config = json.loads(flask.request.data)
    project.save_user_config(
        current_user.id,
        user_config
    )
    return flask.make_response('Saved user config successfully!')
#??????

@user_app.route('/register', methods=['POST'])
def register():
    data = json.loads(flask.request.data)
    if len(data['username']) > 64:
        return flask.make_response('Username is too long!', 400)
    if not data['username']:
        return flask.make_response('Username is a required field!', 400)
    if User.query.filter(User.name == data['username']).first() is not None:
        return flask.make_response('Username already exists!', 400)
    if data.get("email", False):
        if len(data['email']) > 128:
            return flask.make_response('E-mail address is too long!', 400)
        if User.query.filter(User.email == data['email']).first() is not None:
            return flask.make_response('E-mail already exists!', 400)
    if not data['password']:
        return flask.make_response('Password is a required field!', 400)
    if len(data['password']) > 64:
        return flask.make_response('Password is too long!', 400)

    new_user = User(
        name=data['username'],
        email=data['email'],
        admin=False,
    )
    new_user.set_password(data['password'])
    db.session.add(new_user)
    db.session.commit()

    #set_current_user(new_user)

    return flask.make_response(f"{new_user} successfully created!")

@user_app.route('/login', methods=['POST'])
def login():
    
    if current_user.is_authenticated:
        return flask.make_response("Successful login!")
    
    #else
    data = json.loads(flask.request.data)

    if not (data.get('username', False) and data.get('password', False)):
        return flask.make_response('Username and password are required fields!', 400)

    user = User.query.filter(User.name == data['username']).first()

    if user is None or not user.check_password(data['password']):
        return flask.make_response("Username or password are incorrect!", 403)

    login_user(user)

    return flask.make_response("Successful login!")


@user_app.route('/logout')
def logout():
    logout_user()

    return flask.make_response("Successful logout!")

    

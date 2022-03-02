from collections import defaultdict
from datetime import timedelta

import flask
from flask_login import login_required, current_user
from sqlalchemy import func

from iris.user import roles_required
from iris.models import db, Action, User
from iris.project import project

admin_app = flask.Blueprint(
    'admin', __name__,
    template_folder='templates',
    static_folder='static'
)

@admin_app.route('/', methods=['GET'])
def index():

    if current_user.is_anonymous:
        return flask.render_template('admin/index.html', user=None)

    return flask.redirect(flask.url_for('admin.users'))

@admin_app.route('/users', methods=['GET'])
@login_required
@roles_required('admin')
def users():

    order_by = flask.request.args.get('order_by', 'id')
    ascending = flask.request.args.get('ascending', 'true')
    ascending = True if ascending == 'true' else False

    users = User.query
    if ascending:
        users = users.order_by(getattr(User, order_by)).all()
    else:
        users = users.order_by(getattr(User, order_by).desc()).all()

    users_json = [u.to_json() for u in users]

    html = flask.render_template('admin/users.html', users=users_json, order_by=order_by, ascending=ascending)
    return flask.render_template('admin/index.html', user=current_user, page=flask.Markup(html))

@admin_app.route('/actions/<type>', methods=['GET'])
@login_required
@roles_required('admin')
def actions(type):

    order_by = flask.request.args.get('order_by', 'user_id')
    ascending = flask.request.args.get('ascending', 'true')
    ascending = True if ascending == 'true' else False

    actions = Action.query.filter_by(type=type)
    if ascending:
        actions = actions.order_by(getattr(Action, order_by)).all()
    else:
        actions = actions.order_by(getattr(Action, order_by).desc()).all()

    actions_json = [
        {**action.to_json(), 'username': action.user.name}
        for action in actions
    ]
    image_stats = {
        "processed": len(set(action.image_id for action in actions)),
        "total": len(project.image_ids)
    }

    html = flask.render_template(
        'admin/actions.html', action_type=type, actions=actions_json,
        image_stats=image_stats, order_by=order_by, ascending=ascending
    )
    return flask.render_template('admin/index.html', user=current_user, page=flask.Markup(html))

@admin_app.route('/images', methods=['GET'])
@login_required
@roles_required('admin')
def images():

    order_by = flask.request.args.get('order_by', 'user_id')
    ascending = flask.request.args.get('ascending', 'true')
    ascending = True if ascending == 'true' else False

    # TODO: make this more performant by using less database calls
    images = defaultdict(dict)
    actions = Action.query.all();
    default_stats = {
        'score': 0,
        'count': 0,
        'difficulty': 0,
        'time_spent': timedelta(),
    }
    for image_id in project.image_ids:
        for action in actions:
            if action.image_id != image_id:
                continue

            if action.type not in images[image_id]:
                images[image_id][action.type] = default_stats.copy()

            images[image_id][action.type]['count'] += 1
            images[image_id][action.type]['score'] += action.score
            images[image_id][action.type]['difficulty'] += action.difficulty
            images[image_id][action.type]['time_spent'] += action.time_spent

        # Calculate the average values:
        for stats in images[image_id].values():
            stats['score'] /= stats['count']
            stats['difficulty'] /= stats['count']
            stats['time_spent'] /= stats['count']
            stats['time_spent'] = stats['time_spent'].total_seconds() / 3600.

    html = flask.render_template(
        'admin/images.html', images=images, order_by=order_by, ascending=ascending
    )
    return flask.render_template('admin/index.html', user=current_user, page=flask.Markup(html))

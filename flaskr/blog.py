import os
from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort
from werkzeug.utils import secure_filename

from flaskr.auth import login_required
from flaskr.db import get_db

bp = Blueprint('blog', __name__)

UPLOAD_FOLDER = '/var/www/Dev/Flask/flask-tutorial/flaskr/uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}


@bp.route('/')
def index():
    db = get_db()
    posts = db.execute(
        'SELECT p.id, title, body, created, author_id, username'
        ' FROM post p JOIN user u ON p.author_id = u.id'
        ' ORDER BY created DESC'
    ).fetchall()
    return render_template('blog/index.html', posts=posts)


@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        error = None

        if not title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            row = db.execute(
                'INSERT INTO post (title, body, author_id)'
                ' VALUES (?, ?, ?)',
                (title, body, g.user['id'])
            )
            db.commit()

            post_id = row.lastrowid

            if 'file' in request.files:
                file = request.files['file']
                if file and file.filename != '':
                    if not allowed_file(file.filename):
                        flash('File must be JPG')
                        db.rollback()
                        return redirect(request.url)
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(UPLOAD_FOLDER, filename))

                    print('filename')
                    print(filename)

                    db = get_db()
                    db.execute(
                        'INSERT INTO post_image (post_id, name)'
                        ' VALUES (?, ?)',
                        (post_id, filename)
                    )
            return redirect(url_for('blog.index'))

    return render_template('blog/create.html')


def get_post(id, check_author=True):
    post = get_db().execute(
        'SELECT p.id, title, body, created, author_id, username'
        ' FROM post p JOIN user u ON p.author_id = u.id'
        ' WHERE p.id = ?',
        (id,)
    ).fetchone()

    if post is None:
        abort(404, f"Post id {id} doesn't exist.")

    if check_author and post['author_id'] != g.user['id']:
        abort(403)

    return post


def get_post_comment(comment_id, post_id, user_id, check_author=True):
    post_comment = get_db().execute(
        'SELECT p.id, post_id, body, created, user_id, username'
        ' FROM post_comment p JOIN user u ON p.user_id = u.id'
        ' WHERE p.id = ? AND p.post_id = ? AND p.user_id = ?',
        (comment_id, post_id, user_id,)
    ).fetchone()

    if post_comment is None:
        abort(404, f"Post Comment id {id} doesn't exist.")

    if check_author and post_comment['user_id'] != g.user['id']:
        abort(403)

    return post_comment


def get_post_like(post_id, user_id):
    like = get_db().execute(
        'SELECT * FROM post_like WHERE post_id = ? AND user_id = ?', (post_id, user_id)
    ).fetchone()

    if like is None:
        return None

    return like


def get_post_like_total(post_id):
    like_total = get_db().execute(
        'SELECT * FROM post_like WHERE post_id = ?', (post_id,)
    ).fetchall()

    return len(like_total)


def get_post_comments(post_id):
    post_comments = get_db().execute(
        'SELECT p.id, post_id, body, created, user_id, username'
        ' FROM post_comment p JOIN user u ON p.user_id = u.id'
        ' WHERE post_id = ?', (post_id,)
    ).fetchall()

    return post_comments


# def get_post_images(post_id):
#     post_images = get_db().execute(
#         'SELECT p.id, post_id, body, created, user_id, username'
#         ' FROM post_image p JOIN user u ON p.user_id = u.id'
#         ' WHERE post_id = ?', (post_id,)
#     ).fetchall()
#
#     return post_images


@bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    post = get_post(id)

    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        error = None

        if not title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'UPDATE post SET title = ?, body = ?'
                ' WHERE id = ?',
                (title, body, id)
            )
            db.commit()
            return redirect(url_for('blog.index'))

    return render_template('blog/update.html', post=post)


@bp.route('/<int:post_id>/post_like')
@login_required
def post_like(post_id):
    like = get_post_like(post_id, g.user['id'])

    if like is None:
        db = get_db()
        db.execute(
            'INSERT INTO post_like (user_id, post_id)'
            ' VALUES (?, ?)',
            (g.user['id'], post_id)
        )
        db.commit()
    else:
        db = get_db()
        db.execute('DELETE FROM post_like WHERE post_id = ? AND user_id = ?', (post_id, g.user['id'],))
        db.commit()

    return redirect(url_for('blog.details', id=post_id))


@bp.route('/<int:id>/details')
@login_required
def details(id):
    post = get_post(id, False)
    like = get_post_like(id, g.user['id'])
    like_total = get_post_like_total(id)
    post_comments = get_post_comments(id)

    return render_template('blog/details.html', post=post, like=like, like_total=like_total,
                           post_comments=post_comments)


@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete(id):
    get_post(id)
    db = get_db()
    db.execute('DELETE FROM post WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('blog.index'))


@bp.route('/<int:post_id>/post_comment', methods=('GET', 'POST'))
@login_required
def post_comment(post_id):
    if request.method == 'POST':
        user_id = g.user['id']
        post_id = post_id
        body = request.form['body']
        error = None

        if not body:
            error = 'Body is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'INSERT INTO post_comment (user_id, post_id, body)'
                ' VALUES (?, ?, ?)',
                (user_id, post_id, body)
            )
            db.commit()

    return redirect(url_for('blog.details', id=post_id))


@bp.route('/<int:post_id>/<int:comment_id>/comment_delete', methods=('POST',))
@login_required
def comment_delete(post_id, comment_id):
    get_post(post_id)
    get_post_comment(comment_id, post_id, g.user['id'])
    db = get_db()
    db.execute('DELETE FROM post_comment WHERE id = ?', (comment_id,))
    db.commit()
    return redirect(url_for('blog.details', id=post_id))


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

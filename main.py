from datetime import date
from flask import Flask, abort, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap5
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import ForeignKey, Integer, String, Text
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import os
from flask_quill import Quill
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_KEY')
bootstrap = Bootstrap5(app)
quill = Quill(app)

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# CREATE DATABASE
class Base(DeclarativeBase):
    pass
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', f"sqlite:///{os.path.join(os.path.dirname(__file__), 'posts.db')}")
db = SQLAlchemy(model_class=Base)
db.init_app(app)

# CONFIGURE TABLES


class User(db.Model, UserMixin):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="author")
    
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    author: Mapped["User"] = relationship(back_populates="posts")
    comments = relationship("Comment", back_populates="post")

class Comment(db.Model):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))  
    author: Mapped["User"] = relationship(back_populates="comments")
    post_id: Mapped[int] = mapped_column(ForeignKey("blog_posts.id"))
    post: Mapped["BlogPost"] = relationship(back_populates="comments")

with app.app_context():
    db.create_all()
    
# 管理者のみがアクセスできるようにするデコレーター
def admin_only(func):
    @wraps(func) # エンドポイントのオリジナルの関数名を保持させる
    def wrapper(*args, **kwargs):
        if current_user.is_authenticated == False or current_user.id != 1:
            return abort(403)
        return func(*args, **kwargs)
    return wrapper

@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if request.method == "POST" and form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data or '').first()
        if user:
            flash("You've already signed up with that email, please log in instead!")
            return redirect(url_for("login"))
        new_user = User(
            email=form.email.data or '',
            password=generate_password_hash(form.password.data or '', method="pbkdf2:sha256", salt_length=8),
            name=form.name.data or ''
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for("get_all_posts"))
    return render_template("register.html", form=form)

@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if request.method == "POST" and form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data or '').first()
        if user and check_password_hash(user.password, form.password.data or ''):
            login_user(user)
            return redirect(url_for("get_all_posts"))
        else:
            flash("Invalid credentials")
    return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route('/')
def get_all_posts():
    result = db.session.execute(db.select(BlogPost))
    posts = result.scalars().all()
    return render_template("index.html", all_posts=posts)

@app.route("/post/<int:post_id>")
def show_post(post_id):
    requested_post = db.get_or_404(BlogPost, post_id)
    comment_form = CommentForm()
    return render_template("post.html", post=requested_post, form=comment_form)

@app.route("/add-comment/<int:post_id>", methods=["POST"])
@login_required
def add_comment(post_id):
    comment_form = CommentForm()
    if comment_form.validate_on_submit():
        new_comment = Comment(text=comment_form.comment.data or '', author_id=current_user.id, post_id=post_id)
        db.session.add(new_comment)
        db.session.commit()
    return redirect(url_for("show_post", post_id=post_id))

@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if request.method == "POST" and form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data or '',
            subtitle=form.subtitle.data or '',
            body=form.body.data or '',
            img_url=form.img_url.data or '',
            author_id=current_user.id,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)

@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data or ''
        post.subtitle = edit_form.subtitle.data or ''
        post.img_url = edit_form.img_url.data or ''
        post.author_id = current_user.id
        post.body = edit_form.body.data or ''
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))
    return render_template("make-post.html", form=edit_form, is_edit=True)

@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = db.get_or_404(BlogPost, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


if __name__ == "__main__":
    app.run(debug=False)

from __future__ import annotations
from functools import wraps
from typing import Optional

from cs50 import SQL
from flask import Flask, render_template, flash, request, redirect, session, jsonify
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
import random

MOVIES_DISPLAYED = 5

class MovieTree:
    """A subtree for a Movie Tree.

    Each node in the tree stores the type of node it is and its name
    The type of node is either a filter or a movie.
    The name of the node represents what is being filtered or the name of the movie

    Instance Attributes:
     - kind: the type of this node, either a filter or a movie
     - name: the title of the filter or movie
     - score:

    Representation Invariants:
        - self.kind in {'filter','movie'}
        - 0.0 <= self.score <= 1.0
    """
    kind: str
    name: str
    score: Optional

    # Private Instance Attributes:
    #   - _subtrees:
    #       the subtrees of this tree which represent another filter or movie recommendations
    _subtrees: list[MovieTree]

    def __init__(self, kind: str, name: str, score: float = 0.0) -> None:
        """Initialize a new game tree.

        Note that this initializer uses optional arguments, as illustrated below."""
        self.kind = kind
        self.name = name
        self.score = score
        self._subtrees = []

    def get_subtrees(self) -> list[MovieTree]:
        """Return the subtrees of this game tree."""
        return self._subtrees

    def add_subtree(self, subtree: MovieTree) -> None:
        """Add a subtree to this game tree."""

        self._subtrees.append(subtree)

    def find_subtree_by_name(self, name: str) -> Optional[MovieTree]:
        """Return the subtree corresponding to the given move.

        Return None if no subtree corresponds to that move.
        """
        for subtree in self._subtrees:
            if subtree.name == name:
                return subtree

        return None

    def remove_subtrees(self, target: str) -> None:
        """Remove all nodes and their subtrees in the tree that have a name that is the same as the
        target. This checks all nodes of the tree.

        This means that if a parent subtree is removed, the children of that subtree are also
        removed"""
        for subtree in self._subtrees:
            if subtree.name == target:
                self._subtrees.remove(subtree)
            else:
                subtree.remove_subtrees(target)

    def _subtree_calculator(self) -> list:
        """Collects all of the subtrees inside the movie tree into a list."""
        list_so_far = []
        if self is None:
            return []
        else:
            for subtree in self._subtrees:
                list_so_far = [self] + list_so_far + subtree._subtree_calculator()
        return list_so_far


    def new_score(self) -> None:
        """This function updates all the scores of this tree."""
        if self._subtrees == []:  # Checks if it's a leaf
            return
        else:
            subtrees = self._subtree_calculator()
            self.score = sum([subtree.score for subtree in subtrees]) / len(subtrees)
            return

    def refresh_score(self) -> None:
        if self.kind == "filter":
            for subtree in self._subtrees:
                subtree.refresh_score()
            self.new_score()
        else:
            return

    def scores(self) -> None:
        if self._subtrees == []:
            return
        else:
            print(self.score)
            for subtree in self._subtrees:
                subtree.scores()


    def find_best_movies(self, curr_list: list, total_movies: int, existing_list: list, depth: int = 0) -> list:
        """This function finds the highest scoring subtrees and returns a list of movies equal to
        the length of total_movies

        This will only ever recurse into the highest scoring subtree

        This function creates a sorted list of subtrees based on score from highest to lowest.

        Then it iterates through them to find the movies until a list of length total_movies
        is generated"""
        if depth == 7:
            return [movie.name for movie in self._subtrees]
        else:
            sorted_subtrees = []
            movies_so_far = curr_list

            final_list = []
            for item in self._subtrees:
                added = False
                if sorted_subtrees == []:
                    sorted_subtrees.append(item)
                for i in range(0, len(sorted_subtrees)):
                    if item.score > sorted_subtrees[i].score:
                        sorted_subtrees.insert(i, item)
                        added = True

                if not added:
                    sorted_subtrees.append(item)

            for subtree in sorted_subtrees:
                movies_so_far += subtree.find_best_movies(movies_so_far, total_movies, [], depth + 1)

                for x in movies_so_far:
                    if x not in final_list and x not in existing_list:
                        final_list.append(x)

                if len(final_list) >= total_movies:
                    break
            return final_list

    def movie_filter(self, age: int, artistic: str, foreign: str, runtime: str) -> None:
        """Prunes movie tree based on user inputs
        """
        if age < 18:
            self.remove_subtrees('18+')
        if age < 13:
            self.remove_subtrees('13+')

        if runtime == 'shorter':
            self.remove_subtrees('longer')
        elif runtime == 'longer':
            self.remove_subtrees('shorter')

        if artistic == "No":
            self.remove_subtrees('artistic: Yes')
        elif artistic == "Yes":
            self.remove_subtrees('artistic: No')

        if foreign == "No":
            self.remove_subtrees('foreign: Yes')

    def movie_scores(self, genre1: str, genre2: str, genre3: str):
        """Determines similarity for each value."""
        if self._subtrees != []:
            if self.name == genre1 or self.name == genre2 or self.name == genre3:
                self.score = self.score + 1.0
            for subtree in self._subtrees:
                subtree.movie_scores(genre1, genre2, genre3)


def generate_movie_tree(movie_database: list) -> MovieTree:
    """Creates movie tree."""
    movie_tree = MovieTree('filter', 'root')
    for row in movie_database:
        add_subtree(movie_tree, 0, row)
    return movie_tree


def add_subtree(curr_tree: MovieTree, depth: int, row: dict) -> None:
    """ Adds a subtree based on depth

    If the subtree is not at depth 7, then the function adds a filter, otherwise a movie is added"""
    if depth == 0:
        if row["rating"] not in [subtree.name for subtree in curr_tree.get_subtrees()]:
            new_tree = MovieTree("filter", row["rating"])
            curr_tree.add_subtree(new_tree)
        new_subtree = curr_tree.find_subtree_by_name(row["rating"])
        add_subtree(new_subtree, 1, row)

    elif depth == 1:
        if row["runtime"] == "":
            duration = "unlisted"

        elif int(row["runtime"]) <= 120:
            duration = "shorter"
        else:
            duration = "longer"
        if duration not in [subtree.name for subtree in curr_tree.get_subtrees()]:
            new_tree = MovieTree("filter", duration)
            curr_tree.add_subtree(new_tree)

        new_subtree = curr_tree.find_subtree_by_name(duration)
        add_subtree(new_subtree, 2, row)

    elif depth == 2:
        if row["genre1"] not in [subtree.name for subtree in curr_tree.get_subtrees()]:
            new_tree = MovieTree("filter", row["genre1"])
            curr_tree.add_subtree(new_tree)
        new_subtree = curr_tree.find_subtree_by_name(row['genre1'])
        add_subtree(new_subtree, 3, row)

    elif depth == 3:
        if row['genre2'] not in [subtree.name for subtree in curr_tree.get_subtrees()]:
            new_tree = MovieTree('filter', row['genre2'])
            curr_tree.add_subtree(new_tree)
        new_subtree = curr_tree.find_subtree_by_name(row['genre2'])
        add_subtree(new_subtree, 4, row)

    elif depth == 4:
        if row['genre3'] not in [subtree.name for subtree in curr_tree.get_subtrees()]:
            new_tree = MovieTree('filter', row['genre3'])
            curr_tree.add_subtree(new_tree)
        new_subtree = curr_tree.find_subtree_by_name(row['genre3'])
        add_subtree(new_subtree, 5, row)

    elif depth == 5:
        artistic = 'artistic: ' + row['artistic']
        if row['artistic'] not in [subtree.name for subtree in curr_tree.get_subtrees()]:
            new_tree = MovieTree('filter', artistic)
            curr_tree.add_subtree(new_tree)

        new_subtree = curr_tree.find_subtree_by_name(artistic)
        add_subtree(new_subtree, 6, row)

    elif depth == 6:
        foreign = 'foreign: ' + row['foreign']
        if row['foreign'] not in [subtree.name for subtree in curr_tree.get_subtrees()]:
            new_tree = MovieTree('filter', foreign)
            curr_tree.add_subtree(new_tree)
        new_subtree = curr_tree.find_subtree_by_name(foreign)
        add_subtree(new_subtree, 7, row)

    else:
        if row['title'] not in [subtree.name for subtree in curr_tree.get_subtrees()]:
            new_tree = MovieTree('movie', row['title'])
            curr_tree.add_subtree(new_tree)

def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

app = Flask(__name__)

app.config["TEMPLATES_AUTO_RELOAD"] = True

db = SQL("sqlite:///recommendations.db")

# Guarantees responses are not being cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Operate session using filesystems instead of signed cookies
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

@app.route("/", methods =["GET", "POST"])
@login_required
def index():
    # POST route from form submission
    if request.method == "POST":
        user = db.execute("SELECT id, username FROM users WHERE id == ?", session["user_id"])
        username = user[0]["username"]
        user_id = user[0]["id"]

        recommendations = session["recommendations"]
        for recommendation in recommendations:
            recommendation_id = db.execute("SELECT id FROM movies WHERE title = ? AND director = ? AND year = ?", recommendation["title"], recommendation["director"], recommendation["year"])[0]["id"]
            db.execute("INSERT INTO recommended_movies (movie_id, user_id) VALUES (?, ?)", recommendation_id, user_id)

        user_movies = db.execute("SELECT title, director, year FROM movies JOIN recommended_movies ON movies.id = recommended_movies.movie_id WHERE recommended_movies.user_id = ? ORDER BY title", user_id)
        return render_template("index.html", username=username, user_movies=user_movies)
    # GET route from form submission
    else:
        session["recommendations"] = []
        user = db.execute("SELECT id, username FROM users WHERE id == ?", session["user_id"])
        username = user[0]["username"]
        user_id = user[0]["id"]

        user_movies = db.execute("SELECT title, director, year FROM movies JOIN recommended_movies ON movies.id = recommended_movies.movie_id WHERE recommended_movies.user_id = ? ORDER BY title", user_id)
        return render_template("index.html", username=username, user_movies=user_movies)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Clears current session
    session.clear()

    session["recommendations"] = []
    # POST route from form submission
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return render_template("error.html", message="ERROR: Username missing.")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return render_template("error.html", message="ERROR: Password missing.")

        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return render_template("error.html", message="ERROR: Username or password is invalid.")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # GET route from being clicked
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    session["recommendations"] = []
    # Clears out user_id
    session.clear()

    # Sends user back to the login page
    return redirect("/login")

@app.route("/movies", methods =["GET", "POST"])
@login_required
def movies():

    # POST route from form submission
    if request.method == "POST":
        if not request.form.get("age"):
            return render_template("error.html", message="ERROR: Remember to input your age.")
        age = int(request.form.get("age"))

        artistic = request.form.get("artistic")
        foreign = request.form.get("foreign")
        runtime = request.form.get("runtime")

        if not artistic or not foreign or not runtime:
            return render_template("error.html", message="ERROR: Please fill in every option.")

        if not request.form.get("genre1") or not request.form.get("genre2") or not request.form.get("genre3"):
            return render_template("error.html", message="ERROR: Please select three genres.")
        genre1 = (request.form.get("genre1"))
        genre2 = (request.form.get("genre2"))
        genre3 = (request.form.get("genre3"))

        movie_database = db.execute("SELECT * from movies")
        movie_tree = generate_movie_tree(movie_database)
        movie_tree.remove_subtrees('')
        movie_tree.movie_filter(age, artistic, foreign, runtime)
        movie_tree.movie_scores(genre1, genre2, genre3)
        movie_tree.refresh_score()

        user = db.execute("SELECT id, username FROM users WHERE id == ?", session["user_id"])
        user_id = user[0]["id"]

        existing_movie_database = db.execute("SELECT title FROM movies JOIN recommended_movies ON movies.id = recommended_movies.movie_id WHERE recommended_movies.user_id = ? ORDER BY title", user_id)
        existing_list = []
        for movie in existing_movie_database:
            existing_list.append(movie["title"])

        recommendations = movie_tree.find_best_movies([], 10, existing_list)

        if recommendations == []:
            return render_template("apology.html")

        else:
            random.shuffle(recommendations)
            recommendations = sorted(recommendations[:MOVIES_DISPLAYED])

            recommendation_list = []
            for recommendation in recommendations:
                recommendation_list = recommendation_list + db.execute("SELECT title, director, year FROM movies WHERE title = ?", recommendation)

            session["recommendations"] = session["recommendations"] + recommendation_list

            return render_template("recommendations.html", recommendation_list=recommendation_list)

    # GET route from being clicked
    else:
        session["recommendations"] = []
        return render_template("movies.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    session["recommendations"] = []
    # POST route from form submission
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return render_template("error.html", message="ERROR: Username missing.")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return render_template("error.html", message="ERROR: Password missing.")

        # Ensure password confirmation was submitted
        elif not request.form.get("confirmation"):
            return render_template("error.html", message="ERROR: Password not confirmed.")

        # Ensure passwords match
        elif request.form.get("confirmation") != request.form.get("password"):
            return render_template("error.html", message="ERROR: Passwords don't match.")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        if len(rows) != 0:
            return render_template("error.html", message="ERROR: Username already exists; select another.")

        username = request.form.get("username")
        hashed_password = generate_password_hash(request.form.get("password"), method='pbkdf2:sha256', salt_length=8)

        db.execute("INSERT into users (username, hash) VALUES (?, ?)", username, hashed_password)

        return redirect("/login")

    # GET route from being clicked
    else:
        return render_template("register.html")

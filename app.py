#!/usr/bin/env python3

import os
import sys
import subprocess
import datetime
import re

from flask import Flask, render_template, request, redirect, url_for, make_response

# import logging
import sentry_sdk
from sentry_sdk.integrations.flask import (
    FlaskIntegration,
)  # delete this if not using sentry.io

# from markupsafe import escape
import pymongo
from pymongo.errors import ConnectionFailure
from bson.objectid import ObjectId
#from dotenv import load_dotenv

# load credentials and configuration options from .env file
# if you do not yet have a file named .env, make one based on the template in env.example
#load_dotenv(override=True)  # take environment variables from .env.

# initialize Sentry for help debugging... this requires an account on sentrio.io
# you will need to set the SENTRY_DSN environment variable to the value provided by Sentry
# delete this if not using sentry.io
#sentry_sdk.init(
     #dsn=os.getenv("SENTRY_DSN"),
    # enable_tracing=True,
    # Set traces_sample_rate to 1.0 to capture 100% of transactions for performance monitoring.
     #traces_sample_rate=1.0,
    # Set profiles_sample_rate to 1.0 to profile 100% of sampled transactions.
    # We recommend adjusting this value in production.
    
     #integrations=[FlaskIntegration()],
     #send_default_pii=True,
#)

# instantiate the app using sentry for debugging
app = Flask(__name__)
# # turn on debugging if in development mode
# app.debug = True if os.getenv("FLASK_ENV", "development") == "development" else False

# try to connect to the database, and quit if it doesn't work
try:
    cxn=pymongo.MongoClient('class-mongodb.cims.nyu.edu', 27017, 
                                username='rs8050',
                                password='XiVBZLDs',
                                authSource='rs8050')
    #cxn = pymongo.MongoClient(os.getenv("MONGO_URI"))
    db = cxn['rs8050']  # store a reference to the selected database

    # verify the connection works by pinging the database
    #cxn.admin.command("ping")  # The ping command is cheap and does not require auth.
    print(" * Connected to MongoDB!")  # if we get here, the connection worked!
except ConnectionFailure as e:
    # catch any database errors
    # the ping command failed, so the connection is not available.
    print(" * MongoDB connection error:", e)  # debug
     #sentry_sdk.capture_exception(e)  # send the error to sentry.io. delete if not using
    sys.exit(1)  # this is a catastrophic error, so no reason to continue to live


# set up the routes


@app.route("/")
def home():
    """
    Route for the home page.
    Simply returns to the browser the content of the index.html file located in the templates folder.
    """
    return render_template("index.html")


@app.route("/read")
def read():
    """
    Route for GET requests to the read page.
    Displays some information for the user with links to other pages.
    """
    docs = db.exampleapp.find({}).sort(
        "created_at", -1
    )  # sort in descending order of created_at timestamp
    return render_template("read.html", docs=docs)  # render the read template

@app.route("/search")
def search():
    """
    Route for GET requests to the create page.
    Displays a form users can fill out to create a new document.
    """
    return render_template("search.html")  # render the search template

@app.route("/search", methods=["POST"])
def search_post():
    """
    Route for POST requests to search for products by type.
    Accepts the form submission data for a product type and retrieves all products with the same type from the database.
    """
    product_type = request.form["product_type"]

    # Convert product_type to case-insensitive regular expression pattern
    regex_pattern = re.compile(f"^{re.escape(product_type)}$", re.IGNORECASE)

    # Query database for products with the same type (case-insensitive)
    docs = db.exampleapp.find({"type": {"$regex": regex_pattern}})
    return render_template("search_read.html", docs=docs, product_type=product_type)

@app.route("/create")
def create():
    """
    Route for GET requests to the create page.
    Displays a form users can fill out to create a new document.
    """
    return render_template("create.html")  # render the create template


@app.route("/create", methods=["POST"])
def create_post():
    """
    Route for POST requests to the create page.
    Accepts the form submission data for a new document and saves the document to the database.
    """
    product_type = request.form["product_type"]
    description = request.form["product_description"]
    price = request.form["product_price"]
    id = request.form["user_id"]
    email = request.form['user_email']

    # Create a new document with the data the user entered
    doc = {
        "type": product_type,
        "description": description,
        "price": price,
        "id": id,
        "email": email,
        "created_at": datetime.datetime.utcnow(),
    }
    db.exampleapp.insert_one(doc)  # insert a new document

    return redirect(
        url_for("read")
    )  # tell the browser to make a request for the /read route


@app.route("/edit/<mongoid>")
def edit(mongoid):
    """
    Route for GET requests to the edit page.
    Displays a form users can fill out to edit an existing record.

    Parameters:
    mongoid (str): The MongoDB ObjectId of the record to be edited.
    """
    doc = db.exampleapp.find_one({"_id": ObjectId(mongoid)})
    return render_template(
        "edit.html", mongoid=mongoid, doc=doc
    )  # render the edit template


@app.route("/edit/<mongoid>", methods=["POST"])
def edit_post(mongoid):
    """
    Route for POST requests to the edit page.
    Accepts the form submission data for the specified document and updates the document in the database.

    Parameters:
    mongoid (str): The MongoDB ObjectId of the record to be edited.
    """
    product_type = request.form["product_type"]
    description = request.form["product_description"]
    price = request.form["product_price"]
    id = request.form["user_id"]
    email = request.form['user_email']

    doc = {
        "type": product_type,
        "description": description,
        "price": price,
        "id": id,
        "email": email,
        "created_at": datetime.datetime.utcnow(),
    }

    db.exampleapp.update_one(
        {"_id": ObjectId(mongoid)}, {"$set": doc}  # match criteria
    )

    return redirect(
        url_for("read")
    ) 


@app.route("/delete/<mongoid>")
def delete(mongoid):
    """
    Route for GET requests to the delete page.
    Deletes the specified record from the database, and then redirects the browser to the read page.

    Parameters:
    mongoid (str): The MongoDB ObjectId of the record to be deleted.
    """
    db.exampleapp.delete_one({"_id": ObjectId(mongoid)})
    return redirect(
        url_for("read")
    )  # tell the web browser to make a request for the /read route.

# Flask app




@app.route("/webhook", methods=["POST"])
def webhook():
    """
    GitHub can be configured such that each time a push is made to a repository, GitHub will make a request to a particular web URL... this is called a webhook.
    This function is set up such that if the /webhook route is requested, Python will execute a git pull command from the command line to update this app's codebase.
    You will need to configure your own repository to have a webhook that requests this route in GitHub's settings.
    Note that this webhook does do any verification that the request is coming from GitHub... this should be added in a production environment.
    """
    # run a git pull command
    process = subprocess.Popen(["git", "pull"], stdout=subprocess.PIPE)
    pull_output = process.communicate()[0]
    # pull_output = str(pull_output).strip() # remove whitespace
    process = subprocess.Popen(["chmod", "a+x", "flask.cgi"], stdout=subprocess.PIPE)
    chmod_output = process.communicate()[0]
    # send a success response
    response = make_response(f"output: {pull_output}", 200)
    response.mimetype = "text/plain"
    return response


@app.errorhandler(Exception)
def handle_error(e):
    """
    Output any errors - good for debugging.
    """
    return render_template("error.html", error=e)  # render the edit template


# run the app
if __name__ == "__main__":
    # logging.basicConfig(filename="./flask_error.log", level=logging.DEBUG)
    app.run()

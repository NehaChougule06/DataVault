from flask import Flask, render_template, request, redirect, send_file

import pyrebase
import json
import subprocess
from werkzeug.utils import secure_filename
import os
import requests
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import bcrypt
from flask_cors import CORS, cross_origin
import time
from flask_session import Session

app = Flask(__name__)
# ALlow cross origin requests
app.config["CORS_HEADERS"] = "Content-Type"
cors = CORS(app, resources={r"/upload": {"origins": "http://localhost:3000"}})
SESSION_TYPE = "filesystem"
app.config.from_object(__name__)
Session(app)
CORS(app)


def verify_hash(hash, passwd):
    ohash = hash
    salt = hash.split("$$")[0].encode()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=390000,
    )
    key = base64.urlsafe_b64encode(
        kdf.derive(passwd.encode() + app.secret_key.encode("utf-8"))
    )
    hash = salt + "$$".encode() + bcrypt.hashpw(key, salt)
    print(hash, ohash)
    if hash == ohash.encode():
        return True, key
    else:
        return False, 0


def encrypting(password, pepper):
    print("Encrypting")
    bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    print(salt)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=390000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(bytes + pepper.encode("utf-8")))
    hash = salt + "$$".encode() + bcrypt.hashpw(key, salt)
    return key, hash


def encrypt_file(filedata, key, filename):

    fernet = Fernet(key)
    encrypted = fernet.encrypt(filedata)
    a = open(app.config["uploadFolder"] + filename, "wb")
    a.write(encrypted)
    a.flush()
    a.close()


def decrypt_file(filename, key):
    fernet = Fernet(key)
    encrypted = open(
        app.config["uploadFolder"] + "encrypted_" + filename + "/" + filename, "rb"
    ).read()
    decrypted = fernet.decrypt(encrypted)
    a = open(app.config["uploadFolder"] + "decrypted" + filename, "wb")
    a.write(decrypted)
    a.flush()
    a.close()


def upload_file(file, hash, session):
    users = db.get().val()

    opp = subprocess.run(
        f"w3 put {file}", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
    )
    filename = file.split("/")[-1].replace(".", ",")
    filecid = opp.stdout.decode().split()[1]
    print(filename, filecid)
    data = {"data": [hash.decode(), filecid]}
    db.child(session["UserID"]).child(filename).set(data)


def getCookies(cookiestring):
    cookie = {}
    a = cookiestring[:-1].split(";")
    for i in a:
        cookie[i.split("=")[0]] = i.split("=")[-1]

    return cookie


app.secret_key = "cre=ebrorU#Ipr&b#gibapreyAqlmLwufof+7ipo4uJa@rozi2"
app.config["uploadFolder"] = "uploads/"

config = {
    "apiKey": "AIzaSyBTIZ1Kh57qF6L-2T5LAh9Vvo92oiweN-k",
    "authDomain": "datavault-6e0a9.firebaseapp.com",
    "projectId": "datavault-6e0a9",
    "storageBucket": "datavault-6e0a9.appspot.com",
    "messagingSenderId": "4788139923",
    "appId": "1:4788139923:web:702b2c92dca85b43651a66",
    "databaseURL": "https://datavault-6e0a9-default-rtdb.firebaseio.com/",
}

firebase = pyrebase.initialize_app(config)
auth = firebase.auth()
db = firebase.database()

# @app.route("/")
# def home_page():

#     if "UserName" in session:
#         return render_template("upload.html")
#     else:
#         return render_template("login.html")


@app.route("/files", methods=["POST"])
@cross_origin(origin="localhost", headers=["Content- Type", "Authorization"])
def getFiles():
    if request.method == "POST":
        session = getCookies(request.headers["Authorization"])
        print("INSIDE FILES\n", session)
        if "UserID" in session:

            d = db.child(session["UserID"]).get().val()
            lis = {}
            lis["files"] = []
            for i in d:
                lis["files"].append(i.replace(",", "."))

            print("LIS IS\n", lis)

            return {"status": 200, "data": lis}
        else:
            return {"status": 400}


@app.route("/register", methods=["POST"])
@cross_origin(origin="localhost", headers=["Content- Type", "Authorization"])
def registerUser():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        passwd = request.form.get("password")
        cpasswd = request.form.get("cpassword")

        request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/signupNewUser?key={0}".format(
            config["apiKey"]
        )
        headers = {"content-type": "application/json; charset=UTF-8"}
        data = json.dumps(
            {
                "email": email,
                "password": passwd,
                "returnSecureToken": True,
                "displayName": username,
            }
        )

        request_object = requests.post(request_ref, headers=headers, data=data)
        out = request_object.json()
        auth.send_email_verification(out["idToken"])

        return {"status": 200}


@app.route("/logout")
@cross_origin(origin="localhost", headers=["Content- Type", "Authorization"])
def logout():
    session = getCookies(request.header["Authorization"])
    if "UserID" in session:
        d = db.child(session["UserID"]).get().val()
        for i in d:
            i = i.replace(",", ".")
            if os.path.exists(os.path.join(app.config["uploadFolder"], i, i)):
                os.remove(os.path.join(app.config["uploadFolder"], i, i))

            if os.path.exists(os.path.join(app.config["uploadFolder"], i)):
                os.rmdir(os.path.join(app.config["uploadFolder"], i))
            if os.path.exists(
                os.path.join(app.config["uploadFolder"], "decrypted" + i)
            ):
                os.remove(os.path.join(app.config["uploadFolder"], "decrypted" + i))
        session.pop("UserID", None)
        session.pop("UserName", None)
        return {"status": 200}
    else:
        return {"status": 400}


@app.route("/verify", methods=["POST"])
@cross_origin(origin="localhost", headers=["Content- Type", "Authorization"])
def download():
    session["UserID"] = "test"
    if request.method == "POST":
        session = getCookies(request.header["Authorization"])
        if "UserID" in session:

            passwd = request.form.get("password")
            filename = request.form.get("filename").replace(".", ",")

            users = db.get().val()
            if session["UserID"] in users:

                cid = (
                    db.child(session["UserID"])
                    .child(filename)
                    .child("data")
                    .get()
                    .val()[-1]
                )
                shash = (
                    db.child(session["UserID"])
                    .child(filename)
                    .child("data")
                    .get()
                    .val()[0]
                )
                check, key = verify_hash(shash, passwd)
                if check:
                    file = filename.replace(",", ".")
                    session["allowed_files"].append(file)
                    os.system(
                        "w3 get {} -o {}".format(
                            cid, app.config["uploadFolder"] + "encrypted_" + file
                        )
                    )
                    decrypt_file(file, key)
                    file = "decrypted" + filename.replace(",", ".")
                    return {"status": 200}
                else:
                    return {"status": 400}
        else:
            return {"status": 400}


@app.route("/upload", methods=["GET", "POST"])
@cross_origin(origin="localhost", headers=["Content- Type", "Authorization"])
def uploadToServer():
    if request.method == "POST":
        session = getCookies(request.header["Authorization"])

        if "UserID" in session:

            print("uploading")
            files = request.files.get("file")
            # print("Time taken to get files: ", new_time - Time) Most Time
            secretKey = request.form.get("key")
            filename = secure_filename(files.filename)
            filedata = files.read()
            key, hash = encrypting(secretKey, app.secret_key)
            encrypt_file(filedata, key, filename)
            print("Encrypted")
            t1 = time.time()
            upload_file(
                os.path.join(app.config["uploadFolder"], filename), hash, session
            )
            t2 = time.time()
            print("Time taken to upload: ", t2 - t1)
            return {"status": "success"}
        else:
            return {"status": 400}


@app.route("/download/<file>", methods=["POST", "GET"])
@cross_origin(origin="localhost", headers=["Content- Type", "Authorization"])
def send_download(file):
    if request.method == "GET":
        session = getCookies(request.header["Authorization"])
        if "UserID" in session:
            if file in session["allowed_files"]:

                print("Sending: " + app.config["uploadFolder"] + "decrypted" + file)
                return send_file(
                    app.config["uploadFolder"] + "decrypted" + file,
                    as_attachment=True,
                    attachment_filename=file,
                )
            else:
                return {"status": 400}
        else:
            return {"status": 400}


@app.route("/login", methods=["POST"])
@cross_origin(
    origin="localhost",
    headers=["Content- Type", "Authorization"],
    supports_credentials=True,
)
def login():
    email = request.form.get("email")
    password = request.form.get("password")
    try:
        user = auth.sign_in_with_email_and_password(email, password)
    except:
        return {"status": 400}
    UserInfo = auth.get_account_info(user["idToken"])
    Verified = UserInfo["users"][0]["emailVerified"]
    if Verified:

        return {
            "status": 200,
            "UserName": user["displayName"],
            "UserID": UserInfo["users"][0]["localId"],
            "verified": UserInfo["users"][0]["emailVerified"],
        }
    else:
        return {"status": 400}


if __name__ == "__main__":
    app.run(debug=True)

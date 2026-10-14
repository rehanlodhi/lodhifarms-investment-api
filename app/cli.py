"""User management: `uv run python -m app.cli --help`."""
import argparse
import getpass
import sys

from pymongo import MongoClient

from .config import settings
from .security import password_hash

users = MongoClient(settings.mongo_url)[settings.mongo_db].users


def read_password(given: str | None) -> str:
    if given:
        return given
    pw = getpass.getpass("Password: ")
    if pw != getpass.getpass("Confirm password: "):
        sys.exit("Passwords do not match")
    if len(pw) < 8:
        sys.exit("Password must be at least 8 characters")
    return pw


def find(login: str) -> dict | None:
    login = login.strip().lower()
    return users.find_one({"$or": [{"username": login}, {"email": login}]})


def create_user(args):
    username = args.username.strip().lower()
    email = args.email.strip().lower() if args.email else None
    if find(username) or (email and find(email)):
        sys.exit("A user with that username or email already exists")
    doc = {"username": username, "password": password_hash.hash(read_password(args.password))}
    if email:
        doc["email"] = email
    users.insert_one(doc)
    print(f"Created {username}")


def set_password(args):
    user = find(args.login)
    if not user:
        sys.exit(f"No such user: {args.login}")
    users.update_one({"_id": user["_id"]}, {"$set": {"password": password_hash.hash(read_password(args.password))}})
    print("Password updated")


def delete_user(args):
    user = find(args.login)
    if not user:
        sys.exit(f"No such user: {args.login}")
    if users.count_documents({}) <= 1:
        sys.exit("Refusing to delete the last user")
    users.delete_one({"_id": user["_id"]})
    print("Deleted")


def list_users(_):
    for u in users.find().sort("username", 1):
        print(f"{u.get('username') or '-':20} {u.get('email') or ''}")


def main():
    parser = argparse.ArgumentParser(prog="app.cli", description="Manage login users")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("create-user", help="Create a user (prompts for the password)")
    p.add_argument("username")
    p.add_argument("--email", help="Optional; can also be used to log in")
    p.add_argument("--password", help="Avoid: visible in shell history. Omit to be prompted.")
    p.set_defaults(fn=create_user)

    p = sub.add_parser("set-password", help="Change a user's password")
    p.add_argument("login", help="Username or email")
    p.add_argument("--password")
    p.set_defaults(fn=set_password)

    p = sub.add_parser("delete-user", help="Delete a user")
    p.add_argument("login", help="Username or email")
    p.set_defaults(fn=delete_user)

    sub.add_parser("list-users", help="List users").set_defaults(fn=list_users)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()

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


def create_user(args):
    email = args.email.strip().lower()
    if users.find_one({"email": email}):
        sys.exit(f"User {email} already exists")
    users.insert_one({"email": email, "password": password_hash.hash(read_password(args.password))})
    print(f"Created {email}")


def set_password(args):
    email = args.email.strip().lower()
    res = users.update_one({"email": email}, {"$set": {"password": password_hash.hash(read_password(args.password))}})
    print(f"Updated {email}" if res.matched_count else f"No such user: {email}")


def delete_user(args):
    email = args.email.strip().lower()
    if users.count_documents({}) <= 1:
        sys.exit("Refusing to delete the last user")
    res = users.delete_one({"email": email})
    print(f"Deleted {email}" if res.deleted_count else f"No such user: {email}")


def list_users(_):
    for u in users.find().sort("email", 1):
        print(u["email"])


def main():
    parser = argparse.ArgumentParser(prog="app.cli", description="Manage login users")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name, fn, help_ in [
        ("create-user", create_user, "Create a user (prompts for the password)"),
        ("set-password", set_password, "Change a user's password"),
        ("delete-user", delete_user, "Delete a user"),
    ]:
        p = sub.add_parser(name, help=help_)
        p.add_argument("email")
        if name != "delete-user":
            p.add_argument("--password", help="Avoid: visible in shell history. Omit to be prompted.")
        p.set_defaults(fn=fn)
    sub.add_parser("list-users", help="List users").set_defaults(fn=list_users)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()

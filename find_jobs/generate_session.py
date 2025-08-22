from pyrogram import Client

# Optional TgCrypto check (Pyrogram uses it automatically if installed)
try:
    import tgcrypto  # noqa: F401
    print("TgCrypto detected: using accelerated MTProto.")
except Exception:
    print("TgCrypto not detected: using pure-Python MTProto.")

api_id = int(input("Enter your API ID: "))
api_hash = input("Enter your API HASH: ")

with Client("my_account", api_id=api_id, api_hash=api_hash) as app:
    print("Session string:")
    print(app.export_session_string())
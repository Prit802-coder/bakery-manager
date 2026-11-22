import os
import socket
import uvicorn
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

from backend.seed import seed_database
from backend.database import Base, engine

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def main():
    print("=" * 60)
    print("  MOM'S HOMEMADE CAKE BUSINESS MANAGER")
    print("  Private, Phone-Friendly Bakery Management System")
    print("=" * 60)

    # Initialize tables and seed default user and bakery data
    Base.metadata.create_all(bind=engine)
    seed_database()

    local_ip = get_local_ip()
    port = 8000
    owner_username = os.getenv("OWNER_USERNAME", "mom")

    print("\n[OK] Application is ready!")
    print(f" -> Access on this computer: http://localhost:{port}")
    print(f" -> Access on Mom's Phone (same Wi-Fi): http://{local_ip}:{port}")
    print("\nOwner Authentication:")
    print(f"   Username: {owner_username}")
    print("   Password: [Configured in your private .env file (OWNER_PASSWORD)]")
    print("=" * 60)
    print("Press CTRL+C to stop the server.\n")

    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=False)

if __name__ == "__main__":
    main()

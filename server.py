import socket
import threading
import logging
import os
import datetime
import sqlite3
import json
from hashlib import sha256
import jwt

# Khởi tạo cơ sở dữ liệu
def initialize_database():
    conn = sqlite3.connect('db.sqlite3')
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE,
                        password TEXT,
                        token TEXT
                    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS chats (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        message TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(user_id) REFERENCES users(id)
                    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS projects (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        owner INTEGER,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(owner) REFERENCES users(id)
                    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS project_members (
                        project_id INTEGER,
                        user_id INTEGER,
                        FOREIGN KEY(project_id) REFERENCES projects(id),
                        FOREIGN KEY(user_id) REFERENCES users(id)
                    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS tasks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        project_id INTEGER,
                        name TEXT,
                        FOREIGN KEY(project_id) REFERENCES projects(id)
                    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS task_assignments (
                        task_id INTEGER,
                        user_id INTEGER,
                        FOREIGN KEY(task_id) REFERENCES tasks(id),
                        FOREIGN KEY(user_id) REFERENCES users(id)
                    )''')
    conn.commit()
    conn.close()

# Thiết lập logging
def setup_logging():
    today = datetime.datetime.now().strftime("%d_%m_%Y")
    log_dir = f'logs/{today}'
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'server.log')
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler()
    ])

# Các hàm xử lý
SECRET_KEY = 'your_secret_key'
conn = sqlite3.connect('db.sqlite3', check_same_thread=False)
cur = conn.cursor()

def register(username, password):
    hashed_password = sha256(password.encode()).hexdigest()
    try:
        cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
        conn.commit()
        logging.info(f"User registered: {username}")
        return {"status": "success", "message": "User registered successfully"}
    except sqlite3.IntegrityError:
        return {"status": "error", "message": "Username already exists"}

def login(username, password):
    hashed_password = sha256(password.encode()).hexdigest()
    cur.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, hashed_password))
    user = cur.fetchone()
    if user:
        token = jwt.encode({"username": username}, SECRET_KEY, algorithm="HS256")
        cur.execute("UPDATE users SET token = ? WHERE id = ?", (token, user[0]))
        conn.commit()
        logging.info(f"User logged in: {username}")
        return {"status": "success", "token": token}
    else:
        return {"status": "error", "message": "Invalid credentials"}

def chat(token, message):
    decoded_token = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    username = decoded_token['username']
    cur.execute("SELECT id FROM users WHERE username = ?", (username,))
    user = cur.fetchone()
    if user:
        cur.execute("INSERT INTO chats (user_id, message) VALUES (?, ?)", (user[0], message))
        conn.commit()
        logging.info(f"Message from {username}: {message}")
        return {"status": "success", "message": "Message sent"}
    return {"status": "error", "message": "Authentication failed"}

def get_all_chats():
    cur.execute("SELECT u.username, c.message, c.timestamp FROM chats c JOIN users u ON c.user_id = u.id ORDER BY c.timestamp")
    chats = cur.fetchall()
    return [{"username": chat[0], "message": chat[1], "timestamp": chat[2]} for chat in chats]

def create_project(token, project_name, members):
    decoded_token = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    username = decoded_token['username']
    cur.execute("SELECT id FROM users WHERE username = ?", (username,))
    owner = cur.fetchone()
    if owner:
        cur.execute("INSERT INTO projects (name, owner) VALUES (?, ?)", (project_name, owner[0]))
        project_id = cur.lastrowid
        for member in members:
            cur.execute("SELECT id FROM users WHERE username = ?", (member,))
            user = cur.fetchone()
            if user:
                cur.execute("INSERT INTO project_members (project_id, user_id) VALUES (?, ?)", (project_id, user[0]))
        conn.commit()
        logging.info(f"Project created: {project_name} by {username} with members {members}")
        return {"status": "success", "message": "Project created successfully"}
    return {"status": "error", "message": "Invalid token"}

def add_task(token, project_id, task_name, members):
    decoded_token = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    username = decoded_token['username']
    cur.execute("SELECT id FROM users WHERE username = ?", (username,))
    user = cur.fetchone()
    if user:
        cur.execute("SELECT owner FROM projects WHERE id = ?", (project_id,))
        project_owner = cur.fetchone()
        if project_owner and project_owner[0] == user[0]:
            cur.execute("INSERT INTO tasks (project_id, name) VALUES (?, ?)", (project_id, task_name))
            task_id = cur.lastrowid
            for member in members:
                cur.execute("SELECT id FROM users WHERE username = ?", (member,))
                assigned_user = cur.fetchone()
                if assigned_user:
                    cur.execute("INSERT INTO task_assignments (task_id, user_id) VALUES (?, ?)", (task_id, assigned_user[0]))
            conn.commit()
            logging.info(f"Task '{task_name}' added to project {project_id} by {username}")
            return {"status": "success", "message": "Task added successfully"}
    return {"status": "error", "message": "Only project owner can add tasks"}

def get_projects():
    cur.execute("SELECT p.id, p.name, u.username FROM projects p JOIN users u ON p.owner = u.id")
    projects = cur.fetchall()
    result = []
    for proj in projects:
        cur.execute("SELECT u.username FROM project_members pm JOIN users u ON pm.user_id = u.id WHERE pm.project_id = ?", (proj[0],))
        members = [member[0] for member in cur.fetchall()]
        result.append({"id": proj[0], "name": proj[1], "owner": proj[2], "members": members})
    return result

def get_tasks(project_id):
    cur.execute("SELECT id, name FROM tasks WHERE project_id = ?", (project_id,))
    tasks = cur.fetchall()
    result = []
    for task in tasks:
        cur.execute("SELECT u.username FROM task_assignments ta JOIN users u ON ta.user_id = u.id WHERE ta.task_id = ?", (task[0],))
        members = [member[0] for member in cur.fetchall()]
        result.append({"id": task[0], "name": task[1], "members": members})
    return result

def get_all_users():
    cur.execute("SELECT username FROM users")
    users = [user[0] for user in cur.fetchall()]
    return users

# Xử lý từng kết nối client
def handle_client(conn, addr):
    with conn:
        logging.info(f"Connected by {addr}")
        while True:
            try:
                data = conn.recv(1024).decode()
                if not data:
                    break
                request = json.loads(data)
                action = request.get("action")
                # Xử lý các hành động từ client
                if action == "register":
                    response = register(request["username"], request["password"])
                elif action == "login":
                    response = login(request["username"], request["password"])
                elif action == "chat":
                    response = chat(request["token"], request["message"])
                elif action == "get_all_chats":
                    response = get_all_chats()
                elif action == "create_project":
                    response = create_project(request["token"], request["project_name"], request["members"])
                elif action == "add_task":
                    response = add_task(request["token"], request["project_id"], request["task_name"], request["members"])
                elif action == "get_projects":
                    response = get_projects()
                elif action == "get_tasks":
                    response = get_tasks(request["project_id"])
                elif action == "get_all_users":
                    response = get_all_users()
                else:
                    response = {"status": "error", "message": "Invalid action"}
                conn.sendall(json.dumps(response).encode())
            except ConnectionResetError as e:
                logging.error(f"ConnectionResetError: {e} - Client {addr} disconnected.")
                break
            except json.JSONDecodeError as e:
                logging.error(f"JSONDecodeError: {e} - Invalid data from {addr}.")
            except Exception as e:
                logging.error(f"Error: {e}")


# Chạy server
def start_server():
    initialize_database()
    setup_logging()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('localhost', 5555))
    server.listen(100)
    logging.info("Server is running on port 5555...")
    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr)).start()

if __name__ == "__main__":
    start_server()

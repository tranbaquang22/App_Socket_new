import socket
import json

SERVER_IP = 'localhost'
SERVER_PORT = 5555

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((SERVER_IP, SERVER_PORT))

token = None

def send_request(request):
    try:
        client.sendall(json.dumps(request).encode())
        data = b""
        while True:
            part = client.recv(1024)
            data += part
            if len(part) < 1024:
                break
        response = json.loads(data.decode())
        return response
    except ConnectionResetError as e:
        print(f"Error: Connection to the server was lost. {e}")
        return {"status": "error", "message": "Connection to the server was lost."}
    except Exception as e:
        print(f"Unexpected error: {e}")
        return {"status": "error", "message": "Unexpected error occurred."}


def register():
    try:
        while True:
            username = input("Enter username: ").strip()
            if not username:
                print("Username cannot be empty. Please try again.")
                continue
            password = input("Enter password: ").strip()
            if not password:
                print("Password cannot be empty. Please try again.")
                continue
            break
        response = send_request({"action": "register", "username": username, "password": password})
        print(response["message"])
    except Exception as e:
        print(f"Error during registration: {e}")

def login():
    global token
    try:
        while True:
            username = input("Enter username: ").strip()
            if not username:
                print("Username cannot be empty. Please try again.")
                continue
            password = input("Enter password: ").strip()
            if not password:
                print("Password cannot be empty. Please try again.")
                continue
            break
        response = send_request({"action": "login", "username": username, "password": password})
        if response["status"] == "success":
            token = response["token"]
            print("Login successful!")
        else:
            print(response["message"])
    except Exception as e:
        print(f"Error during login: {e}")

def chat():
    if not token:
        print("You need to log in first.")
        return
    try:
        while True:
            message = input("Enter message (or 'exit' to quit): ").strip()
            if not message:
                print("Message cannot be empty. Please try again.")
                continue
            if message.lower() == "exit":
                break
            response = send_request({"action": "chat", "token": token, "message": message})
            print(response["message"])
    except Exception as e:
        print(f"Error during chat: {e}")

def view_chats():
    if not token:
        print("You need to log in first.")
        return
    try:
        response = send_request({"action": "get_all_chats"})
        for chat in response:
            print(f"{chat['username']} ({chat['timestamp']}): {chat['message']}")
    except Exception as e:
        print(f"Error viewing chats: {e}")

def add_project():
    if not token:
        print("You need to log in first.")
        return
    try:
        project_name = input("Enter project name: ").strip()
        if not project_name:
            print("Project name cannot be empty. Please try again.")
            return
        response = send_request({"action": "get_all_users"})
        if response:
            print("\nAvailable users:")
            for user in response:
                print(f"- {user}")
            print("Enter members (comma-separated usernames): ")
            members = input().strip()
            if not members:
                print("Members cannot be empty. Please try again.")
                return
            response = send_request({
                "action": "create_project",
                "token": token,
                "project_name": project_name,
                "members": [member.strip() for member in members.split(',')]
            })
            print(response["message"])
    except Exception as e:
        print(f"Error adding project: {e}")

def view_projects():
    try:
        response = send_request({"action": "get_projects"})
        if response:
            print("\nProjects:")
            for project in response:
                print(f"ID: {project['id']}, Name: {project['name']}, Owner: {project['owner']}")
                print(f"Members: {', '.join(project['members'])}")
        else:
            print("No projects found.")
    except Exception as e:
        print(f"Error viewing projects: {e}")

def add_task():
    if not token:
        print("You need to log in first.")
        return
    try:
        project_id = input("Enter project ID: ").strip()
        if not project_id.isdigit():
            print("Project ID must be a number. Please try again.")
            return
        project_id = int(project_id)
        response = send_request({"action": "get_projects"})
        if not any(project["id"] == project_id for project in response):
            print(f"Project with ID {project_id} does not exist.")
            return
        response = send_request({"action": "get_tasks", "project_id": project_id})
        print("\nMembers in this project:")
        for project in response:
            print(f"- {project['name']}")
        task_name = input("Enter task name: ").strip()
        if not task_name:
            print("Task name cannot be empty. Please try again.")
            return
        print("Enter task members (comma-separated usernames): ")
        members = input().strip()
        if not members:
            print("Members cannot be empty. Please try again.")
            return
        response = send_request({
            "action": "add_task",
            "token": token,
            "project_id": project_id,
            "task_name": task_name,
            "members": [member.strip() for member in members.split(',')]
        })
        print(response["message"])
    except Exception as e:
        print(f"Error adding task: {e}")

def view_tasks():
    try:
        project_id = input("Enter project ID to view tasks: ").strip()
        if not project_id.isdigit():
            print("Project ID must be a number. Please try again.")
            return
        project_id = int(project_id)
        response = send_request({"action": "get_tasks", "project_id": project_id})
        if response:
            print("\nTasks:")
            for task in response:
                print(f"Task ID: {task['id']}, Name: {task['name']}")
                print(f"Members: {', '.join(task['members'])}")
        else:
            print("No tasks found for this project.")
    except Exception as e:
        print(f"Error viewing tasks: {e}")

def main():
    while True:
        print("\n=== MENU ===")
        print("1. Register")
        print("2. Login")
        print("3. Chat")
        print("4. View Chats")
        print("5. Add Project")
        print("6. View Projects")
        print("7. Add Task")
        print("8. View Tasks")
        print("9. Exit")
        choice = input("Choose an option: ").strip()
        if choice == "1":
            register()
        elif choice == "2":
            login()
        elif choice == "3":
            chat()
        elif choice == "4":
            view_chats()
        elif choice == "5":
            add_project()
        elif choice == "6":
            view_projects()
        elif choice == "7":
            add_task()
        elif choice == "8":
            view_tasks()
        elif choice == "9":
            print("Goodbye!")
            break
        else:
            print("Invalid choice, please try again.")

if __name__ == "__main__":
    main()

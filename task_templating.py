import json
import os
import requests
import time
from datetime import datetime, timedelta

API_URL = "https://api.usemotion.com/v1"
API_KEY = os.environ.get("MOTION_API_KEY")
TEMPLATES_DIR = "templates"

if not API_KEY:
    raise EnvironmentError("MOTION_API_KEY environment variable must be set.")


def get_data(url, params=None):
    headers = {"X-API-Key": API_KEY}
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None


def post_data(url, data):
    headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error posting data: {e}")
        return None


def list_schedules():
    """Lists schedules available."""
    schedules_url = f"{API_URL}/schedules"
    schedules_data = get_data(schedules_url)
    schedules = []
    if schedules_data:
        schedules = schedules_data
    else:
        print("Could not retrieve schedules.")
        return None
    return schedules


def list_workspaces():
    workspaces_url = f"{API_URL}/workspaces"
    workspaces_data = get_data(workspaces_url)

    if not workspaces_data or "workspaces" not in workspaces_data:
        print("Could not retrieve workspaces.")
        return None

    workspaces = workspaces_data["workspaces"]

    if not workspaces:
        print("No workspaces found.")
        return None

    print("Available Workspaces:")
    for i, workspace in enumerate(workspaces):
        print(f"{i+1}. {workspace['name']} (ID: {workspace['id']})")

    while True:
        try:
            choice = int(input("Enter the number of the workspace you want to select: "))
            if 1 <= choice <= len(workspaces):
                return workspaces[choice - 1]
            else:
                print("Invalid selection. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")


def list_projects(workspace_id):
    projects_url = f"{API_URL}/projects"
    projects_data = get_data(projects_url, params={"workspaceId": workspace_id})

    if not projects_data or "projects" not in projects_data:
        print("Could not retrieve projects.")
        return None

    projects = projects_data["projects"]

    if not projects:
        print("No projects found in this workspace.")
        return None

    print("Available Projects:")
    for i, project in enumerate(projects):
        print(f"{i+1}. {project['name']} (ID: {project['id']})")

    while True:
        try:
            choice = int(input("Enter the number of the project you want to select: "))
            if 1 <= choice <= len(projects):
                return projects[choice - 1]
            else:
                print("Invalid selection. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")


def get_tasks_for_project(project_id):
    tasks_url = f"{API_URL}/tasks"
    tasks_data = get_data(tasks_url, params={"projectId": project_id})

    if not tasks_data or "tasks" not in tasks_data:
        print("Could not retrieve tasks for this project.")
        return []

    tasks = tasks_data["tasks"]
    return tasks

def generate_task_template(workspace, project, tasks):

    #Date Format implementation
    creation_time = datetime.now().strftime("%Y%m%d_%H%M%S") # Modified format

    template_tasks = []
    for task in tasks:
        task_post_data = {
            "name": task.get("name", ""),
            "workspaceId": workspace["id"],
            "dueDate": task.get("dueDate", "2024-12-31T23:59:59Z"),
            "duration": task.get("duration", 30),
            "priority": task.get("priority", "MEDIUM"),
        }
        template_tasks.append(task_post_data)

    template = {
        "tasks": template_tasks
    }

    filename = f"{workspace['name'].replace(' ', '_')}.{project['name'].replace(' ', '_')}.{creation_time}.json" # Added timestamp
    filepath = os.path.join(TEMPLATES_DIR, filename)

    if not os.path.exists(TEMPLATES_DIR):
        os.makedirs(TEMPLATES_DIR)

    try:
        with open(filepath, "w") as f:
            json.dump(template, f, indent=4)
        print(f"Template file created successfully at: {filepath}")
    except IOError as e:
        print(f"Error writing template file: {e}")


def load_template(filename):
    filepath = os.path.join(TEMPLATES_DIR, filename)
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Template file not found: {filepath}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in template file: {filepath}")
        return None
    except IOError as e:
        print(f"Error reading the file {filepath}: {e}")
        return None


def create_project(workspace, due_date_delta):
    """Create a new project and return its ID"""
    project_name = input("Enter the name for the new project: ")
    if not project_name:
        print("Project name cannot be empty. Project creation skipped.")
        return None

    try:
        if due_date_delta:
            due_date_delta = int(due_date_delta)
        else:
            due_date_delta = 0
    except ValueError:
        print("Invalid input. Using default due date.")
        due_date_delta = 0

    priority = input(   "Enter priority value (ASAP, HIGH, MEDIUM, LOW, or leave blank for MEDIUM):")
    if not priority:
        priority = "MEDIUM"
    elif priority.upper() not in ("ASAP", "HIGH", "MEDIUM", "LOW"):
        print("Value is not right. Reverting to default (MEDIUM)")
        priority = "MEDIUM"
    else:
        priority = priority.upper()

    new_date = datetime.utcnow()
    if due_date_delta:
        new_date = datetime.utcnow() + timedelta(days=due_date_delta)

    new_date = new_date.isoformat().replace("+00:00", "Z")

    post_payload = {
        "name": project_name,
        "workspaceId": workspace["id"],
        "priority": priority,
        "dueDate": new_date,
    }

    projects_url = f"{API_URL}/projects"
    response = post_data(projects_url, post_payload)

    if response and "id" in response:
        print(f"Project '{project_name}' created successfully! (ID: {response['id']})")
        return response["id"]
    else:
        print(f"Error creating project '{project_name}'.")
        return None


def create_tasks_from_template(workspace, template):
    """Creates multiple tasks from a task group template, with rate limiting."""
    if not template or "tasks" not in template:
        print("Invalid template format.")
        return

    due_date_delta = input(
        "Enter the number of days in the future for the due date (or leave blank for default): "
    )
    selected_schedule = None
    try:
        if due_date_delta:
            due_date_delta = int(due_date_delta)
        else:
            due_date_delta = 0
    except ValueError:
        print("Invalid input. Using default due date.")
        due_date_delta = 0

    create_new_project = input("Create a new project for these tasks (y/n)? ").lower() == "y"
    project_id = None
    if create_new_project:
        project_id = create_project(workspace, due_date_delta)

    use_autoschedule = input("Enable autoscheduling (y/n)? ").lower() == "y"

    schedules = list_schedules()

    if schedules:
        print("\nAvailable Schedules:")
        for i, schedule in enumerate(schedules):
            print(f"{i + 1}. {schedule['name']}")

        while True:
            try:
                schedule_choice = input(
                    "Enter the number of the schedule to use for ALL tasks (or enter 0 for none): "
                )

                if not schedule_choice:
                    print("No schedule selected. Proceeding without.")
                    break

                schedule_choice = int(schedule_choice)
                if schedule_choice == 0:
                    break
                if 1 <= schedule_choice <= len(schedules):
                    selected_schedule = schedules[schedule_choice - 1]['name']
                    break
                else:
                    print("Invalid selection. Please try again.")
            except ValueError:
                print("Invalid input. Please enter a number.")

    task_successes = 0
    task_failures = 0

    ##########################
    # Rate Limiting Implementation - SAFE VERSION
    ##########################
    DELAY_SECONDS = 8 # This ensures we stay well below 12 requests/minute
    for i, task_data in enumerate(template["tasks"]):
        print(f"Creating task {i+1}/{len(template['tasks'])}...")
        original_due_date = task_data.get(
            "dueDate", "2024-12-31T23:59:59Z")

        try:
            due_date = datetime.fromisoformat(
                original_due_date.replace("Z", "+00:00")) + timedelta(days=due_date_delta)
        except ValueError as e:
            print(f"Invalid date {original_due_date}, setting to today. {e}")
            due_date = datetime.utcnow()

        due_date_str = due_date.isoformat().replace("+00:00", "Z")


        post_payload = {
            "name": task_data["name"],
            "workspaceId": workspace["id"],
            "dueDate": due_date_str,
            "duration": task_data.get("duration", 30),
            "priority": task_data["priority"],
        }

        if project_id:
            post_payload["projectId"] = project_id

        if selected_schedule:
            post_payload["autoScheduled"] = {
                "startDate": datetime.utcnow().isoformat().replace("+00:00", "Z"),
                "deadlineType": "SOFT",
                "schedule": selected_schedule,
            }
        elif use_autoschedule and not selected_schedule:
            post_payload["autoScheduled"] = {
                "startDate": datetime.utcnow().isoformat().replace("+00:00", "Z"),
                "deadlineType": "SOFT",
                "schedule": "Work Hours",
            }

        tasks_url = f"{API_URL}/tasks"
        response = post_data(tasks_url, post_payload)

        if response and "id" in response:
            print(f"Task '{task_data['name']}' created successfully! (ID: {response['id']})")
            task_successes += 1
        else:
            print(f"Error creating task '{task_data['name']}'.")
            print(f"Payload sent: `{json.dumps(post_payload)}`")
            task_failures += 1

        time.sleep(DELAY_SECONDS)  # Wait 8 seconds

    print(f"Task Creations Completed with {task_successes}/{len(template['tasks'])} success and {task_failures} failures.")


def list_template_files():
    try:
        files = [f for f in os.listdir(TEMPLATES_DIR) if f.endswith(".json")]
        return files
    except FileNotFoundError:
        print(f"Template directory not found: {TEMPLATES_DIR}")
        return []


def get_template_filename_from_user(files):
    if not files:
        print("No template files found.")
        return None

    print("Available Task Group Templates:")
    for i, filename in enumerate(files):
        print(f"{i+1}. {filename}")

    while True:
        try:
            choice = input(
                "Enter the number of the template file to use (or leave blank to create a template): "
            )
            if not choice:
                return None

            choice = int(choice)
            if 1 <= choice <= len(files):
                return files[choice - 1]
            else:
                print("Invalid selection. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number or leave blank.")


def main_menu():
    while True:
        print("\nMain Menu:")
        print("1. Pull Task Group Template from Existing Tasks")
        print("2. Create Tasks from Task Group Template")
        print("3. Exit")

        choice = input("Enter your choice: ")

        if choice == "1":
            workspace = list_workspaces()
            if workspace:
                project = list_projects(workspace["id"])
                if project:
                    tasks = get_tasks_for_project(project["id"])
                    generate_task_template(workspace, project, tasks)
        elif choice == "2":
            workspace = list_workspaces()
            if workspace:
                template_files = list_template_files()
                template_filename = get_template_filename_from_user(template_files)
                if template_filename:
                    template = load_template(template_filename)
                    if template:
                        create_tasks_from_template(workspace, template)
                else:
                    print("Creating tasks without a template. Directing to step 1.")
                    project = list_projects(workspace["id"])
                    if project:
                        tasks = get_tasks_for_project(project["id"])
                        generate_task_template(workspace, project, tasks)
                    else:
                        print("No project was given to create a template from. Can't proceed.")
        elif choice == "3":
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main_menu()
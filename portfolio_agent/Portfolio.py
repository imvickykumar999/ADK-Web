import logging
import requests

logging.basicConfig(level=logging.DEBUG)
BASE_URL = "https://drfapi.pythonanywhere.com"

def get_home() -> dict:
    """Fetch Home from GET /api/home/. See get_api_overview for return format."""
    try:
        r = requests.get(f"{BASE_URL}/api/home/", timeout=30)
        r.raise_for_status()
        data = r.json()
        logging.debug("GET /api/home/ -> %s", data)
        return {"status": "success", "report": data}
    except requests.exceptions.Timeout:
        return {"status": "error", "report": "The request timed out. Please try again later."}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "report": f"An error occurred: {e}"}

def get_about() -> dict:
    """Fetch About from GET /api/about/. See get_api_overview for return format."""
    try:
        r = requests.get(f"{BASE_URL}/api/about/", timeout=30)
        r.raise_for_status()
        data = r.json()
        logging.debug("GET /api/about/ -> %s", data)
        return {"status": "success", "report": data}
    except requests.exceptions.Timeout:
        return {"status": "error", "report": "The request timed out. Please try again later."}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "report": f"An error occurred: {e}"}

def get_skilled() -> dict:
    """Fetch Skilled from GET /api/skilled/. See get_api_overview for return format."""
    try:
        r = requests.get(f"{BASE_URL}/api/skilled/", timeout=30)
        r.raise_for_status()
        data = r.json()
        logging.debug("GET /api/skilled/ -> %s", data)
        return {"status": "success", "report": data}
    except requests.exceptions.Timeout:
        return {"status": "error", "report": "The request timed out. Please try again later."}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "report": f"An error occurred: {e}"}

def get_skills() -> dict:
    """Fetch Skills from GET /api/skills/. See get_api_overview for return format."""
    try:
        r = requests.get(f"{BASE_URL}/api/skills/", timeout=30)
        r.raise_for_status()
        data = r.json()
        logging.debug("GET /api/skills/ -> %s", data)
        return {"status": "success", "report": data}
    except requests.exceptions.Timeout:
        return {"status": "error", "report": "The request timed out. Please try again later."}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "report": f"An error occurred: {e}"}

def get_work() -> dict:
    """Fetch Work from GET /api/work/. See get_api_overview for return format."""
    try:
        r = requests.get(f"{BASE_URL}/api/work/", timeout=30)
        r.raise_for_status()
        data = r.json()
        logging.debug("GET /api/work/ -> %s", data)
        return {"status": "success", "report": data}
    except requests.exceptions.Timeout:
        return {"status": "error", "report": "The request timed out. Please try again later."}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "report": f"An error occurred: {e}"}

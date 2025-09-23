# >>> ***`ADK` `Web`***

```bash
python3 -m venv .venv

# ubuntu
source .venv/bin/activate

# windows
.venv\Scripts\Activate

pip install -r requirements.txt

adk web --session_service_uri sqlite:///sessions.db --port 5000

Go to http://localhost:5000
Ctrl + C to exit.
```

<img width="1324" height="706" alt="image" src="https://github.com/user-attachments/assets/16863076-06fb-4834-a50f-2aeed30a0d61" />

    You can port forward to ngrok.

    >>> adk web --port 8000
    >>> ngrok http --url=internal-adjusted-possum.ngrok-free.app 8000

<img width="1322" height="699" alt="image" src="https://github.com/user-attachments/assets/c38e9b06-d356-4cac-bc32-73a94d7b7d77" />
<br><br>

>- Install and Run Ngrok : https://dashboard.ngrok.com/get-started/setup/linux
>- Deployed temporarily at : [`click here`](https://internal-adjusted-possum.ngrok-free.app/dev-ui/?app=tool_agent&session=00501ecd-79e9-4323-8aab-d835d407b1f6)
>- **Note** : `name=` parameter must match folder name, here `tool_agent` or `greeting_agent`.

```py
root_agent = Agent(
    name="tool_agent",
    ...

root_agent = Agent(
    name="greeting_agent",
    ...
```

```bash
>>> tree
.
├── 1-basic-agent
│   └── greeting_agent
│       ├── __init__.py
│       ├── __pycache__
│       │   ├── __init__.cpython-312.pyc
│       │   └── agent.cpython-312.pyc
│       └── agent.py
├── 2-tool-agent
│   └── tool_agent
│       ├── __init__.py
│       ├── __pycache__
│       │   ├── __init__.cpython-312.pyc
│       │   └── agent.cpython-312.pyc
│       └── agent.py
└── requirements.txt
```

---

## `1-basic-agent`

```bash
>>> ls -la
    total 24
    drwxrwxr-x  4 vicky vicky 4096 Sep 11 11:27 .
    drwxrwxr-x 50 vicky vicky 4096 Sep 11 11:25 ..
    drwxrwxr-x  3 vicky vicky 4096 Sep 11 10:38 1-basic-agent
    -rw-rw-r--  1 vicky vicky  123 Sep 11 10:51 requirements.txt
    drwxrwxr-x  5 vicky vicky 4096 Sep 11 10:54 .venv
>>> pip install -r requirements.txt
```

```bash
>>> pip install google-adk -U
>>> cd 1-basic-agent
>>> ls
    greeting_agent
>>> adk web
```

<img width="1322" height="699" alt="image" src="https://github.com/user-attachments/assets/3ec8af1d-5efc-4868-aa1b-2ea24e46edb5" />

---

## `2-tool-agent`

```bash
>>> cd 2-tool-agent
>>> ls
    tool_agent
>>> adk web
```

<img width="1322" height="699" alt="image" src="https://github.com/user-attachments/assets/d601c1f7-34f4-45f7-a95d-411bd82d385e" />

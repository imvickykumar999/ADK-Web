# ***`ADK` `Web`***

    You can port forward to ngrok.

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

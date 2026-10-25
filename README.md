# 📚 Libby – Library SQL Agent

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/<your-username>/libby-library-agent/blob/main/Latihan_Class_3.ipynb)

A library chatbot built with **LangGraph** (`create_agent`), **Google Gemini** and **Streamlit**.
Libby reads a SQLite database to answer questions about books: which books exist, where they are
shelved, whether they are available, and who borrowed them.

## What's in this repo

```
.
├── Latihan_Class_3.ipynb   # Class notebook: build the SQL agent step by step, then run it in Streamlit
├── streamlit_chat_app.py   # The Streamlit chatbot app (same code as the %%writefile cell)
├── init_db.py              # Creates library.db with tables + sample data
├── requirements.txt        # Python dependencies
└── README.md
```

`library.db` is **not** stored in the repo. It's created by the notebook's `%%sql` cell,
by `python init_db.py`, or automatically the first time the app starts.

## Before you start

You need a **Google AI (Gemini) API key**:
1. Open <https://aistudio.google.com>
2. Click **Get API Key → Create API Key** and copy it

Each person uses their own key. Never commit a key to GitHub.

---

## Option A — Run the notebook in Google Colab (recommended for class)

1. Click the **Open in Colab** badge at the top of this page.
2. In Colab, click the 🔑 **Secrets** icon in the left sidebar and add:
   | Name | Value |
   |------|-------|
   | `GEMINI` | your Gemini API key |
   | `NGROK_TOKEN` | your ngrok authtoken from <https://dashboard.ngrok.com> (free account) |

   Turn on **Notebook access** for both.
3. Run the cells from top to bottom (**Runtime → Run all**).
4. The "Jalankan chatbot-nya" cell prints a link like `https://xxxx.ngrok-free.dev`. Open it,
   paste your Gemini key into the sidebar, and start chatting.
5. When you're done, run the last cell to stop Streamlit and close the tunnel.

> If you re-run the `%%sql` cell you'll see `UNIQUE constraint failed`. That's normal:
> the sample data is already in the database.

## Option B — Run only the app in Colab (without the notebook)

```python
!git clone https://github.com/<your-username>/libby-library-agent.git
%cd libby-library-agent
!pip install -q -r requirements.txt pyngrok
!python init_db.py
```

```python
import subprocess, time
from pyngrok import ngrok
from google.colab import userdata

ngrok.set_auth_token(userdata.get("NGROK_TOKEN"))
proc = subprocess.Popen(
    ["streamlit", "run", "streamlit_chat_app.py", "--server.headless=true", "--server.port", "8501"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
)
time.sleep(5)
print("Open the app:", ngrok.connect(8501).public_url)
```

Stop it with `proc.terminate(); ngrok.kill()`.

## Option C — Run on your own computer

Requires Python 3.10+. No ngrok needed.

```bash
git clone https://github.com/<your-username>/libby-library-agent.git
cd libby-library-agent

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
python init_db.py                # optional, the app does this automatically
streamlit run streamlit_chat_app.py
```

Open <http://localhost:8501> and paste your Gemini key into the sidebar.

---

## Try asking

- "Buku apa saja karya Andrea Hirata?"
- "Is *Clean Code* available? Where is it shelved?"
- "Siapa yang meminjam *Database System Concepts*?"
- "Buku apa saja yang ada di Reading Room?"

## Reset the sample data

```bash
python init_db.py --reset
```

## How it works

1. The agent has three tools: `list_tables`, `describe_table` and `execute_query`.
2. The system prompt tells it to always inspect the schema before writing SQL.
3. The app opens the database **read-only**, so the agent can't change any data.
4. `st.session_state` keeps the chat history across Streamlit reruns.

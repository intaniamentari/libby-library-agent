# Import library yang dibutuhkan
import os
import sqlite3
import streamlit as st
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent

# Lokasi database (file yang sama dengan yang dibuat di Langkah 1)
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "library.db")

# ── 1. Konfigurasi Halaman ───────────────────────────────────────────────────
st.title("📚 Libby – Library Agent")
st.caption("Chatbot perpustakaan yang bisa membaca data buku yang ada di perpustakaan dan ketersediaannya untuk bisa dipinjam dan lokasi buku")

# ── 2. Sidebar: Pengaturan App ───────────────────────────────────────────────
with st.sidebar:
    st.subheader("Pengaturan")
    google_api_key = st.text_input("Google AI API Key", type="password")
    show_tools = st.checkbox("Tampilkan tool calls", value=True,
                             help="Lihat tool apa saja yang dipanggil agent")
    reset_button = st.button("Reset Percakapan", help="Hapus semua pesan dan mulai dari awal")

# ── 3. Validasi API Key & Database ───────────────────────────────────────────
if not google_api_key:
    st.info("Masukkan Google AI API Key di sidebar untuk mulai chat.", icon="🗝️")
    st.stop()

if not os.path.exists(DB_FILE):
    # Buat database otomatis (misal: baru clone repo dari GitHub)
    from init_db import create_database
    create_database(DB_FILE)

# ── 4. Tools untuk SQL Agent (sama seperti Langkah 2) ────────────────────────
# Streamlit berjalan di proses terpisah, jadi tools harus didefinisikan ulang di sini.
# Koneksi dibuka read-only supaya agent tidak bisa mengubah data.
def _connect():
    return sqlite3.connect(f"file:{DB_FILE}?mode=ro", uri=True)

def list_tables() -> list[str]:
    """Retrieve the names of all tables in the database."""
    with _connect() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        return [t[0] for t in cursor.fetchall()]

def describe_table(table_name: str) -> list[tuple[str, str]]:
    """Look up the table schema.

    Returns:
      List of columns, where each entry is a tuple of (column, type).
    """
    with _connect() as conn:
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name});")
        return [(col[1], col[2]) for col in cursor.fetchall()]

def execute_query(sql: str) -> list[list[str]]:
    """Execute a SELECT statement, returning the results."""
    with _connect() as conn:
        cursor = conn.cursor()
        cursor.execute(sql)
        return cursor.fetchall()

db_tools = [list_tables, describe_table, execute_query]

# ── 5. System Prompt (sama seperti Langkah 3) ────────────────────────────────
instruction = """
# Role
You are "Libby", a friendly library assistant for a public library. You help
readers and librarians find books, check where a book is shelved, see whether
it is available or borrowed, and who borrowed it.

# Tone
- Warm, polite and concise. Use simple language.
- Answer in the same language the user writes in (English or Bahasa Indonesia).
- When listing several books, use a short bulleted list.

# How to use the database
- ALWAYS start by calling list_tables to discover the available tables.
- ALWAYS call describe_table on the relevant tables before writing SQL.
- Never assume or guess table or column names; verify first.
- Only run SELECT queries. Never INSERT, UPDATE, DELETE or DROP anything.

# Privacy
- Do not reveal readers' email or phone numbers unless the user says they are a librarian.

# If you can't find it
- Say so honestly and suggest a similar search (e.g. by author or partial title).
"""

# ── 6. Inisialisasi Agent ────────────────────────────────────────────────────
# Agent hanya dibuat ulang kalau belum ada atau API key berganti
if ("agent" not in st.session_state) or (
    st.session_state.get("_last_key") != google_api_key
):
    try:
        model = ChatGoogleGenerativeAI(
            model="gemini-3.5-flash-lite",
            temperature=0,
            google_api_key=google_api_key,
        )
        st.session_state.agent = create_agent(
            model=model,
            tools=db_tools,
            system_prompt=instruction,
        )
        st.session_state._last_key = google_api_key
        st.session_state.pop("messages", None)
    except Exception as e:
        st.error(f"Gagal membuat agent: {e}")
        st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []

# ── 7. Tombol Reset ──────────────────────────────────────────────────────────
if reset_button:
    st.session_state.pop("messages", None)
    st.rerun()

# ── Helper: ambil teks dari konten pesan Gemini ──────────────────────────────
# Gemini kadang mengembalikan content berupa list of parts, bukan string
def to_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for p in content:
            if isinstance(p, str):
                parts.append(p)
            elif isinstance(p, dict) and p.get("type") == "text":
                parts.append(p.get("text", ""))
        return "".join(parts)
    return str(content)

# ── 8. Tampilkan Riwayat Percakapan ──────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── 9. Input & Respons ───────────────────────────────────────────────────────
prompt = st.chat_input("Tanya Libby, misal: 'Buku apa saja karya Andrea Hirata?'")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Libby sedang mencari di database..."):
                # Kirim seluruh riwayat ke agent supaya konteks percakapan terjaga
                history = [{"role": m["role"], "content": m["content"]}
                           for m in st.session_state.messages]
                result = st.session_state.agent.invoke({"messages": history})

            new_msgs = result["messages"][len(history):]

            # Tampilkan tool calls (opsional) agar terlihat proses berpikir agent
            if show_tools:
                calls = [tc for m in new_msgs for tc in (getattr(m, "tool_calls", None) or [])]
                if calls:
                    with st.expander(f"🔧 {len(calls)} tool call"):
                        for tc in calls:
                            st.code(f"{tc['name']}({tc['args']})", language="python")

            answer = to_text(result["messages"][-1].content) or "_(tidak ada jawaban)_"
        except Exception as e:
            answer = f"Terjadi error: {e}"

        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})

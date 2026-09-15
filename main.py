import streamlit as st
import subprocess
import os
import re
import time
import threading
from pathlib import Path


# ============================================================
# SSHX CONFIG
# ============================================================

SSHX_DIR = Path.home() / ".local" / "bin"
SSHX_PATH = SSHX_DIR / "sshx"


# ============================================================
# INSTALL SSHX
# ============================================================

def install_sshx():
    SSHX_DIR.mkdir(parents=True, exist_ok=True)

    if SSHX_PATH.exists():
        return True

    st.info("Installing sshx...")

    try:
        result = subprocess.run(
            "curl -sSf https://sshx.io/get | sh",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=120
        )

        print(result.stdout, flush=True)

        if SSHX_PATH.exists():
            return True

        # بعضی نسخه‌های installer ممکن است مسیر دیگری استفاده کنند
        possible_paths = [
            Path.home() / ".local/bin/sshx",
            Path("/usr/local/bin/sshx"),
            Path("/usr/bin/sshx"),
        ]

        for path in possible_paths:
            if path.exists():
                return True

        return False

    except Exception as e:
        print(f"SSHX install error: {e}", flush=True)
        return False


# ============================================================
# FIND SSHX
# ============================================================

def find_sshx():

    paths = [
        SSHX_PATH,
        Path.home() / ".local/bin/sshx",
        Path("/usr/local/bin/sshx"),
        Path("/usr/bin/sshx"),
    ]

    for path in paths:
        if path.exists() and os.access(path, os.X_OK):
            return str(path)

    return None


# ============================================================
# SSHX MANAGER
# ============================================================

class SSHXManager:

    def __init__(self):
        self.process = None
        self.url = None
        self.lock = threading.Lock()
        self.thread = None
        self.running = False

    def start(self):

        with self.lock:

            # اگر قبلاً اجرا شده و هنوز زنده است
            if self.process is not None:
                if self.process.poll() is None:
                    return

            sshx = find_sshx()

            if not sshx:
                print("sshx not found. Installing...", flush=True)

                if not install_sshx():
                    print("Could not install sshx", flush=True)
                    return

                sshx = find_sshx()

            if not sshx:
                print("sshx executable still not found", flush=True)
                return

            print(f"Starting sshx: {sshx}", flush=True)

            try:

                self.process = subprocess.Popen(
                    [sshx],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    text=True,
                    bufsize=1,
                    start_new_session=True
                )

                self.running = True

                self.thread = threading.Thread(
                    target=self.read_output,
                    daemon=True
                )

                self.thread.start()

            except Exception as e:
                print(f"SSHX start error: {e}", flush=True)

    def read_output(self):

        if not self.process:
            return

        try:

            for line in iter(self.process.stdout.readline, ""):

                if not line:
                    break

                line = line.strip()

                if line:
                    print(f"[sshx] {line}", flush=True)

                # پیدا کردن لینک sshx
                urls = re.findall(
                    r'https?://[^\s]+',
                    line
                )

                for url in urls:

                    # حذف کاراکترهای انتهایی
                    url = url.rstrip(
                        ".,;)]}\"'"
                    )

                    if "sshx.io" in url:
                        self.url = url

                        print(
                            f"\nSSHX PUBLIC URL: {url}\n",
                            flush=True
                        )

        except Exception as e:

            print(
                f"SSHX output reader error: {e}",
                flush=True
            )

        self.running = False

    def is_alive(self):

        return (
            self.process is not None
            and self.process.poll() is None
        )

    def get_url(self):

        return self.url


# ============================================================
# CREATE SINGLE SSHX MANAGER
# ============================================================

@st.cache_resource
def get_sshx_manager():

    manager = SSHXManager()

    # شروع SSHX
    manager.start()

    return manager


# ============================================================
# AUTO RESTART
# ============================================================

def ensure_sshx(manager):

    if not manager.is_alive():

        print(
            "SSHX is not running. Restarting...",
            flush=True
        )

        manager.start()


# ============================================================
# STREAMLIT UI
# ============================================================

st.title("SSHX Public SSH")

manager = get_sshx_manager()

# اگر sshx قطع شده باشد دوباره اجرا می‌شود
ensure_sshx(manager)

st.write("SSHX Status")

if manager.is_alive():

    st.success("SSHX is running")

else:

    st.error("SSHX is not running")


# ============================================================
# SHOW PUBLIC URL
# ============================================================

url = manager.get_url()

if url:

    st.success("Public SSH URL:")

    st.code(
        url,
        language="text"
    )

    st.markdown(
        f"""
        ### SSH URL

        `{url}`
        """
    )

else:

    st.warning(
        "Waiting for SSHX public URL..."
    )

    st.info(
        "Refresh the Streamlit page after a few seconds."
    )


# ============================================================
# MANUAL RESTART
# ============================================================

if st.button("Restart SSHX"):

    try:

        if manager.process:

            manager.process.terminate()

            time.sleep(2)

    except Exception:
        pass

    manager.url = None
    manager.process = None

    manager.start()

    st.rerun()

import streamlit as st
import subprocess
import os
import re
import time
import threading
import urllib.request
import tarfile
from pathlib import Path


# ============================================================
# SSHX CONFIG
# ============================================================

SSHX_DIR = Path.home() / ".local" / "bin"
SSHX_PATH = SSHX_DIR / "sshx"

SSHX_URL = (
    "https://s3.amazonaws.com/sshx/"
    "sshx-x86_64-unknown-linux-musl.tar.gz"
)


# ============================================================
# INSTALL SSHX WITHOUT SUDO
# ============================================================

def install_sshx():

    SSHX_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    if SSHX_PATH.exists():
        SSHX_PATH.chmod(0o755)
        return True

    archive = Path("/tmp/sshx.tar.gz")
    extract_dir = Path("/tmp/sshx_extract")

    try:

        print(
            f"Downloading sshx from {SSHX_URL}",
            flush=True
        )

        urllib.request.urlretrieve(
            SSHX_URL,
            archive
        )

        if extract_dir.exists():
            subprocess.run(
                ["rm", "-rf", str(extract_dir)],
                check=False
            )

        extract_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        print(
            "Extracting sshx...",
            flush=True
        )

        with tarfile.open(
            archive,
            "r:gz"
        ) as tar:

            tar.extractall(
                extract_dir
            )

        # پیدا کردن فایل اجرایی sshx
        found = None

        for p in extract_dir.rglob("sshx"):

            if p.is_file():
                found = p
                break

        if found is None:

            print(
                "sshx binary was not found in archive",
                flush=True
            )

            return False

        # کپی به مسیر کاربر
        subprocess.run(
            [
                "cp",
                str(found),
                str(SSHX_PATH)
            ],
            check=True
        )

        SSHX_PATH.chmod(0o755)

        print(
            f"sshx installed at {SSHX_PATH}",
            flush=True
        )

        return True

    except Exception as e:

        print(
            f"SSHX installation error: {e}",
            flush=True
        )

        return False

    finally:

        try:
            archive.unlink(
                missing_ok=True
            )
        except Exception:
            pass


# ============================================================
# FIND SSHX
# ============================================================

def find_sshx():

    paths = [

        SSHX_PATH,

        Path.home() / ".local" / "bin" / "sshx",

        Path("/usr/local/bin/sshx"),

        Path("/usr/bin/sshx"),

    ]

    for path in paths:

        if (
            path.exists()
            and os.access(path, os.X_OK)
        ):
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

            # اگر قبلاً اجرا شده
            if self.process is not None:

                if self.process.poll() is None:
                    return

            sshx = find_sshx()

            # نصب
            if not sshx:

                print(
                    "sshx not found. Installing...",
                    flush=True
                )

                if not install_sshx():

                    print(
                        "Could not install sshx",
                        flush=True
                    )

                    return

                sshx = find_sshx()


            if not sshx:

                print(
                    "sshx executable still not found",
                    flush=True
                )

                return


            print(
                f"Starting sshx: {sshx}",
                flush=True
            )


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

                print(
                    f"SSHX start error: {e}",
                    flush=True
                )


    def read_output(self):

        if not self.process:
            return


        try:

            for line in iter(
                self.process.stdout.readline,
                ""
            ):

                if not line:
                    break


                line = line.strip()


                if line:

                    print(
                        f"[sshx] {line}",
                        flush=True
                    )


                # پیدا کردن URL
                urls = re.findall(
                    r'https?://[^\s]+',
                    line
                )


                for url in urls:

                    url = url.rstrip(
                        ".,;)]}\"'"
                    )


                    if "sshx.io" in url:

                        self.url = url


                        print(
                            "\n"
                            f"SSHX PUBLIC URL: {url}"
                            "\n",
                            flush=True
                        )


        except Exception as e:

            print(
                f"SSHX output error: {e}",
                flush=True
            )


        self.running = False


    def is_alive(self):

        return (

            self.process is not None

            and

            self.process.poll() is None

        )


    def get_url(self):

        return self.url


# ============================================================
# SINGLE SSHX INSTANCE
# ============================================================

@st.cache_resource
def get_sshx_manager():

    manager = SSHXManager()

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
# STREAMLIT
# ============================================================

st.title("SSHX Public SSH")


manager = get_sshx_manager()


# اگر sshx قطع شده باشد
ensure_sshx(manager)


# ============================================================
# STATUS
# ============================================================

if manager.is_alive():

    st.success(
        "SSHX is running"
    )

else:

    st.error(
        "SSHX is not running"
    )


# ============================================================
# URL
# ============================================================

url = manager.get_url()


if url:

    st.success(
        "Public SSH URL:"
    )

    st.code(
        url,
        language="text"
    )

else:

    st.warning(
        "Waiting for SSHX public URL..."
    )


# ============================================================
# RESTART BUTTON
# ============================================================

if st.button(
    "Restart SSHX"
):

    try:

        if manager.process:

            manager.process.terminate()

            time.sleep(2)

    except Exception:
        pass


    manager.process = None

    manager.url = None

    manager.start()


    st.rerun()

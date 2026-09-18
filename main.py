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
            f"[SSHX] Downloading: {SSHX_URL}",
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
            "[SSHX] Extracting...",
            flush=True
        )

        with tarfile.open(
            archive,
            "r:gz"
        ) as tar:

            tar.extractall(
                extract_dir
            )

        found = None

        for p in extract_dir.rglob("sshx"):

            if p.is_file():
                found = p
                break

        if found is None:

            print(
                "[SSHX] Binary was not found",
                flush=True
            )

            return False

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
            f"[SSHX] Installed: {SSHX_PATH}",
            flush=True
        )

        return True

    except Exception as e:

        print(
            f"[SSHX] Installation error: {e}",
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


    # --------------------------------------------------------
    # START SSHX
    # --------------------------------------------------------

    def start(self):

        with self.lock:

            if self.process is not None:

                if self.process.poll() is None:

                    print(
                        "[SSHX] Already running",
                        flush=True
                    )

                    return


            sshx = find_sshx()


            # ------------------------------------------------
            # INSTALL
            # ------------------------------------------------

            if not sshx:

                print(
                    "[SSHX] Not found. Installing...",
                    flush=True
                )

                if not install_sshx():

                    print(
                        "[SSHX] Installation failed",
                        flush=True
                    )

                    return

                sshx = find_sshx()


            if not sshx:

                print(
                    "[SSHX] Executable still not found",
                    flush=True
                )

                return


            print(
                f"[SSHX] Executable: {sshx}",
                flush=True
            )


            # ------------------------------------------------
            # RUN SSHX
            # ------------------------------------------------

            try:

                self.process = subprocess.Popen(

                    [
                        sshx,
                        "run"
                    ],

                    stdout=subprocess.PIPE,

                    stderr=subprocess.STDOUT,

                    stdin=subprocess.DEVNULL,

                    text=True,

                    bufsize=1,

                    start_new_session=True

                )

                self.running = True


                print(
                    "[SSHX] Process started",
                    flush=True
                )

                print(
                    "[SSHX] Waiting for public URL...",
                    flush=True
                )


                self.thread = threading.Thread(

                    target=self.read_output,

                    daemon=True

                )

                self.thread.start()


            except Exception as e:

                print(
                    f"[SSHX] Start error: {e}",
                    flush=True
                )


    # --------------------------------------------------------
    # READ SSHX OUTPUT
    # --------------------------------------------------------

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


                if not line:
                    continue


                # ------------------------------------------------
                # PRINT EVERY SSHX LINE TO STREAMLIT LOG
                # ------------------------------------------------

                print(
                    f"[SSHX] {line}",
                    flush=True
                )


                # ------------------------------------------------
                # FIND HTTP / HTTPS URL
                # ------------------------------------------------

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


                        # ========================================
                        # IMPORTANT:
                        # THIS APPEARS IN DAPPLING LOG
                        # ========================================

                        print(
                            "",
                            flush=True
                        )

                        print(
                            "========================================",
                            flush=True
                        )

                        print(
                            "       SSHX PUBLIC URL",
                            flush=True
                        )

                        print(
                            "========================================",
                            flush=True
                        )

                        print(
                            url,
                            flush=True
                        )

                        print(
                            "========================================",
                            flush=True
                        )

                        print(
                            "",
                            flush=True
                        )


        except Exception as e:

            print(
                f"[SSHX] Output error: {e}",
                flush=True
            )


        self.running = False


    # ========================================================
    # STATUS
    # ========================================================

    def is_alive(self):

        return (

            self.process is not None

            and

            self.process.poll() is None

        )


    # ========================================================
    # GET URL
    # ========================================================

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
            "[SSHX] Process stopped. Restarting...",
            flush=True
        )

        manager.start()


# ============================================================
# STREAMLIT UI
# ============================================================

st.title(
    "SSHX Public SSH"
)


manager = get_sshx_manager()


ensure_sshx(
    manager
)


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
# PUBLIC URL
# ============================================================

url = manager.get_url()


if url:

    st.success(
        "SSHX Public URL:"
    )

    st.code(
        url,
        language="text"
    )

    st.link_button(
        "Open SSHX",
        url
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

    manager.running = False


    manager.start()


    st.rerun()
```

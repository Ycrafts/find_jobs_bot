import os
import signal
import subprocess
import sys
import time

# Resolve project directory and script paths so this works from any CWD
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_PATH = os.path.join(PROJECT_DIR, "main.py")
WORKER_PATH = os.path.join(PROJECT_DIR, "worker.py")


def _send_signal_if_alive(proc: subprocess.Popen, sig: int) -> None:
    if proc is not None and proc.poll() is None:
        try:
            proc.send_signal(sig)
        except Exception:
            pass


def _terminate_gently(proc: subprocess.Popen, grace_seconds: float = 5.0) -> None:
    if proc is None:
        return
    if proc.poll() is not None:
        return
    try:
        proc.terminate()
    except Exception:
        pass
    deadline = time.time() + grace_seconds
    while time.time() < deadline:
        if proc.poll() is not None:
            return
        time.sleep(0.2)
    try:
        proc.kill()
    except Exception:
        pass


def run_all() -> int:
    env_main = os.environ.copy()
    # Avoid duplicate schedulers: let worker own scheduling when running together
    env_main["ENABLE_SCHEDULER"] = "false"

    print("[entrypoint] Starting main (bot-only)...")
    p_main = subprocess.Popen([sys.executable, MAIN_PATH], env=env_main, cwd=PROJECT_DIR)

    print("[entrypoint] Starting worker (scheduler)...")
    p_worker = subprocess.Popen([sys.executable, WORKER_PATH], env=os.environ.copy(), cwd=PROJECT_DIR)

    shutdown_requested = {"flag": False}

    def _handle_signal(signum, frame):
        if shutdown_requested["flag"]:
            return
        shutdown_requested["flag"] = True
        print(f"[entrypoint] Signal {signum} received. Shutting down children...")
        _send_signal_if_alive(p_main, signal.SIGINT)
        _send_signal_if_alive(p_worker, signal.SIGINT)

    # Handle SIGINT/SIGTERM for graceful stop
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    try:
        # Wait until any child exits
        while True:
            main_rc = p_main.poll()
            worker_rc = p_worker.poll()
            if main_rc is not None or worker_rc is not None:
                break
            time.sleep(0.3)
    except KeyboardInterrupt:
        _handle_signal(signal.SIGINT, None)
    finally:
        # Ensure both are stopping
        _send_signal_if_alive(p_main, signal.SIGINT)
        _send_signal_if_alive(p_worker, signal.SIGINT)
        # Gentle terminate leftover
        _terminate_gently(p_main)
        _terminate_gently(p_worker)

    # Compute exit code
    main_rc = p_main.returncode if p_main.returncode is not None else 0
    worker_rc = p_worker.returncode if p_worker.returncode is not None else 0
    exit_code = main_rc if main_rc != 0 else worker_rc
    print(f"[entrypoint] Exiting. main_rc={main_rc}, worker_rc={worker_rc}")
    return exit_code


def main() -> int:
    mode = os.getenv("APP_MODE", "all").strip().lower()
    if mode == "main":
        # Replace current process so it becomes PID1
        os.execv(sys.executable, [sys.executable, MAIN_PATH])
    elif mode == "worker":
        os.execv(sys.executable, [sys.executable, WORKER_PATH])
    elif mode == "all":
        return run_all()
    else:
        print(f"[entrypoint] Unknown APP_MODE='{mode}'. Use one of: main, worker, all.")
        return 2


if __name__ == "__main__":
    sys.exit(main()) 
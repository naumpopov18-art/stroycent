log_file = None

def debug_log(msg):
    print(f"[DEBUG] {msg}")
    if log_file:
        log_file.write(f"[DEBUG] {msg}\n")
        log_file.flush()

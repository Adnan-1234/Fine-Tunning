import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import subprocess
import os

# ===== YAHAN APNA GITHUB LINK DAALO =====
GITHUB_REPO_LINK = "https://github.com/Adnan-1234/Fine-Tunning.git"
# ========================================

REPO_PATH = os.path.dirname(os.path.abspath(__file__))

def remove_lock_file():
    """Remove index.lock file if exists"""
    lock_file = os.path.join(REPO_PATH, ".git", "index.lock")
    if os.path.exists(lock_file):
        try:
            os.remove(lock_file)
            print("🔓 Removed existing index.lock file")
        except Exception as e:
            print(f"⚠️ Could not remove lock file: {e}")

def run_git_command(cmd, cwd):
    """Run git command with lock file handling"""
    remove_lock_file()  # Remove lock before each command
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    
    # Agar lock file error aaye toh remove karke dobara try karo
    if "index.lock" in result.stderr:
        remove_lock_file()
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    
    if result.returncode != 0 and result.stderr:
        # Ignore "nothing to commit" error
        if "nothing to commit" not in result.stderr:
            print(f"⚠️ Git warning: {result.stderr}")
    
    return result

class AutoGitHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if not event.is_directory:
            # Thoda wait karo file write complete hone ke liye
            time.sleep(0.5)
            
            print(f"🔄 Change detected: {os.path.basename(event.src_path)}")
            
            # Git add
            run_git_command(["git", "add", "."], REPO_PATH)
            
            # Git commit (ignore agar kuch commit karne ko nahi hai)
            result = run_git_command(["git", "commit", "-m", "Auto push"], REPO_PATH)
            if "nothing to commit" in result.stderr:
                print("📝 No changes to commit")
                return
            
            # Git push
            run_git_command(["git", "push"], REPO_PATH)
            print("✅ Pushed to GitHub\n")  

# Pehle lock file remove karo
remove_lock_file()

# Pehle check karo git init hua ya nahi
if not os.path.exists(os.path.join(REPO_PATH, ".git")):
    print("🔧 First time setup - Initializing git...")
    run_git_command(["git", "init"], REPO_PATH)
    run_git_command(["git", "remote", "add", "origin", GITHUB_REPO_LINK], REPO_PATH)
    run_git_command(["git", "branch", "-M", "main"], REPO_PATH)
    print("✅ Git initialized with your repo link")

# Pehli baar sab files ko push karo
print("📤 Pushing all existing files to GitHub...")
run_git_command(["git", "add", "."], REPO_PATH)
run_git_command(["git", "commit", "-m", "Initial commit - all files"], REPO_PATH)
run_git_command(["git", "push", "-u", "origin", "main"], REPO_PATH)
print("✅ Initial push complete!\n")

# Ab watch karo
observer = Observer()
observer.schedule(AutoGitHandler(), REPO_PATH, recursive=True)
observer.start()
print(f"🚀 Watching: {REPO_PATH}")
print("📁 Ab jo bhi file banayoge ya change karoge, auto push hoga!\n")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    observer.stop()
observer.join()
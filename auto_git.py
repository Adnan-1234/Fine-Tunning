import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import subprocess
import os
import sys

# ===== CONFIGURATION =====
GITHUB_REPO_LINK = "https://github.com/Adnan-1234/Fine-Tunning.git"
BRANCH_NAME = "main"
REPO_PATH = os.path.dirname(os.path.abspath(__file__))
# ========================

def remove_lock_file():
    """Remove index.lock file if exists"""
    lock_file = os.path.join(REPO_PATH, ".git", "index.lock")
    if os.path.exists(lock_file):
        try:
            os.remove(lock_file)
            print("🔓 Removed lock file")
        except:
            pass

def run_git_command(cmd, cwd, timeout=120):
    """Run git command with automatic error handling"""
    remove_lock_file()
    
    try:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f"⏰ Command timeout: {' '.join(cmd)}")
        return None
    except Exception as e:
        print(f"❌ Command error: {e}")
        return None
    
    # Auto-handle lock file errors
    if result.stderr and "index.lock" in result.stderr:
        remove_lock_file()
        try:
            result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        except:
            pass
    
    return result

def is_harmful_error(stderr):
    """Check if error message is harmful or just informational"""
    harmless_patterns = [
        "nothing to commit", "already up to date", "no upstream branch",
        "fetch first", "secret scanning", "push protection", "paths",
        "updating currently", "pull before pushing", "divergent branches"
    ]
    return any(pattern.lower() in stderr.lower() for pattern in harmless_patterns)

def auto_fix_merge_conflicts():
    """Automatically resolve merge conflicts"""
    print("🔧 Auto-resolving merge conflicts...")
    
    # Accept all remote changes for conflicts
    run_git_command(["git", "checkout", "--theirs", "."], REPO_PATH)
    run_git_command(["git", "add", "."], REPO_PATH)
    run_git_command(["git", "commit", "-m", "Auto-resolved merge conflicts"], REPO_PATH)
    print("✅ Conflicts resolved")

def sync_with_remote():
    """Sync local with remote repository"""
    print("🔄 Syncing with remote...")
    
    # Fetch latest changes
    run_git_command(["git", "fetch", "origin"], REPO_PATH)
    
    # Try to pull with auto-merge
    result = run_git_command(["git", "pull", "origin", BRANCH_NAME, "--allow-unrelated-histories", "--no-rebase"], REPO_PATH)
    
    if result and result.stderr and "CONFLICT" in result.stderr:
        auto_fix_merge_conflicts()
        return True
    return True

def push_with_retry(max_retries=3):
    """Push with automatic retry and force push fallback"""
    for attempt in range(max_retries):
        print(f"📤 Push attempt {attempt + 1}/{max_retries}...")
        
        # Try normal push
        result = run_git_command(["git", "push", "-u", "origin", BRANCH_NAME], REPO_PATH)
        
        if result and result.returncode == 0:
            print("✅ Push successful")
            return True
        
        # Check if force push is needed
        if result and result.stderr:
            error_msg = result.stderr.lower()
            
            if "rejected" in error_msg or "fetch first" in error_msg:
                print("⚠️ Push rejected, syncing...")
                sync_with_remote()
                
                # Try normal push again after sync
                result = run_git_command(["git", "push", "-u", "origin", BRANCH_NAME], REPO_PATH)
                if result and result.returncode == 0:
                    return True
                
                # Last resort: force push
                print("⚠️ Trying force push...")
                result = run_git_command(["git", "push", "-u", "origin", BRANCH_NAME, "--force"], REPO_PATH)
                if result and result.returncode == 0:
                    print("✅ Force push successful")
                    return True
            
            elif "secret" in error_msg or "token" in error_msg:
                print("🔒 Secret detected! Please allow it on GitHub:")
                print("   https://github.com/Adnan-1234/Fine-Tunning/settings/security_analysis")
                print("📌 Or remove hardcoded tokens from your files")
                return False
        
        if attempt < max_retries - 1:
            print(f"⏳ Retrying in 3 seconds...")
            time.sleep(3)
    
    print("❌ Push failed after all retries")
    return False

def initial_setup():
    """Complete initial repository setup"""
    print("🔧 Setting up repository...")
    
    # Configure git to handle large files and timeouts
    subprocess.run(["git", "config", "--global", "http.postBuffer", "524288000"], capture_output=True)
    subprocess.run(["git", "config", "--global", "http.lowSpeedLimit", "0"], capture_output=True)
    subprocess.run(["git", "config", "--global", "http.lowSpeedTime", "999999"], capture_output=True)
    subprocess.run(["git", "config", "--global", "push.autoSetupRemote", "true"], capture_output=True)
    subprocess.run(["git", "config", "--global", "pull.rebase", "false"], capture_output=True)
    
    remove_lock_file()
    
    # Initialize git if needed
    if not os.path.exists(os.path.join(REPO_PATH, ".git")):
        print("📁 Initializing git repository...")
        run_git_command(["git", "init"], REPO_PATH)
        run_git_command(["git", "remote", "add", "origin", GITHUB_REPO_LINK], REPO_PATH)
        run_git_command(["git", "branch", "-M", BRANCH_NAME], REPO_PATH)
        print("✅ Git initialized")
    else:
        # Ensure remote is correct
        run_git_command(["git", "remote", "set-url", "origin", GITHUB_REPO_LINK], REPO_PATH)
        run_git_command(["git", "branch", "-M", BRANCH_NAME], REPO_PATH)
    
    # Create .gitignore if not exists
    gitignore_path = os.path.join(REPO_PATH, ".gitignore")
    if not os.path.exists(gitignore_path):
        with open(gitignore_path, "w") as f:
            f.write("""# Python
__pycache__/
*.py[cod]
*.so
.Python

# Jupyter Notebook
.ipynb_checkpoints/
*.ipynb

# Large files
*.pth
*.bin
*.zip
*.tar.gz

# IDE
.vscode/
.idea/

# Secrets
*secret*
*token*
*.env
""")
        print("✅ Created .gitignore")

def ensure_no_tokens_in_files():
    """Check and warn about tokens in files"""
    problematic_patterns = ["github_pat_", "ghp_", "gho_", "ghu_", "ghs_", "ghr_"]
    
    for root, dirs, files in os.walk(REPO_PATH):
        if ".git" in root:
            continue
        for file in files:
            if file.endswith((".py", ".txt", ".md", ".json", ".yml", ".yaml")):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                        for pattern in problematic_patterns:
                            if pattern in content:
                                print(f"⚠️ WARNING: Token pattern found in {filepath}")
                                print(f"   Please remove '{pattern}' from this file")
                except:
                    pass

class AutoGitHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.is_directory:
            return
        
        # Ignore git internal files
        if ".git" in event.src_path or "COMMIT_EDITMSG" in event.src_path:
            return
        
        # Wait for file write to complete
        time.sleep(0.5)
        
        filename = os.path.basename(event.src_path)
        print(f"\n🔄 Change detected: {filename}")
        
        # Add changes
        run_git_command(["git", "add", "."], REPO_PATH)
        
        # Commit changes
        commit_msg = f"Auto: {filename} updated"
        result = run_git_command(["git", "commit", "-m", commit_msg], REPO_PATH)
        
        if result and result.stderr:
            if "nothing to commit" in result.stderr:
                print("📝 No changes to commit")
                return
            elif is_harmful_error(result.stderr):
                print(f"ℹ️ {result.stderr.split(chr(10))[0]}")
        
        # Push changes
        if push_with_retry():
            print("✅ Changes pushed to GitHub\n")
        else:
            print("⚠️ Push failed, but continuing to watch...\n")

# ========== MAIN EXECUTION ==========
if __name__ == "__main__":
    print("=" * 50)
    print("🚀 Auto Git Push Script")
    print("=" * 50)
    
    # Initial setup
    initial_setup()
    
    # Warn about tokens
    ensure_no_tokens_in_files()
    
    # Sync with remote
    sync_with_remote()
    
    # Initial push of all files
    print("\n📤 Initial push of existing files...")
    run_git_command(["git", "add", "."], REPO_PATH)
    run_git_command(["git", "commit", "-m", "Initial commit"], REPO_PATH)
    
    if not push_with_retry():
        print("\n⚠️ If push keeps failing, visit:")
        print("   https://github.com/Adnan-1234/Fine-Tunning/settings/security_analysis")
        print("   And allow the detected secret or remove it from your code\n")
    
    # Start file watcher
    observer = Observer()
    observer.schedule(AutoGitHandler(), REPO_PATH, recursive=True)
    observer.start()
    
    print("\n" + "=" * 50)
    print(f"🎯 Watching: {REPO_PATH}")
    print("📁 Auto-push active on branch: main")
    print("🛑 Press Ctrl+C to stop")
    print("=" * 50 + "\n")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Stopping watcher...")
        observer.stop()
    observer.join()
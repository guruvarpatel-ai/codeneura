import threading
import subprocess
import stat
import argparse
import os
import sys
from brain_parser.codebase_walker import walk_codebase, save_brain
from brain_parser.file_watcher import start_watching
from brain_parser.graph_builder import build_graph, visualize_interactive
from brain_parser.query_engine import ask_brain
import io

# Force UTF-8 output regardless of parent process encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import argparse
import os
# ... rest of your existing imports

def cmd_start(path):
    print(" Codeneura starting...")
    print(f" Reading codebase at: {path}")
    brain = walk_codebase(path)
    save_brain(brain)
    print(f"Brain built: {len(brain)} files analyzed")

    print(" Building dependency graph...")
    G = build_graph(brain)
    visualize_interactive(G)
    print("Graph ready: brain_map.html")

    print("\n Scanning for bugs...")
    from brain_parser.bug_detector import run_all_detectors
    bugs = run_all_detectors(brain, G)
    if bugs:
        print(f"\n Found {len(bugs)} potential bugs:\n")
        for bug in bugs:
            print(f"  [{bug['severity']}] {bug['type'].replace('_', ' ').upper()}")
            print(f"  {bug['message']}")
            print(f"  Fix: {bug['fix']}\n")
    else:
        print(" No bugs detected. Codebase looks clean.\n")

    print("Starting live file watcher...")
    watcher_thread = threading.Thread(
        target=start_watching,
        args=(path,),
        daemon=True
    )
    watcher_thread.start()
    print("Watching for changes...")

    print("\n Brain is live. Ask anything.")
    print("Type 'exit' to stop query mode.")
    print("Press CTRL+C anytime to shut down completely.\n")
    while True:
        question = input("Ask your brain: ")
        if question == "exit":
            print("Brain shutting down.")
            break
        answer = ask_brain(question)
        print(f"\nBrain: {answer}\n")


def _explain_risk(staged_files, G, risk, brain):
    from brain_parser.llm_router import call_llm

    context = ""
    for f in staged_files:
        target_norm = os.path.abspath(f).replace('\\', '/')
        matched = None
        for node in G.nodes():
            node_norm = os.path.abspath(node).replace('\\', '/')
            if node_norm == target_norm:
                matched = node
                break
        if not matched:
            continue

        file_risk = risk.get(matched, 'LOW')
        if file_risk != 'HIGH':
            continue

        direct = list(G.predecessors(matched))
        file_data = brain.get(matched, {})
        functions = [fn['name'] for fn in file_data.get('functions', [])]

        context += f"\nFile: {f}\n"
        context += f"Risk: {file_risk}\n"
        context += f"Functions in this file: {functions}\n"
        context += f"Files that depend on it: {direct}\n"

    prompt = f"""A developer is about to commit changes to a HIGH risk file.
Given this context:
{context}

In 2-3 sentences, explain in plain English:
1. Why this file is risky to change
2. What could realistically break if the change is wrong
3. What the developer should double check before committing

Be direct and specific. No generic advice."""

    try:
        return call_llm(prompt, max_tokens=200)
    except Exception as e:
        return f"Could not generate explanation: {str(e)}"


def _print_impact(G, risk, filepath, clean):
    from brain_parser.graph_builder import get_impact

    result = get_impact(G, filepath)

    if not result:
        print(f"File not found in brain: {filepath}")
        return None

    file_risk = risk.get(result['target'], 'LOW')

    print(f"\n Change Impact: {filepath}")
    print(f"   Risk Level: {file_risk}\n")
    print(f"DIRECT IMPACT ({len(result['direct'])} files):")
    for f in result['direct']:
        print(f"  → {clean(f)}")
    print(f"\nINDIRECT IMPACT ({len(result['indirect'])} files):")
    for f in result['indirect']:
        print(f"  → {clean(f)}")
    print(f"\nTotal files affected: {result['total_affected']}\n")

    return {'risk': file_risk, 'total': result['total_affected']}


def cmd_impact(filepath=None, staged=False, block=False):
    from brain_parser.codebase_walker import load_brain
    from brain_parser.graph_builder import build_graph, get_impact, calculate_risk

    brain = load_brain()
    if not brain:
        print("No brain found. Run 'brain start' first.")
        return

    G = build_graph(brain)
    risk = calculate_risk(G)

    root = os.path.abspath('.').replace('\\', '/')
    def clean(path):
        return path.replace('\\', '/').replace(root + '/', '')

    if staged:
        result = subprocess.run(
            ["git", "diff", "--name-only", "--cached"],
            capture_output=True, text=True
        )
        staged_files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]

        if not staged_files:
            print("No staged files found.")
            return

        print(f"\n Staged files: {', '.join(staged_files)}\n")

        high_risk_found = False
        for f in staged_files:
            print(f"{'='*50}")
            result_data = _print_impact(G, risk, f, clean)
            if result_data and result_data.get('risk') == 'HIGH':
                high_risk_found = True

        if block and high_risk_found:
            print("\n" + "=" * 50)
            print("BRAIN WARNING: HIGH RISK commit detected.")
            print("This change affects critical files.")
            print("Production incidents have originated from files like these.")

            print("\nAsking Brain to explain the risk...\n")
            explanation = _explain_risk(staged_files, G, risk, brain)
            print(explanation)

            print("\nType 'yes' to commit anyway, anything else to abort: ", end='', flush=True)
            try:
                import platform
                if platform.system() == 'Windows':
                    with open('CON', 'r') as tty:
                        confirm = tty.readline().strip().lower()
                else:
                    with open('/dev/tty', 'r') as tty:
                        confirm = tty.readline().strip().lower()
            except:
                try:
                    confirm = input().strip().lower()
                except EOFError:
                    confirm = 'yes'
            if confirm != 'yes':
                print("\nCommit blocked by Codeneura.")
                sys.exit(1)
            else:
                print("Override confirmed. Committing anyway.")
        return

    if not filepath:
        print("Provide --file or --staged.")
        return

    _print_impact(G, risk, filepath, clean)

def install_hook(repo_path="."):
    hook_dir = os.path.join(repo_path, ".git", "hooks")
    hook_path = os.path.join(hook_dir, "pre-commit")

    if not os.path.exists(hook_dir):
        print("Not a git repository. Run this inside your project folder.")
        return

    hook_script = """#!/bin/sh
    # Codeneura — Pre-commit Impact Check
    # https://github.com/guruvarpatel-ai/codeneura

    STAGED=$(git diff --name-only --cached)

    if [ -z "$STAGED" ]; then
      exit 0
    fi

    echo ""
    echo "Codeneura — Checking blast radius..."
    echo ""

    brain impact --staged --block
    EXIT_CODE=$?

    echo ""
    echo "Powered by Codeneura ("
    echo ""

    exit $EXIT_CODE
    """

    with open(hook_path, "w", newline='\n') as f:  # newline='\n' fixes Windows CRLF
        f.write(hook_script)

    os.chmod(hook_path, os.stat(hook_path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    print(f"Brain hook installed at {hook_path}")
    print("Every commit now shows blast radius automatically.")


def cmd_init():
    import os
    print("Initializing Codeneura...\n")

    # global config — stored once per machine
    config_dir = os.path.expanduser("~/.codeneura")
    os.makedirs(config_dir, exist_ok=True)
    config_path = os.path.join(config_dir, "config.env")

    print("Choose your LLM provider:")
    print("  1. Groq        — Free, fast. llama-3.3-70b (recommended to start)")
    print("  2. OpenAI      — Reliable, trusted by enterprises. gpt-4o-mini")
    print("  3. Anthropic   — Best reasoning. claude-3-5-haiku (your code stays private)")
    print("  4. Google      — Free tier available. gemini-1.5-flash")
    print("  5. Ollama      — 100% local, no API key, no data leaves your machine")
    print("")
    choice = input("Enter 1-5 (default 1): ").strip() or "1"

    providers = {
        "1": {
            "name": "groq",
            "key_prompt": "Groq API key (free at console.groq.com): ",
            "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
            "default_model": "llama-3.3-70b-versatile"
        },
        "2": {
            "name": "openai",
            "key_prompt": "OpenAI API key (platform.openai.com): ",
            "models": ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
            "default_model": "gpt-4o-mini"
        },
        "3": {
            "name": "anthropic",
            "key_prompt": "Anthropic API key (console.anthropic.com): ",
            "models": ["claude-3-5-haiku-20241022", "claude-3-5-sonnet-20241022"],
            "default_model": "claude-3-5-haiku-20241022"
        },
        "4": {
            "name": "google",
            "key_prompt": "Google API key (aistudio.google.com): ",
            "models": ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"],
            "default_model": "gemini-1.5-flash"
        },
        "5": {
            "name": "ollama",
            "key_prompt": None,
            "models": ["llama3.2", "codellama", "deepseek-coder"],
            "default_model": "llama3.2"
        }
    }

    if choice not in providers:
        choice = "1"

    provider = providers[choice]

    if provider["key_prompt"]:
        api_key = input(provider["key_prompt"]).strip()
    else:
        api_key = "ollama"
        print("Ollama selected — make sure Ollama is running at http://localhost:11434")

    print(f"\nAvailable models for {provider['name']}:")
    for i, m in enumerate(provider["models"], 1):
        default_tag = " (default)" if m == provider["default_model"] else ""
        print(f"  {i}. {m}{default_tag}")

    model_choice = input("\nEnter model number (press Enter for default): ").strip()
    if model_choice and model_choice.isdigit():
        idx = int(model_choice) - 1
        if 0 <= idx < len(provider["models"]):
            model = provider["models"][idx]
        else:
            model = provider["default_model"]
    else:
        model = provider["default_model"]

    # save globally — one time setup
    with open(config_path, "w") as f:
        f.write(f"LLM_PROVIDER={provider['name']}\n")
        f.write(f"LLM_API_KEY={api_key}\n")
        f.write(f"LLM_MODEL={model}\n")
        f.write(f"GROQ_API_KEY={api_key}\n")
        f.write(f"GROQ_MODEL={model}\n")

    print(f"\nBrain initialized globally — {provider['name']} / {model}")
    print("Run 'brain start' in any project to begin.\n")

def cmd_rootcause(error_text=None):
    from brain_parser.root_cause import find_root_cause

    if not error_text:
        print("Paste your error/stacktrace below.")
        print("Press Enter twice when done.\n")
        lines = []
        while True:
            line = input()
            if line == "" and lines and lines[-1] == "":
                break
            lines.append(line)
        error_text = "\n".join(lines)

    print(find_root_cause(error_text))
def cmd_uninstall():
    import shutil

    print("Uninstalling Codeneura...\n")

    # remove global config
    config_dir = os.path.expanduser("~/.codeneura")
    if os.path.exists(config_dir):
        shutil.rmtree(config_dir)
        print("Removed global config.")

    # remove local brain.json
    brain_json = os.path.join(os.getcwd(), 'brain.json')
    if os.path.exists(brain_json):
        os.remove(brain_json)
        print("Removed brain.json.")

    # remove local brain_map.html
    brain_map = os.path.join(os.getcwd(), 'brain_map.html')
    if os.path.exists(brain_map):
        os.remove(brain_map)
        print("Removed brain_map.html.")

    # remove git hook
    hook_path = os.path.join(os.getcwd(), '.git', 'hooks', 'pre-commit')
    if os.path.exists(hook_path):
        # only remove if it's a Brain hook
        with open(hook_path, 'r') as f:
            content = f.read()
        if 'Codeneura' in content:
            os.remove(hook_path)
            print("Removed git hook.")

    print("\nCodeneura removed from this project.")
    print("To fully uninstall: pip uninstall codeneura")


def main():
    parser = argparse.ArgumentParser(
        description="Codeneura - Know what you'll break — before you break it."
    )
    # ← "install-hook" added here
    parser.add_argument("--path", default=".", help="Path to codebase")
    parser.add_argument("--file", default="", help="File to analyze impact")
    parser.add_argument("--staged", action="store_true", help="Analyze all staged files")
    parser.add_argument("command", choices=["start", "init", "impact", "install-hook", "rootcause", "uninstall"])
    parser.add_argument("--error", default="", help="Stacktrace to analyze")
    parser.add_argument("--block", action="store_true", help="Block HIGH risk commits")
 
    # ← new
    args = parser.parse_args()


    if args.command == "init":
        cmd_init()
    elif args.command == "rootcause":
        cmd_rootcause(args.error or None)
    elif args.command == "start":
        cmd_start(args.path)
    elif args.command == "impact":
        cmd_impact(filepath=args.file or None, staged=args.staged, block=args.block)
    elif args.command == "install-hook":
        install_hook()
    elif args.command == "uninstall":
        cmd_uninstall()




if __name__ == "__main__":
    main()
   
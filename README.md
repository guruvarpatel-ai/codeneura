<div align="center">

# Codeneura

### Know what you'll break — before you break it.

**pip install codeneura**

</div>

---

It's 11 PM. You asked Claude Code to refactor a helper function — something small, something that should've taken five minutes. It did the job, the diff looked clean, you skimmed it, it made sense, you committed.

Two days later, your on-call phone goes off. Something's broken in production. Not in the file you changed — somewhere else, three files away, in a part of the app you haven't opened in months. You spend the next four hours doing what developers have always done: `grep`, follow the imports by hand, retrace every step, until you finally land on it. The refactor. The one that looked completely reasonable in isolation.

You didn't write careless code. You just don't have the mental model anymore — the AI wrote it, you reviewed it in thirty seconds, and thirty seconds isn't enough time to hold an entire dependency graph in your head. Nobody's is. That's not a skill problem. That's a structural one, and it's getting worse the faster these tools get, not better.

This happens to every developer using Cursor, Claude Code, or Copilot right now. Most people haven't said it out loud yet, because it sounds a little paranoid. It isn't. It's just what happens when code moves faster than the human reviewing it can build intuition for it.

**Codeneura is the fix for that specific moment.**

It's a git hook — the kind that fires automatically every time you type `git commit`, before the commit actually happens. It maps your entire codebase as a dependency graph, and the second you try to commit something risky, it stops you, shows you exactly which files are affected, and — using AI — explains in plain English *why* it matters and what to actually check. Not a list of filenames. An explanation, the way a senior developer glancing over your shoulder would give you one.

If something already broke, you don't need to `grep` for four hours. You paste the stacktrace into `brain rootcause`, and Brain walks backward through the real dependency graph — the same one it built when it scanned your project — and tells you the exact file, the exact function, and why, in seconds.

This is free. Not a trial, not a limited tier designed to expire — the hook itself, the thing that actually catches you at the moment that matters, doesn't cost anything and never will. It runs on your machine, on your code, and the only thing that ever leaves your computer is what you explicitly choose to send to whichever AI provider you pick — your key, your choice, your control.

---

### We didn't just build this and hope it works. We tested it against a real bug.

Python's own core team confirmed and fixed a real `UnicodeDecodeError` in the standard library — [GitHub issue #98744](https://github.com/python/cpython/issues/98744), public, verifiable, nothing hidden.

We gave Brain nothing but the stacktrace. No hints. No prior knowledge of the fix.

```
$ brain rootcause
[pasted the real traceback from the issue]

BRAIN DIAGNOSIS
==================================================
The root cause of the error is in `_byte_offset_to_character_offset`
in traceback.py — an invalid or truncated UTF-8 byte sequence being
passed to the decode method...
```

Brain traced **1,694 files deep** into the standard library's dependency graph and landed on the **exact same function** the actual CPython maintainers identified. You can open the issue right now and check it yourself. We're not asking you to trust a claim — we're handing you the receipt.

This isn't a cherry-picked toy example. CPython is one of the most scrutinized codebases on Earth. If Brain's reasoning holds up there, it holds up on whatever you're building at 11 PM tonight.

---

### Here's what it looks like on your machine, in order

```bash
pip install Codeneura
brain init          # pick an AI provider once — Groq, OpenAI, Anthropic, Google, or fully local Ollama
brain start         # builds the dependency graph for whatever project you're standing in
brain install-hook  # wires Brain into git — this is the step that actually matters
```

After that last command, you don't do anything differently. You `git add`, you `git commit`, exactly like you always have. Brain just quietly checks the blast radius every single time, in the background, and only speaks up when it actually matters. You're not adding a habit — you're upgrading one you already have.

`brain init` runs once per machine. Every project after that just works, immediately, with the same setup.

---

### The specific moments each command is for

You're about to commit → nothing to type, Brain already fired, and if it's risky it's already asking you "are you sure?"

You want to check one file before you even touch it → `brain impact --file path/to/file.py`

Something in production just broke and you have a stacktrace → `brain rootcause`

You just joined a codebase and want the lay of the land → `brain ask "what's the riskiest file in this repo?"`

You want to actually see the shape of your project → run `brain start`, then open `brain_map.html` — red nodes are the ones to be careful with

---

### Why this matters more with every AI-generated commit, not less

Every month, more of what you ship was written faster than you can fully hold in your head. That trade — speed for situational awareness — isn't going away, and it isn't something willpower fixes. You can't force yourself to slow down and trace every diff by hand; that defeats the reason you're using these tools in the first place.

What actually works is something that holds the situational awareness *for* you, automatically, the moment it matters, without asking you to change how you work. That's the whole bet behind Codeneura: not making you more careful, but making the codebase itself tell you when to be.

---

### What this isn't

This isn't a sixty-command structural query engine with dead-code detection and architectural layer inference — if that's what you're after, there are tools built specifically for that, and they do it well.

Codeneura does one thing, on purpose: it catches you at the moment right before you commit, and it explains why, in a sentence you don't need documentation to understand.

---

**Languages:** Python, JavaScript, TypeScript, Java — more on the way.
**AI providers, your choice:** Groq (Free)· OpenAI · Anthropic · Google Gemini · Ollama (fully local, nothing leaves your machine).

```bash
brain uninstall     # removes Brain from the current project cleanly
pip uninstall codeneura
```

---

<div align="center">

Found a false positive? [Open an issue](https://github.com/guruvarpatel-ai/codeneura/issues) — every report makes the risk engine sharper for everyone using it.

</div>
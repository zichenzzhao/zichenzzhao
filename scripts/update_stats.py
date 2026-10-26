#!/usr/bin/env python3
"""
Regenerate the "By the numbers" section of the profile README from the REAL
git history of the MAP Lab repos on this machine.

Run on the Mac that holds the work repos:
    python3 scripts/update_stats.py

Outputs
  stats/stats.json         aggregate counts only (published)
  stats/languages.svg      language breakdown of tracked code (published)
  stats/activity.svg       my commits per month (published)
  README.md                block between <!-- STATS:START --> / <!-- STATS:END -->
  stats/_audit/            local evidence for reviewing README claims (gitignored,
                           never pushed: commit subjects, tree, authors)

Only counts are published -- no file contents, data, paths or commit messages.
Stdlib only; Python 3.8+.
"""
import json, os, re, subprocess, sys, datetime, collections, html

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME = os.path.expanduser("~")

# Repos to include (name -> area shown in README). Paths are auto-discovered.
REPOS = [
    ("MAPLAB_MNE", "EEG pipeline"),
    ("Synthetic_EEG_Cocaine", "Synthetic EEG"),
    ("MAPLAB_Database", "Data platform"),
    ("engineerhub", "MAPLAB Hub"),
    ("redcap-config", "REDCap config"),
    ("abcd-engine", "ABCD / ML"),
    ("aible_ABCD", "ABCD / ML"),
    ("ReMAP", "Cloud app"),
    ("maplab_web", "Lab website"),
]
# Optional manual overrides: {"MAPLAB_MNE": "/Volumes/jaxon/MAPLAB_MNE"}
PATH_OVERRIDES_FILE = os.path.join(ROOT, "stats", "repo_paths.json")
SEARCH_ROOTS = [os.path.join(HOME, "Desktop"), os.path.join(HOME, "Documents"),
                HOME, os.path.join(HOME, "Projects"), os.path.join(HOME, "code")]
# Code I did not write (colleague-supplied or vendored). Excluded from every
# line count and from commit line totals, even when I committed it.
VENDORED = {
    "MAPLAB_MNE": [r"^tarik/", r"^MAPLAB_SOURCE/eegsource_toolkit/"],
    "abcd-engine": [r"Substance Use Onset Censoring"],
    "ReMAP": [r"\.tf$", r"\.tfvars$", r"\.tfstate$"],
}
# Housekeeping commits that sync repos between my two GitHub accounts.
MIRROR = re.compile(r"mirror", re.I)
# Commits whose author name/email matches this count as mine.
ME = re.compile(r"zichen|zz3119|jaxon|jackson|zichenzha0|zichenzzhao", re.I)

EXCLUDE_DIRS = re.compile(
    r"(^|/)(node_modules|\.next|dist|build|out|outputs?|data|golden|venv[^/]*|\.venv|"
    r"__pycache__|\.ipynb_checkpoints|vendor|coverage|\.git|"
    # backups / archived copies, static asset dumps, generated public copies
    r"archived?|archives|backups?|[^/]*_backup[^/]*|assets?|public|static|wp-content|wp-includes)(/|$)", re.I)
EXCLUDE_FILES = re.compile(
    r"(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|poetry\.lock|\.min\.(js|css)$|"
    r"\.(csv|tsv|xlsx?|parquet|feather|rds|sav|edf|vhdr|vmrk|eeg|fif|set|fdt|mat|npy|npz|"
    r"pkl|h5|png|jpe?g|gif|svg|pdf|docx?|pptx?|zip|gz|ico|woff2?|ttf|map|log)$)", re.I)
LANG = {
    ".py": "Python", ".ipynb": "Jupyter", ".r": "R", ".rmd": "R", ".sql": "SQL",
    ".ts": "TypeScript", ".tsx": "TypeScript", ".js": "JavaScript", ".jsx": "JavaScript",
    ".mjs": "JavaScript", ".cjs": "JavaScript", ".css": "CSS", ".scss": "CSS",
    ".html": "HTML", ".sh": "Shell", ".zsh": "Shell", ".m": "MATLAB",
    ".yml": "YAML", ".yaml": "YAML", ".toml": "Config", ".ini": "Config", ".cfg": "Config",
    ".md": "Markdown", ".prisma": "Prisma", ".dockerfile": "Docker",
}
NON_CODE = {"Markdown", "YAML", "Config"}  # counted separately from code
COLORS = {"Python": "#3776AB", "TypeScript": "#3178C6", "JavaScript": "#F7DF1E",
          "SQL": "#03d8f3", "R": "#a78bfa", "Jupyter": "#F37626", "CSS": "#ff0055",
          "HTML": "#E34F26", "Shell": "#00ffc8", "MATLAB": "#ff8a00", "Prisma": "#c084fc",
          "Docker": "#2496ED", "Other": "#9ca3af"}


def git(repo, *args):
    r = subprocess.run(["git", "-C", repo] + list(args), capture_output=True, text=True,
                       errors="replace")
    return r.stdout if r.returncode == 0 else ""


def discover():
    overrides = {}
    if os.path.exists(PATH_OVERRIDES_FILE):
        overrides = json.load(open(PATH_OVERRIDES_FILE))
    wanted = {n.lower(): n for n, _ in REPOS}
    found = collections.defaultdict(list)
    for base in SEARCH_ROOTS:
        if not os.path.isdir(base):
            continue
        base_depth = base.rstrip("/").count("/")
        for dirpath, dirnames, _ in os.walk(base):
            depth = dirpath.count("/") - base_depth
            dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in
                           ("Library", "node_modules", "miniforge3", "Applications")]
            if depth >= 3:
                dirnames[:] = []
            name = os.path.basename(dirpath).lower()
            if name in wanted and os.path.isdir(os.path.join(dirpath, ".git")):
                found[wanted[name]].append(dirpath)
    paths = {}
    for name, _ in REPOS:
        if name in overrides:
            paths[name] = os.path.expanduser(overrides[name]); continue
        cands = sorted(set(found.get(name, [])))
        if not cands:
            continue
        # pick the clone with the most recent commit
        cands.sort(key=lambda p: int(git(p, "log", "-1", "--format=%ct", "--all").strip() or 0))
        paths[name] = cands[-1]
    return paths


def code_lang(path, repo_name=None):
    if EXCLUDE_DIRS.search(path) or EXCLUDE_FILES.search(path):
        return None
    if repo_name and any(re.search(v, path) for v in VENDORED.get(repo_name, [])):
        return None
    base = os.path.basename(path).lower()
    if base == "dockerfile":
        return "Docker"
    return LANG.get(os.path.splitext(base)[1])


GENERATED = re.compile(r"auto-?generated|@generated|do not edit|generated by|this file is generated", re.I)


def generated_paths(repo, name):
    """Tracked code files that declare themselves generated (header) -- not hand-written."""
    out = set()
    for f in git(repo, "ls-files").splitlines():
        if not code_lang(f, name):
            continue
        try:
            with open(os.path.join(repo, f), errors="ignore") as fh:
                head = "".join(fh.readline() for _ in range(12))
        except OSError:
            continue
        if GENERATED.search(head):
            out.add(f)
    return out


def analyze(name, repo):
    gen = generated_paths(repo, name)
    info = {"repo": name}
    log = git(repo, "log", "--all", "--no-merges", "--date=short", "--numstat",
              "--format=@@%H\t%ad\t%an\t%ae")
    subjects = {}
    for l in git(repo, "log", "--all", "--no-merges", "--format=%H\t%s").splitlines():
        if "\t" in l:
            h, sub = l.split("\t", 1); subjects[h] = sub
    commits, authors = {}, collections.Counter()
    cur = None
    for line in log.splitlines():
        if line.startswith("@@"):
            h, d, an, ae = line[2:].split("\t", 3)
            cur = {"date": d, "mine": bool(ME.search(an) or ME.search(ae)), "add": 0, "del": 0,
                   "files": [], "subject": subjects.get(h, "")}
            commits.setdefault(h, cur); cur = commits[h]
            authors["%s <%s>" % (an, ae)] += 1
        elif line.strip() and cur is not None:
            parts = line.split("\t")
            if len(parts) != 3:
                continue
            cur["files"].append(parts[2])
            lang = code_lang(parts[2], name)
            if parts[0] != "-" and lang and lang not in NON_CODE and lang != "Jupyter" \
                    and parts[2] not in gen:
                cur["add"] += int(parts[0]); cur["del"] += int(parts[1])
    skipped = [h for h, c in commits.items() if MIRROR.search(c["subject"]) and
               all(f.startswith(".github/") for f in c["files"])]
    for h in skipped:
        del commits[h]
    info["mirror_commits_skipped"] = len(skipped)
    info["_biggest_commits"] = sorted(([c["add"], c["del"], c["date"], c["subject"][:80], len(c["files"])]
                                       for c in commits.values() if c["mine"]), reverse=True)[:12]
    info["generated_excluded"] = sorted(gen)
    mine = [c for c in commits.values() if c["mine"]]
    dates = sorted(c["date"] for c in mine)
    info.update({
        "commits_total": len(commits), "commits_mine": len(mine),
        "lines_added_mine": sum(c["add"] for c in mine),
        "lines_deleted_mine": sum(c["del"] for c in mine),
        "active_days_mine": len(set(dates)),
        "first_commit": dates[0] if dates else None,
        "last_commit": dates[-1] if dates else None,
        "monthly_mine": dict(collections.Counter(d[:7] for d in dates)),
    })
    # current code at HEAD
    langs = collections.Counter(); files = 0; tests = 0; migrations = 0; sizes = []
    notebook_only = True
    for f in git(repo, "ls-files").splitlines():
        lang = code_lang(f, name)
        if not lang or f in gen:
            continue
        p = os.path.join(repo, f)
        try:
            if lang == "Jupyter":
                nb = json.load(open(p, errors="ignore"))
                n = sum(1 for c in nb.get("cells", []) if c.get("cell_type") == "code"
                        for l in (c.get("source") if isinstance(c.get("source"), list)
                                  else str(c.get("source", "")).splitlines()) if str(l).strip())
            else:
                if os.path.getsize(p) > 1_500_000:
                    continue
                with open(p, errors="ignore") as fh:
                    n = sum(1 for l in fh if l.strip())
        except (OSError, ValueError):
            continue
        langs[lang] += n
        if lang not in NON_CODE:
            files += 1
            sizes.append((n, f))
            if lang != "Jupyter":
                notebook_only = False
        b = os.path.basename(f).lower()
        if re.match(r"(test_.*\.py|.*_test\.py|.*\.(test|spec)\.[jt]sx?)$", b):
            tests += 1
        if lang == "SQL" and re.search(r"migrations?/", f, re.I):
            migrations += 1
    info.update({
        "code_lines_head": sum(v for k, v in langs.items() if k not in NON_CODE),
        "doc_config_lines_head": sum(v for k, v in langs.items() if k in NON_CODE),
        "code_files_head": files, "test_files": tests, "sql_migrations": migrations,
        "languages": dict(langs.most_common()),
        "vendored_excluded": VENDORED.get(name, []),
        "notebook_only": notebook_only and files > 0,
        "_largest_files": [[n, f] for n, f in sorted(sizes, reverse=True)[:25]],
        "tags": [t for t in git(repo, "tag", "--sort=creatordate").split() if t][-15:],
        "branches": len([b for b in git(repo, "branch", "-a").splitlines() if "->" not in b]),
    })
    return info, authors, commits


def write_audit(name, repo, info, authors):
    d = os.path.join(ROOT, "stats", "_audit"); os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, name + ".md"), "w") as f:
        f.write("# %s\n\npath: %s\n\n```json\n%s\n```\n\n" % (name, repo, json.dumps(info, indent=2)))
        f.write("## largest counted files at HEAD (lines, path)\n```\n" + "".join("%7d %s\n" % (n, p) for n, p in info.get("_largest_files", [])) + "```\n\n")
        f.write("## biggest commits of mine (added, deleted, date, subject, files)\n```\n" + "".join("%7d %7d %s %s (%d files)\n" % tuple(c[:2] + [c[2], c[3], c[4]]) for c in info.get("_biggest_commits", [])) + "```\n\n")
        f.write("## authors (all branches)\n" + "".join("- %d  %s\n" % (n, a) for a, n in authors.most_common()))
        f.write("\n## last 400 commit subjects (all authors)\n```\n")
        f.write(git(repo, "log", "--all", "--no-merges", "-n", "400", "--date=short",
                    "--format=%ad %an | %s").strip()[:40000])
        f.write("\n```\n\n## top-level tree\n```\n" + git(repo, "ls-tree", "--name-only", "HEAD") + "```\n")
        f.write("\n## tracked dirs (depth 2, file counts)\n```\n")
        c = collections.Counter("/".join(p.split("/")[:2]) for p in git(repo, "ls-files").splitlines() if "/" in p)
        f.write("".join("%5d %s\n" % (n, p) for p, n in c.most_common(80)) + "```\n")
        f.write("\n## README head\n```\n")
        for cand in ("README.md", "readme.md", "README.MD"):
            p = os.path.join(repo, cand)
            if os.path.exists(p):
                f.write(open(p, errors="ignore").read()[:6000]); break
        f.write("\n```\n")


def bar_svg(title, items, total_label, width=880):
    """Horizontal stacked bar + legend, neon card."""
    total = sum(v for _, v in items) or 1
    h = 112 + 22 * ((len(items) + 2) // 3)
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" font-family="Segoe UI,Helvetica,Arial,sans-serif">' % (width, h, width, h),
           '<rect x="0.5" y="0.5" width="%d" height="%d" rx="12" fill="#141321" stroke="#03d8f3" stroke-opacity="0.35"/>' % (width - 1, h - 1),
           '<text x="28" y="44" fill="#f9fafb" font-size="20" font-weight="600">%s</text>' % html.escape(title),
           '<text x="%d" y="44" fill="#9ca3af" font-size="14" text-anchor="end">%s</text>' % (width - 28, html.escape(total_label))]
    x, bw = 28.0, width - 56
    for k, v in items:
        w = bw * v / total
        out.append('<rect x="%.2f" y="66" width="%.2f" height="14" fill="%s"/>' % (x, max(w, 0.5), COLORS.get(k, COLORS["Other"])))
        x += w
    for i, (k, v) in enumerate(items):
        cx, cy = 28 + (i % 3) * ((width - 56) / 3), 112 + 22 * (i // 3)
        out.append('<circle cx="%.1f" cy="%d" r="5" fill="%s"/>' % (cx + 5, cy - 4, COLORS.get(k, COLORS["Other"])))
        out.append('<text x="%.1f" y="%d" fill="#e5e7eb" font-size="14">%s <tspan fill="#9ca3af">%.1f%% · %s lines</tspan></text>' % (cx + 16, cy, html.escape(k), 100.0 * v / total, format(v, ",")))
    out.append("</svg>")
    return "\n".join(out)


def activity_svg(monthly, width=880, h=220):
    if not monthly:
        return None
    first = datetime.date(int(min(monthly)[:4]), int(min(monthly)[5:]), 1)
    today = datetime.date.today(); months = []
    y, m = first.year, first.month
    while (y, m) <= (today.year, today.month):
        months.append("%04d-%02d" % (y, m)); m += 1
        if m > 12: y, m = y + 1, 1
    mx = max(monthly.values()) or 1
    left, right, top, bottom = 48, 28, 64, 40
    pw = (width - left - right) / len(months); ph = h - top - bottom
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" font-family="Segoe UI,Helvetica,Arial,sans-serif">' % (width, h, width, h),
           '<rect x="0.5" y="0.5" width="%d" height="%d" rx="12" fill="#141321" stroke="#03d8f3" stroke-opacity="0.35"/>' % (width - 1, h - 1),
           '<text x="28" y="40" fill="#f9fafb" font-size="20" font-weight="600">My commits per month · MAP Lab repos</text>',
           '<text x="%d" y="40" fill="#9ca3af" font-size="14" text-anchor="end">%s commits</text>' % (width - 28, format(sum(monthly.values()), ","))]
    for i, mo in enumerate(months):
        v = monthly.get(mo, 0); bh = ph * v / mx
        x = left + i * pw
        out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="3" fill="url(#g)"><title>%s: %d</title></rect>' % (x + pw * 0.15, top + ph - bh, pw * 0.7, max(bh, 1 if v else 0), mo, v))
        if v:
            out.append('<text x="%.1f" y="%.1f" fill="#e5e7eb" font-size="11" text-anchor="middle">%d</text>' % (x + pw / 2, top + ph - bh - 5, v))
        if len(months) <= 18 or i % 2 == 0:
            label = datetime.date(int(mo[:4]), int(mo[5:]), 1).strftime("%b %y")
            out.append('<text x="%.1f" y="%d" fill="#9ca3af" font-size="11" text-anchor="middle">%s</text>' % (x + pw / 2, h - 16, label))
    out.insert(1, '<defs><linearGradient id="g" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#03d8f3"/><stop offset="1" stop-color="#ff0055"/></linearGradient></defs>')
    out.append("</svg>")
    return "\n".join(out)


def fmt(n):
    return format(n, ",")


def main():
    paths = discover()
    missing = [n for n, _ in REPOS if n not in paths]
    area = dict(REPOS)
    results, monthly, langs = [], collections.Counter(), collections.Counter()
    for name, _ in REPOS:
        if name not in paths:
            continue
        info, authors, _ = analyze(name, paths[name])
        info["area"] = area[name]
        write_audit(name, paths[name], info, authors)
        results.append(info)
        monthly.update(info["monthly_mine"])
        langs.update({k: v for k, v in info["languages"].items() if k not in NON_CODE})
        print("%-22s %-45s mine=%d/%d commits" % (name, paths[name], info["commits_mine"], info["commits_total"]))
    if missing:
        print("\nNOT FOUND (add paths to stats/repo_paths.json):", ", ".join(missing))
    today = datetime.date.today().isoformat()
    tot = {
        "repos": len(results),
        "commits_mine": sum(r["commits_mine"] for r in results),
        "lines_added_mine": sum(r["lines_added_mine"] for r in results),
        "lines_deleted_mine": sum(r["lines_deleted_mine"] for r in results),
        "code_lines_head": sum(r["code_lines_head"] for r in results),
        "first_commit": min([r["first_commit"] for r in results if r["first_commit"]] or [None]),
        "last_commit": max([r["last_commit"] for r in results if r["last_commit"]] or [None]),
    }
    public = {"generated": today, "totals": tot,
              "repos": [{k: r[k] for k in ("repo", "area", "commits_mine", "lines_added_mine",
                                           "lines_deleted_mine", "code_lines_head", "code_files_head",
                                           "test_files", "sql_migrations", "first_commit", "last_commit",
                                           "languages", "tags")} for r in results],
              "monthly_commits_mine": dict(sorted(monthly.items())),
              "missing": missing}
    os.makedirs(os.path.join(ROOT, "stats"), exist_ok=True)
    json.dump(public, open(os.path.join(ROOT, "stats", "stats.json"), "w"), indent=2)

    top = langs.most_common(7)
    rest = sum(langs.values()) - sum(v for _, v in top)
    if rest > 0:
        top.append(("Other", rest))
    open(os.path.join(ROOT, "stats", "languages.svg"), "w").write(
        bar_svg("Code by language · MAP Lab repos (current HEAD)", top, "%s lines of code" % fmt(sum(langs.values()))))
    a = activity_svg(dict(monthly))
    if a:
        open(os.path.join(ROOT, "stats", "activity.svg"), "w").write(a)

    rows = ["| Repo | Area | My commits | Lines I added / removed | Code at HEAD | Active |",
            "|---|---|--:|--:|--:|---|"]
    for r in sorted(results, key=lambda r: -r["commits_mine"]):
        span = "%s → %s" % (r["first_commit"][:7], r["last_commit"][:7]) if r["first_commit"] else "–"
        churn = ("notebooks¹" if r.get("notebook_only") else
                 "+%s / −%s" % (fmt(r["lines_added_mine"]), fmt(r["lines_deleted_mine"])))
        rows.append("| `%s` | %s | %s | %s | %s | %s |" % (
            r["repo"], r["area"], fmt(r["commits_mine"]), churn, fmt(r["code_lines_head"]), span))
    block = "\n".join([
        "<!-- STATS:START -->",
        "<p align=\"center\">",
        "  <img src=\"https://img.shields.io/badge/My%%20commits-%s-03d8f3?style=for-the-badge\" alt=\"My commits\" />" % fmt(tot["commits_mine"]).replace(",", "%2C"),
        "  <img src=\"https://img.shields.io/badge/Lines%%20added-%s-ff0055?style=for-the-badge\" alt=\"Lines added\" />" % fmt(tot["lines_added_mine"]).replace(",", "%2C"),
        "  <img src=\"https://img.shields.io/badge/Code%%20maintained-%s%%20lines-fcee0c?style=for-the-badge&labelColor=141321\" alt=\"Code maintained\" />" % fmt(tot["code_lines_head"]).replace(",", "%2C"),
        "  <img src=\"https://img.shields.io/badge/Repos-%d-00ffc8?style=for-the-badge&labelColor=141321\" alt=\"Repos\" />" % tot["repos"],
        "</p>",
        "",
        "<p align=\"center\"><img src=\"./stats/activity.svg\" width=\"100%\" alt=\"My commits per month\" /></p>",
        "<p align=\"center\"><img src=\"./stats/languages.svg\" width=\"100%\" alt=\"Code by language\" /></p>",
        "",
    ] + rows + [
        "",
        "<sub>Computed from local git history on %s by <a href=\"./scripts/update_stats.py\"><code>scripts/update_stats.py</code></a>: "
        "my non-merge commits across all branches, excluding account-mirroring housekeeping. "
        "¹ Notebook repos show code-cell lines at HEAD only; notebook diffs are not counted. "
        "Line counts are source code I wrote: data, outputs, docs, config, lockfiles, images, notebook outputs, and code supplied by colleagues "
        "(e.g. a collaborator's source-analysis toolkit, vendored infrastructure templates) and files that declare themselves generated are excluded. Repos are private, so these are the numbers behind them.</sub>" % today,
        "<!-- STATS:END -->"])
    rp = os.path.join(ROOT, "README.md"); s = open(rp).read()
    if "<!-- STATS:START -->" in s:
        s = re.sub(r"<!-- STATS:START -->.*?<!-- STATS:END -->", lambda _: block, s, flags=re.S)
    else:
        s = s.replace("## Activity", "## By the Numbers 📈\n\n" + block + "\n\n## Activity", 1)
    s = re.sub(r"<sub>Last updated: [^<]*</sub>", "<sub>Last updated: %s</sub>" % datetime.date.today().strftime("%B %Y"), s)
    open(rp, "w").write(s)
    print("\nTotals:", json.dumps(tot))
    print("Wrote stats/stats.json, stats/*.svg, README.md; audit in stats/_audit/ (not pushed)")


if __name__ == "__main__":
    main()

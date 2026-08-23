import os
import re
import sys
from collections import defaultdict

def scan_repo(repo_dir=None):
    if repo_dir is None:
        repo_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    
    skip_dirs = {".git", "node_modules", "__pycache__", ".venv", "env", ".env", "dist", "build", "coverage"}
    skip_files = {"haloerp_migration_scan.py", "migrate_erpnext_to_haloerp.py"}

    pattern = re.compile(r"(erpnext|ERPNext|ERP_NEXT|erp_next|/assets/erpnext)", re.IGNORECASE)
    
    # Category containers
    ext_matches = defaultdict(list)
    runtime_matches = []
    doc_matches = []
    license_matches = []
    
    for root, dirs, files in os.walk(repo_dir):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for f in files:
            if f in skip_files:
                continue
            fpath = os.path.join(root, f)
            relpath = os.path.relpath(fpath, repo_dir).replace("\\", "/")
            ext = os.path.splitext(f)[1].lower() or "[no_ext]"
            
            is_doc_or_license = (
                ext in [".md", ".rst", ".txt", ".po", ".pot"] and f not in ["modules.txt", "patches.txt"]
            ) or f in ["LICENSE", "license.txt", "attributions.md", "SECURITY.md", "CODE_OF_CONDUCT.md"]
            
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as fp:
                    for lineno, line in enumerate(fp, 1):
                        if not pattern.search(line):
                            continue
                        
                        entry = {
                            "file": relpath,
                            "line": lineno,
                            "content": line.strip(),
                            "ext": ext
                        }
                        
                        ext_matches[ext].append(entry)
                        
                        # Classify potential runtime references vs doc/license
                        if is_doc_or_license:
                            if "license" in f.lower() or "copyright" in line.lower() or "author" in line.lower():
                                license_matches.append(entry)
                            else:
                                doc_matches.append(entry)
                        else:
                            # Code / config / data
                            runtime_matches.append(entry)
            except Exception:
                pass

    print("=" * 60)
    print("HALOERP MIGRATION SCAN")
    print("=" * 60)
    
    # Extension groupings
    display_groups = [
        ("Python files (.py)", ext_matches.get(".py", [])),
        ("JavaScript (.js)", ext_matches.get(".js", [])),
        ("TypeScript (.ts, .tsx)", ext_matches.get(".ts", []) + ext_matches.get(".tsx", [])),
        ("Vue (.vue)", ext_matches.get(".vue", [])),
        ("JSON (.json)", ext_matches.get(".json", [])),
        ("YAML (.yml, .yaml)", ext_matches.get(".yml", []) + ext_matches.get(".yaml", [])),
        ("TOML / Config (.toml, .ini, .cfg)", ext_matches.get(".toml", []) + ext_matches.get(".ini", []) + ext_matches.get(".cfg", [])),
        ("HTML / Templates (.html)", ext_matches.get(".html", [])),
        ("CSS / SCSS (.css, .scss)", ext_matches.get(".css", []) + ext_matches.get(".scss", [])),
        ("Translations (.po, .pot, .csv)", ext_matches.get(".po", []) + ext_matches.get(".pot", []) + ext_matches.get(".csv", [])),
        ("Documentation / Markdown (.md, .rst, .txt)", [m for m in (ext_matches.get(".md", []) + ext_matches.get(".rst", []) + ext_matches.get(".txt", [])) if m["file"] not in ["modules.txt", "patches.txt"]]),
    ]
    
    for title, group in display_groups:
        print(f"\n{title}:")
        print(f"  {len(group)} remaining references")
    
    print("\n" + "=" * 60)
    print("POTENTIAL RUNTIME REFERENCES")
    print("=" * 60)
    
    if not runtime_matches:
        print("  None detected! Zero unintended runtime references found.")
    else:
        print(f"  Total potential runtime references: {len(runtime_matches)}")
        for match in runtime_matches[:50]:
            print(f"  {match['file']}:{match['line']} -> {match['content'][:100]}")
        if len(runtime_matches) > 50:
            print(f"  ... and {len(runtime_matches) - 50} more runtime references.")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    total_refs = sum(len(v) for v in ext_matches.values())
    print(f"Total references found: {total_refs}")
    print(f"Runtime / Configuration: {len(runtime_matches)}")
    print(f"Documentation / Translations / Licenses: {len(doc_matches) + len(license_matches)}")
    print("=" * 60)
    
    return {
        "total": total_refs,
        "runtime_count": len(runtime_matches),
        "doc_count": len(doc_matches),
        "license_count": len(license_matches),
        "ext_matches": ext_matches,
        "runtime_matches": runtime_matches
    }

if __name__ == "__main__":
    scan_repo()

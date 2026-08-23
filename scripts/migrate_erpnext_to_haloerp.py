#!/usr/bin/env python3
"""
HaloERP Migration Script
Transforms ERPNext codebase into HaloERP standalone ERP application.
Supports --dry-run and live execution.
"""

import argparse
import os
import re
import shutil
import sys
from pathlib import Path

def parse_args():
    parser = argparse.ArgumentParser(description="Migrate ERPNext to HaloERP")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the migration without modifying files or directories",
    )
    return parser.parse_args()

class HaloERPMigrator:
    def __init__(self, repo_dir: Path, dry_run: bool = False):
        self.repo_dir = repo_dir
        self.dry_run = dry_run
        self.stats = {
            "dirs_renamed": 0,
            "files_renamed": 0,
            "files_transformed": 0,
            "python_imports_changed": 0,
            "js_refs_changed": 0,
            "json_refs_changed": 0,
            "metadata_changed": 0,
            "hooks_changed": 0,
        }
        self.skip_dirs = {
            ".git", "node_modules", "__pycache__", ".venv", "env", ".env", "dist", "build", "coverage"
        }

    def log(self, message: str):
        prefix = "[DRY-RUN] " if self.dry_run else ""
        print(f"{prefix}{message}")

    def run(self):
        self.log("=" * 60)
        self.log("STARTING HALOERP MIGRATION")
        self.log(f"Target repository: {self.repo_dir}")
        self.log(f"Mode: {'DRY-RUN (no disk writes)' if self.dry_run else 'LIVE MIGRATION'}")
        self.log("=" * 60)

        # 1. Rename application directory and specific subfolders
        self.step_1_rename_directories()

        # 2. Rename specific files (assets, bundles, desktop icons, workspaces)
        self.step_2_rename_specific_files()

        # 3. Transform file contents
        self.step_3_transform_file_contents()

        # 4. Transform package and app metadata
        self.step_4_transform_metadata()

        # 5. Summary
        self.log("=" * 60)
        self.log("MIGRATION EXECUTION COMPLETED")
        self.log(f"Directories renamed : {self.stats['dirs_renamed']}")
        self.log(f"Files renamed       : {self.stats['files_renamed']}")
        self.log(f"Files transformed   : {self.stats['files_transformed']}")
        self.log(f"Python imports      : {self.stats['python_imports_changed']}")
        self.log(f"JS/TS references    : {self.stats['js_refs_changed']}")
        self.log(f"JSON references     : {self.stats['json_refs_changed']}")
        self.log("=" * 60)

    def step_1_rename_directories(self):
        self.log("\n[Step 1] Renaming Application Directories...")
        
        # Primary app directory: erpnext -> haloerp
        erpnext_dir = self.repo_dir / "erpnext"
        haloerp_dir = self.repo_dir / "haloerp"
        
        if erpnext_dir.exists() and not haloerp_dir.exists():
            self.log(f"Rename directory: {erpnext_dir.relative_to(self.repo_dir)} -> {haloerp_dir.relative_to(self.repo_dir)}")
            self.stats["dirs_renamed"] += 1
            if not self.dry_run:
                erpnext_dir.rename(haloerp_dir)
        elif erpnext_dir.exists() and haloerp_dir.exists():
            self.log(f"Warning: both {erpnext_dir} and {haloerp_dir} exist. Checking contents...")
        
        target_base = haloerp_dir if (haloerp_dir.exists() or not self.dry_run) else erpnext_dir

        # Submodule rename: erpnext_integrations -> haloerp_integrations
        sub_integrations_old = target_base / "erpnext_integrations"
        sub_integrations_new = target_base / "haloerp_integrations"
        if sub_integrations_old.exists() and not sub_integrations_new.exists():
            self.log(f"Rename directory: {sub_integrations_old.relative_to(self.repo_dir)} -> {sub_integrations_new.relative_to(self.repo_dir)}")
            self.stats["dirs_renamed"] += 1
            if not self.dry_run:
                sub_integrations_old.rename(sub_integrations_new)

        # Workspace directory: setup/workspace/erpnext_settings -> haloerp_settings
        workspace_old = target_base / "setup" / "workspace" / "erpnext_settings"
        workspace_new = target_base / "setup" / "workspace" / "haloerp_settings"
        if workspace_old.exists() and not workspace_new.exists():
            self.log(f"Rename directory: {workspace_old.relative_to(self.repo_dir)} -> {workspace_new.relative_to(self.repo_dir)}")
            self.stats["dirs_renamed"] += 1
            if not self.dry_run:
                workspace_old.rename(workspace_new)

    def step_2_rename_specific_files(self):
        self.log("\n[Step 2] Renaming Application and Asset Files...")
        
        app_dir = self.repo_dir / ("haloerp" if (self.repo_dir / "haloerp").exists() or not self.dry_run else "erpnext")
        
        file_renames = [
            # Desktop icons
            (app_dir / "desktop_icon" / "erpnext.json", app_dir / "desktop_icon" / "haloerp.json"),
            (app_dir / "desktop_icon" / "erpnext_settings.json", app_dir / "desktop_icon" / "haloerp_settings.json"),
            
            # Workspace sidebars and workspace json
            (app_dir / "workspace_sidebar" / "erpnext_settings.json", app_dir / "workspace_sidebar" / "haloerp_settings.json"),
            (app_dir / "setup" / "workspace" / "haloerp_settings" / "erpnext_settings.json", app_dir / "setup" / "workspace" / "haloerp_settings" / "haloerp_settings.json"),
            (app_dir / "setup" / "workspace" / "erpnext_settings" / "erpnext_settings.json", app_dir / "setup" / "workspace" / "haloerp_settings" / "haloerp_settings.json"),
            
            # SVG & icon assets
            (app_dir / "public" / "desktop_icons" / "erpnext_settings.svg", app_dir / "public" / "desktop_icons" / "haloerp_settings.svg"),
            (app_dir / "public" / "icons" / "desktop_icons" / "solid" / "erpnext_settings.svg", app_dir / "public" / "icons" / "desktop_icons" / "solid" / "haloerp_settings.svg"),
            (app_dir / "public" / "icons" / "desktop_icons" / "subtle" / "erpnext_settings.svg", app_dir / "public" / "icons" / "desktop_icons" / "subtle" / "haloerp_settings.svg"),
            (app_dir / "public" / "images" / "erpnext-favicon.svg", app_dir / "public" / "images" / "haloerp-favicon.svg"),
            (app_dir / "public" / "images" / "erpnext-logo-blue.png", app_dir / "public" / "images" / "haloerp-logo-blue.png"),
            (app_dir / "public" / "images" / "erpnext-logo.png", app_dir / "public" / "images" / "haloerp-logo.png"),
            (app_dir / "public" / "images" / "erpnext-logo.svg", app_dir / "public" / "images" / "haloerp-logo.svg"),
            (app_dir / "public" / "images" / "erpnext-video-placeholder.jpg", app_dir / "public" / "images" / "haloerp-video-placeholder.jpg"),
            (app_dir / "public" / "images" / "v16" / "erpnext.svg", app_dir / "public" / "images" / "v16" / "haloerp.svg"),
            
            # Bundle JS / SCSS
            (app_dir / "public" / "js" / "erpnext.bundle.js", app_dir / "public" / "js" / "haloerp.bundle.js"),
            (app_dir / "public" / "scss" / "erpnext-web.bundle.scss", app_dir / "public" / "scss" / "haloerp-web.bundle.scss"),
            (app_dir / "public" / "scss" / "erpnext.bundle.scss", app_dir / "public" / "scss" / "haloerp.bundle.scss"),
            (app_dir / "public" / "scss" / "erpnext.scss", app_dir / "public" / "scss" / "haloerp.scss"),
            (app_dir / "public" / "scss" / "erpnext_email.bundle.scss", app_dir / "public" / "scss" / "haloerp_email.bundle.scss"),
        ]

        for old_path, new_path in file_renames:
            if old_path.exists():
                self.log(f"Rename file: {old_path.relative_to(self.repo_dir)} -> {new_path.relative_to(self.repo_dir)}")
                self.stats["files_renamed"] += 1
                if not self.dry_run:
                    new_path.parent.mkdir(parents=True, exist_ok=True)
                    old_path.rename(new_path)

    def step_3_transform_file_contents(self):
        self.log("\n[Step 3] Transforming File Contents across repository...")
        
        for root, dirs, files in os.walk(self.repo_dir):
            dirs[:] = [d for d in dirs if d not in self.skip_dirs]
            for f in files:
                fpath = Path(root) / f
                relpath = fpath.relative_to(self.repo_dir).as_posix()
                ext = fpath.suffix.lower()
                
                # Skip self and scanner from mutation
                if f in ["migrate_erpnext_to_haloerp.py", "haloerp_migration_scan.py"]:
                    continue
                
                # Skip license/attribution text files from content rewriting
                if f in ["license.txt", "LICENSE", "attributions.md", "SECURITY.md", "CODE_OF_CONDUCT.md"]:
                    continue
                
                if ext == ".py":
                    self.transform_python_file(fpath, relpath)
                elif ext in [".js", ".ts", ".tsx", ".vue"]:
                    self.transform_js_ts_file(fpath, relpath)
                elif ext == ".json":
                    self.transform_json_file(fpath, relpath)
                elif ext in [".html", ".css", ".scss"]:
                    self.transform_markup_style_file(fpath, relpath)
                elif ext in [".yml", ".yaml"]:
                    self.transform_yaml_file(fpath, relpath)
                elif ext == ".sh":
                    self.transform_shell_file(fpath, relpath)
                elif f in [".gitignore", ".eslintrc", ".pre-commit-config.yaml", ".releaserc", "codecov.yml", "CODEOWNERS", "crowdin.yml", "babel_extractors.csv"]:
                    self.transform_config_file(fpath, relpath)

    def transform_python_file(self, fpath: Path, relpath: str):
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as fp:
                content = fp.read()
        except Exception:
            return

        original = content
        
        # 1. Imports
        content, c1 = re.subn(r"\bfrom\s+erpnext\b", "from haloerp", content)
        content, c2 = re.subn(r"\bimport\s+erpnext\b", "import haloerp", content)
        self.stats["python_imports_changed"] += (c1 + c2)
        
        # 2. erpnext_integrations submodule
        content = re.sub(r"\berpnext_integrations\b", "haloerp_integrations", content)
        
        # 3. erpnext namespace attribute / calls: erpnext.accounts -> haloerp.accounts
        content = re.sub(r"\berpnext\.", "haloerp.", content)
        
        # 4. String references in python: "erpnext." -> "haloerp."
        content = re.sub(r"([\"'])erpnext\.", r"\1haloerp.", content)
        content = re.sub(r"([\"'])erpnext_integrations\b", r"\1haloerp_integrations", content)
        
        # 5. App name in frappe API calls:
        content = re.sub(r'frappe\.get_app_path\(\s*["\']erpnext["\']', 'frappe.get_app_path("haloerp"', content)
        content = re.sub(r'get_module_app\([^)]+\)\s*==\s*["\']erpnext["\']', 'get_module_app(module) == "haloerp"', content)
        content = re.sub(r'get_module_app\([^)]+\)\s*!=\s*["\']erpnext["\']', 'get_module_app(module) != "haloerp"', content)
        content = re.sub(r'app\s*==\s*["\']erpnext["\']', 'app == "haloerp"', content)
        content = re.sub(r'app_name\s*=\s*["\']erpnext["\']', 'app_name="haloerp"', content)
        content = re.sub(r'["\']app_name["\']:\s*["\']erpnext["\']', '"app_name": "haloerp"', content)
        content = re.sub(r'capture\(\s*["\']([^"\']+)["\'],\s*["\']erpnext["\']', r'capture("\1", "haloerp"', content)
        content = re.sub(r'["\']installed_apps["\']:\s*\[([^\]]*?)["\']erpnext["\']', r'"installed_apps": [\1"haloerp"', content)
        content = re.sub(r'/assets/erpnext/', '/assets/haloerp/', content)
        content = re.sub(r'assets/erpnext/', 'assets/haloerp/', content)
        content = re.sub(r'erpnext-logo\.svg', 'haloerp-logo.svg', content)
        content = re.sub(r'erpnext-favicon\.svg', 'haloerp-favicon.svg', content)

        # 6. Specific Class renames with backward compatibility
        if relpath.endswith("accounts/custom/address.py"):
            content = content.replace("class ERPNextAddress(Address):", "class HaloERPAddress(Address):")
            if "ERPNextAddress = HaloERPAddress" not in content:
                content += "\n\n# Backward compatibility alias\nERPNextAddress = HaloERPAddress\n"
        elif relpath.endswith("tests/utils.py"):
            content = content.replace("class ERPNextTestSuite(unittest.TestCase):", "class HaloERPTestSuite(unittest.TestCase):")
            if "ERPNextTestSuite = HaloERPTestSuite" not in content:
                content += "\n\n# Backward compatibility alias\nERPNextTestSuite = HaloERPTestSuite\n"
        elif relpath.endswith("deprecation_dumpster.py"):
            content = re.sub(r"\bclass ERPNextDeprecationError\b", "class HaloERPDeprecationError", content)
            content = re.sub(r"\bclass ERPNextDeprecationWarning\b", "class HaloERPDeprecationWarning", content)
            content = re.sub(r"\bclass PendingERPNextDeprecationWarning\b", "class PendingHaloERPDeprecationWarning", content)
            content = re.sub(r"\bclass V15ERPNextDeprecationWarning\b", "class V15HaloERPDeprecationWarning", content)
            content = re.sub(r"\bclass V16ERPNextDeprecationWarning\b", "class V16HaloERPDeprecationWarning", content)
            content = re.sub(r"\bclass V17ERPNextDeprecationWarning\b", "class V17HaloERPDeprecationWarning", content)
            content = re.sub(r'class_name = f"\{cleaned_graduation\}ERPNextDeprecationWarning"', 'class_name = f"{cleaned_graduation}HaloERPDeprecationWarning"', content)
            content = content.replace("warnings.simplefilter(\"error\", ERPNextDeprecationError)", "warnings.simplefilter(\"error\", HaloERPDeprecationError)")
            content = content.replace("warnings.simplefilter(\"ignore\", PendingERPNextDeprecationWarning)", "warnings.simplefilter(\"ignore\", PendingHaloERPDeprecationWarning)")
            if "ERPNextDeprecationError = HaloERPDeprecationError" not in content:
                content += "\n\n# Aliases for backward compatibility\nERPNextDeprecationError = HaloERPDeprecationError\nERPNextDeprecationWarning = HaloERPDeprecationWarning\nPendingERPNextDeprecationWarning = PendingHaloERPDeprecationWarning\n"

        # 7. hooks.py special handling
        if relpath.endswith("hooks.py"):
            content = re.sub(r'^app_name\s*=\s*["\']erpnext["\']', 'app_name = "haloerp"', content, flags=re.MULTILINE)
            content = re.sub(r'^app_title\s*=\s*["\']ERPNext["\']', 'app_title = "HaloERP"', content, flags=re.MULTILINE)
            content = re.sub(r'^app_publisher\s*=\s*["\'][^"\']+["\']', 'app_publisher = "HaloERP"', content, flags=re.MULTILINE)
            content = re.sub(r'^app_description\s*=\s*"""[^"]+"""', 'app_description = """HaloERP Enterprise Resource Planning"""', content, flags=re.MULTILINE)
            content = re.sub(r'app_include_js\s*=\s*["\']erpnext\.bundle\.js["\']', 'app_include_js = "haloerp.bundle.js"', content)
            content = re.sub(r'app_include_css\s*=\s*["\']erpnext\.bundle\.css["\']', 'app_include_css = "haloerp.bundle.css"', content)
            content = re.sub(r'web_include_css\s*=\s*["\']erpnext-web\.bundle\.css["\']', 'web_include_css = "haloerp-web.bundle.css"', content)
            content = re.sub(r'email_css\s*=\s*["\']email_erpnext\.bundle\.css["\']', 'email_css = "email_haloerp.bundle.css"', content)
            content = re.sub(r'setup_wizard_requires\s*=\s*["\']assets/erpnext/js/setup_wizard\.js["\']', 'setup_wizard_requires = "assets/haloerp/js/setup_wizard.js"', content)
            content = content.replace("erpnext.accounts.custom.address.ERPNextAddress", "haloerp.accounts.custom.address.HaloERPAddress")
            content = content.replace("erpnext-logo.svg", "haloerp-logo.svg")
            content = content.replace("erpnext-favicon.svg", "haloerp-favicon.svg")
            content = content.replace("erpnext-logo.jpg", "haloerp-logo.png")
            self.stats["hooks_changed"] += 1

        if content != original:
            self.stats["files_transformed"] += 1
            if not self.dry_run:
                with open(fpath, "w", encoding="utf-8") as fp:
                    fp.write(content)

    def transform_js_ts_file(self, fpath: Path, relpath: str):
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as fp:
                content = fp.read()
        except Exception:
            return

        original = content

        # Assets path
        content, c1 = re.subn(r"/assets/erpnext/", "/assets/haloerp/", content)
        content, c2 = re.subn(r"assets/erpnext/", "assets/haloerp/", content)
        
        # API method strings
        content, c3 = re.subn(r"([\"'])erpnext\.", r"\1haloerp.", content)
        content, c4 = re.subn(r"\berpnext_integrations\b", "haloerp_integrations", content)
        
        # erpnext JS namespace: erpnext. -> haloerp.
        content, c5 = re.subn(r"\berpnext\.", "haloerp.", content)
        content, c6 = re.subn(r"\bwindow\.erpnext\b", "window.haloerp", content)
        
        # Bundles & SCSS imports
        content = content.replace("erpnext.bundle.js", "haloerp.bundle.js")
        content = content.replace("erpnext.bundle.css", "haloerp.bundle.css")
        content = content.replace("erpnext-web.bundle.css", "haloerp-web.bundle.css")
        content = content.replace("email_erpnext.bundle.css", "email_haloerp.bundle.css")
        content = content.replace("erpnext/public/scss/website", "haloerp/public/scss/website")
        content = content.replace("erpnext-logo.svg", "haloerp-logo.svg")
        content = content.replace("erpnext-favicon.svg", "haloerp-favicon.svg")

        # In vite config
        if "outDir: '../erpnext/public/banking'" in content:
            content = content.replace("outDir: '../erpnext/public/banking'", "outDir: '../haloerp/public/banking'")

        self.stats["js_refs_changed"] += (c1 + c2 + c3 + c4 + c5 + c6)

        if content != original:
            self.stats["files_transformed"] += 1
            if not self.dry_run:
                with open(fpath, "w", encoding="utf-8") as fp:
                    fp.write(content)

    def transform_json_file(self, fpath: Path, relpath: str):
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as fp:
                content = fp.read()
        except Exception:
            return

        original = content

        # Module references in DocTypes
        content = re.sub(r'"module":\s*"ERPNext Integrations"', '"module": "HaloERP Integrations"', content)
        
        # App fields
        content = re.sub(r'"app":\s*"erpnext"', '"app": "haloerp"', content)
        content = re.sub(r'"name":\s*"ERPNext Settings"', '"name": "HaloERP Settings"', content)
        content = re.sub(r'"title":\s*"ERPNext Settings"', '"title": "HaloERP Settings"', content)
        content = re.sub(r'"label":\s*"ERPNext Settings"', '"label": "HaloERP Settings"', content)
        content = re.sub(r'"link_to":\s*"ERPNext Settings"', '"link_to": "HaloERP Settings"', content)
        content = re.sub(r'"name":\s*"ERPNext"', '"name": "HaloERP"', content)
        content = re.sub(r'"label":\s*"ERPNext"', '"label": "HaloERP"', content)
        content = re.sub(r'"parent_icon":\s*"ERPNext"', '"parent_icon": "HaloERP"', content)
        
        # Assets & methods inside json expressions
        content = re.sub(r'/assets/erpnext/', '/assets/haloerp/', content)
        content = re.sub(r'\berpnext\.', 'haloerp.', content)
        content = re.sub(r'"install_apps":\s*\[(.*?)["\']erpnext["\'](.*?)\]', r'"install_apps": [\1"haloerp"\2]', content)
        content = content.replace("erpnext-logo.svg", "haloerp-logo.svg")
        content = content.replace("erpnext-favicon.svg", "haloerp-favicon.svg")

        if content != original:
            self.stats["files_transformed"] += 1
            self.stats["json_refs_changed"] += 1
            if not self.dry_run:
                with open(fpath, "w", encoding="utf-8") as fp:
                    fp.write(content)

    def transform_markup_style_file(self, fpath: Path, relpath: str):
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as fp:
                content = fp.read()
        except Exception:
            return

        original = content
        content = re.sub(r"/assets/erpnext/", "/assets/haloerp/", content)
        content = re.sub(r"assets/erpnext/", "assets/haloerp/", content)
        content = re.sub(r"\berpnext\.", "haloerp.", content)
        content = re.sub(r'([\"\'\s])erpnext/templates/', r'\1haloerp/templates/', content)
        content = content.replace("erpnext.bundle.js", "haloerp.bundle.js")
        content = content.replace("erpnext.bundle.css", "haloerp.bundle.css")
        content = content.replace("erpnext-web.bundle.css", "haloerp-web.bundle.css")
        content = content.replace("email_erpnext.bundle.css", "email_haloerp.bundle.css")
        content = content.replace("erpnext-logo.svg", "haloerp-logo.svg")
        content = content.replace("erpnext-favicon.svg", "haloerp-favicon.svg")

        if content != original:
            self.stats["files_transformed"] += 1
            if not self.dry_run:
                with open(fpath, "w", encoding="utf-8") as fp:
                    fp.write(content)

    def transform_yaml_file(self, fpath: Path, relpath: str):
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as fp:
                content = fp.read()
        except Exception:
            return

        original = content
        content = re.sub(r"\berpnext/", "haloerp/", content)
        content = re.sub(r"\berpnext\b", "haloerp", content)

        if content != original:
            self.stats["files_transformed"] += 1
            if not self.dry_run:
                with open(fpath, "w", encoding="utf-8") as fp:
                    fp.write(content)

    def transform_shell_file(self, fpath: Path, relpath: str):
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as fp:
                content = fp.read()
        except Exception:
            return

        original = content
        content = re.sub(r"apps/erpnext\b", "apps/haloerp", content)
        content = re.sub(r"bench get-app erpnext\b", "bench get-app haloerp", content)
        content = re.sub(r"bench get-app --skip-assets erpnext\b", "bench get-app --skip-assets haloerp", content)
        content = re.sub(r"bench generate-pot-file --app erpnext\b", "bench generate-pot-file --app haloerp", content)
        content = re.sub(r"--app erpnext\b", "--app haloerp", content)
        content = re.sub(r"erpnext/locale", "haloerp/locale", content)

        if content != original:
            self.stats["files_transformed"] += 1
            if not self.dry_run:
                with open(fpath, "w", encoding="utf-8") as fp:
                    fp.write(content)

    def transform_config_file(self, fpath: Path, relpath: str):
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as fp:
                content = fp.read()
        except Exception:
            return

        original = content
        if fpath.name == ".eslintrc":
            content = content.replace('"erpnext": true', '"haloerp": true')
        elif fpath.name == ".gitignore":
            content = content.replace("erpnext/public/dist", "haloerp/public/dist")
            content = content.replace("erpnext/docs/current", "haloerp/docs/current")
            content = content.replace("erpnext/public/banking", "haloerp/public/banking")
            content = content.replace("erpnext/www/banking.html", "haloerp/www/banking.html")
        elif fpath.name == "babel_extractors.csv":
            content = content.replace("erpnext.gettext.", "haloerp.gettext.")
        elif fpath.name == "CODEOWNERS":
            content = content.replace("erpnext/", "haloerp/")
        elif fpath.name == "crowdin.yml":
            content = content.replace("/erpnext/locale/", "/haloerp/locale/")
        elif fpath.name in [".pre-commit-config.yaml", ".releaserc", "codecov.yml"]:
            content = content.replace("erpnext/", "haloerp/")
            content = content.replace("erpnext.", "haloerp.")
            content = content.replace("erpnext", "haloerp")

        if content != original:
            self.stats["files_transformed"] += 1
            if not self.dry_run:
                with open(fpath, "w", encoding="utf-8") as fp:
                    fp.write(content)

    def step_4_transform_metadata(self):
        self.log("\n[Step 4] Updating Package & App Metadata...")
        
        # 1. pyproject.toml
        pyproject_path = self.repo_dir / "pyproject.toml"
        if pyproject_path.exists():
            with open(pyproject_path, "r", encoding="utf-8") as fp:
                pyproj = fp.read()
            
            pyproj = re.sub(r'name\s*=\s*"erpnext"', 'name = "haloerp"', pyproj)
            pyproj = re.sub(r'description\s*=\s*"Open Source ERP"', 'description = "HaloERP Enterprise Resource Planning"', pyproj)
            pyproj = pyproj.replace('"erpnext.deprecation_dumpster"', '"haloerp.deprecation_dumpster"')
            pyproj = pyproj.replace('out_dir = "../erpnext/public/banking"', 'out_dir = "../haloerp/public/banking"')
            pyproj = pyproj.replace('index_html_path = "../erpnext/www/banking.html"', 'index_html_path = "../haloerp/www/banking.html"')
            
            self.stats["metadata_changed"] += 1
            if not self.dry_run:
                with open(pyproject_path, "w", encoding="utf-8") as fp:
                    fp.write(pyproj)

        # 2. Root package.json
        pkg_path = self.repo_dir / "package.json"
        if pkg_path.exists():
            with open(pkg_path, "r", encoding="utf-8") as fp:
                pkg = fp.read()
            pkg = re.sub(r'"name":\s*"erpnext"', '"name": "haloerp"', pkg)
            pkg = re.sub(r'"description":\s*"[^"]+"', '"description": "HaloERP Enterprise Resource Planning system powered by Frappe Framework"', pkg)
            self.stats["metadata_changed"] += 1
            if not self.dry_run:
                with open(pkg_path, "w", encoding="utf-8") as fp:
                    fp.write(pkg)

        # 3. modules.txt
        app_dir = self.repo_dir / ("haloerp" if (self.repo_dir / "haloerp").exists() or not self.dry_run else "erpnext")
        modules_path = app_dir / "modules.txt"
        if modules_path.exists():
            with open(modules_path, "r", encoding="utf-8") as fp:
                modules = fp.read()
            modules = modules.replace("ERPNext Integrations", "HaloERP Integrations")
            self.stats["metadata_changed"] += 1
            if not self.dry_run:
                with open(modules_path, "w", encoding="utf-8") as fp:
                    fp.write(modules)

        # 4. patches.txt
        patches_path = app_dir / "patches.txt"
        if patches_path.exists():
            with open(patches_path, "r", encoding="utf-8") as fp:
                patches = fp.read()
            patches = re.sub(r'\berpnext\.patches\.', 'haloerp.patches.', patches)
            self.stats["metadata_changed"] += 1
            if not self.dry_run:
                with open(patches_path, "w", encoding="utf-8") as fp:
                    fp.write(patches)

        # 5. banking/package.json
        banking_pkg = self.repo_dir / "banking" / "package.json"
        if banking_pkg.exists():
            with open(banking_pkg, "r", encoding="utf-8") as fp:
                bpkg = fp.read()
            bpkg = re.sub(r'"name":\s*"banking"', '"name": "haloerp-banking"', bpkg)
            bpkg = bpkg.replace("../erpnext/", "../haloerp/")
            self.stats["metadata_changed"] += 1
            if not self.dry_run:
                with open(banking_pkg, "w", encoding="utf-8") as fp:
                    fp.write(bpkg)

def main():
    args = parse_args()
    repo_dir = Path(__file__).resolve().parent.parent
    migrator = HaloERPMigrator(repo_dir=repo_dir, dry_run=args.dry_run)
    migrator.run()

if __name__ == "__main__":
    main()

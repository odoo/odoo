import os
import sys
import tempfile
import zipfile
from pathlib import Path

import requests

from . import Command


class Deploy(Command):
    """Deploy a module on an Odoo instance"""

    def __init__(self):
        super().__init__()
        self.session = requests.session()

    def deploy_module(self, module_path, url, login, password, db="", force=False):
        url = url.rstrip("/")
        module_file = self.zip_module(module_path)
        try:
            return self.login_upload_module(
                module_file, url, login, password, db, force=force
            )
        finally:
            Path(module_file).unlink()

    def login_upload_module(self, module_file, url, login, password, db, force=False):
        print("Uploading module file...")
        self.session.get(
            f"{url}/web/login?db={db}", allow_redirects=False
        )  # this set the db in the session
        endpoint = url + "/base_import_module/login_upload"
        post_data = {
            "login": login,
            "password": password,
            "db": db,
            "force": "1" if force else "",
        }
        with Path(module_file).open("rb") as f:
            res = self.session.post(endpoint, files={"mod_file": f}, data=post_data)

        if res.status_code == 404:
            raise requests.exceptions.HTTPError(
                f"The server {url!r} does not have the 'base_import_module' installed or is not up-to-date.",
                response=res,
            )
        res.raise_for_status()
        return res.text

    def zip_module(self, path):
        """Create a zip archive of the module at ``path``.

        Returns the path to the temporary zip file.
        """
        module_dir = Path(path).resolve()
        if not module_dir.is_dir():
            raise FileNotFoundError(f"Could not find module directory {module_dir!r}")
        fd, temp = tempfile.mkstemp(suffix=".zip")
        os.close(fd)
        try:
            print("Zipping module directory...")
            with zipfile.ZipFile(temp, "w") as zfile:
                for filepath in module_dir.rglob("*"):
                    if filepath.is_file():
                        zfile.write(filepath, filepath.relative_to(module_dir.parent))
                return temp
        except Exception:
            Path(temp).unlink()
            raise

    def run(self, cmdargs):
        parser = self.parser
        parser.add_argument("path", help="Path of the module to deploy")
        parser.add_argument(
            "url",
            nargs="?",
            help="Url of the server (default=http://localhost:8069)",
            default="http://localhost:8069",
        )
        parser.add_argument(
            "--db",
            dest="db",
            help="Database to use if server does not use db-filter.",
        )
        parser.add_argument(
            "--login",
            dest="login",
            default="admin",
            help="Login (default=admin)",
        )
        parser.add_argument(
            "--password",
            dest="password",
            default="admin",
            help="Password (default=admin)",
        )
        # NOTE: SSL verification is disabled by default — intentional for dev deployment
        # tooling (default URL is http://localhost:8069). Use --verify-ssl for HTTPS targets.
        parser.add_argument(
            "--verify-ssl", action="store_true", help="Verify SSL certificate"
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help='Force init even if module is already installed. (will update `noupdate="1"` records)',
        )
        if not cmdargs:
            sys.exit(parser.print_help())

        args = parser.parse_args(args=cmdargs)

        if not args.verify_ssl:
            self.session.verify = False

        try:
            if not args.url.startswith(("http://", "https://")):
                args.url = f"https://{args.url}"
            result = self.deploy_module(
                args.path,
                args.url,
                args.login,
                args.password,
                args.db,
                force=args.force,
            )
            print(result)
        except Exception as e:
            sys.exit(f"ERROR: {e}")

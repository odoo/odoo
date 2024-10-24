import subprocess
import shutil
import itertools
from . import get_tooling, defineCommand, CONFIG

from logging import getLogger
logger = getLogger(__name__)


def has_node_modules(path):
    return path.joinpath("package-lock.json").exists() and path.joinpath("node_modules").exists()

def copy(src, target):
    logger.info(f"Copy {src} to {target}")
    args = []
    if src.is_dir():
        args.append("-r")
    args.extend([src, target])
    subprocess.run(["cp"] + args)

NODE_FILES = {
    "package.json": "_package.json",
}

ES_LINT_FILES = {
    ".eslintignore": "_eslintignore",
    ".eslintrc.json": "_eslintrc.json",
}

FILES = {
    **NODE_FILES,
    **ES_LINT_FILES,
}

def is_path_odoo(path):
    return path.joinpath("odoo-bin").exists()

def create_in_roots(addons_path, force_node=False):
    odoo = CONFIG["odoo"]
    tooling = get_tooling()

    tooling_to_root = {v: k for k,v in FILES.items()}

    for fsource, ftarget in tooling_to_root.items():
        src, trg = tooling.joinpath(fsource), odoo.joinpath(ftarget)
        copy(src, trg)
    if not has_node_modules(odoo) or force_node:
        logger.info(f"Building node_modules in {odoo}")
        subprocess.run(["npm", "install"], cwd=odoo)

    for root in addons_path.keys():
        if root == odoo:
            continue
        for fsource, ftarget in tooling_to_root.items():
            src, trg = tooling.joinpath(fsource), root.joinpath(ftarget)
            copy(src, trg)

        for fname in ["node_modules", "package-lock.json"]:
            src, trg = odoo.joinpath(fname), root
            copy(src, trg)

def delete_in_roots(addons_path, force_node=False):
    files = list(FILES.keys())
    if force_node:
        files.extend(["node_modules", "package-lock.json"])
    for root in addons_path.keys():
        for fname in files:
            file = root.joinpath(fname)
            if file.exists():
                logger.info(f"Delete {file}")
                if file.is_dir():
                    shutil.rmtree(file)
                else:
                    file.unlink()


def root_paths_from_addons_path(addons_path):
    for root, info in addons_path.items():
        for parent in itertools.chain([root], root.parents):
            if parent.joinpath(".git").exists():
                yield parent, info

@defineCommand
class nodejs:
    @staticmethod
    def configure(argparser):
        argparser.add_argument("--force-node", action="store_true")

    def execute(self, addons_path, operation, args):
        root_paths = root_paths_from_addons_path(addons_path)
        if operation == "install":
            return create_in_roots(dict(root_paths), args.force_node)
        else:
            return delete_in_roots(dict(root_paths), args.force_node)

def pre_commit_in_roots(addons_path):
    for root, info in addons_path.items():
        if not has_node_modules(root):
            create_in_roots({root: info})
        logger.info(f"Created precommit at {root} (git config core.hooksPath)")
        subprocess.run(["git", "config", "core.hooksPath", get_tooling().joinpath("hooks")], cwd=root)


@defineCommand
class precommit:
    def execute(self, addons_path, operation, args):
        root_paths = root_paths_from_addons_path(addons_path)
        if operation == "install":
            pre_commit_in_roots(dict(root_paths))
        else:
            for root in dict(root_paths).keys():
                cmd = ["git", "config", "--unset", "core.hooksPath"]
                logger.info(f"Deactivating hooks in {root} ({' '.join(cmd)})")
                subprocess.run(["git", "config", "--unset", "core.hooksPath"], cwd=root)

import subprocess
import shutil
import shlex
import itertools
from . import get_tooling, defineCommand, CONFIG

from logging import getLogger
logger = getLogger(__name__)


def has_node_modules(path):
    return path.joinpath("package-lock.json").exists() and path.joinpath("node_modules").exists()


def copy(src, target):
    args = []
    if src.is_dir():
        args.append("-r")
    args.extend([src, target])
    if subprocess.run(["cp"] + args, check=False).returncode == 0:
        logger.info("Copied %s to %s", str(src), str(target))


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

    tooling_to_root = {v: k for k, v in FILES.items()}

    for fsource, ftarget in tooling_to_root.items():
        src, trg = tooling.joinpath(fsource), odoo.joinpath(ftarget)
        copy(src, trg)
    if not has_node_modules(odoo) or force_node:
        logger.info("Building node_modules in %s", str(odoo))
        subprocess.run(["npm", "install"], cwd=odoo, check=False)

    for root in addons_path:
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
    for root in addons_path:
        for fname in files:
            file = root.joinpath(fname)
            if file.exists():
                if file.is_dir():
                    shutil.rmtree(file)
                else:
                    file.unlink()
                logger.info("Deleted %s", str(file))


def root_paths_from_addons_path(addons_path):
    for root, info in addons_path.items():
        for parent in itertools.chain([root], root.parents):
            if parent.joinpath(".git").exists():
                yield parent, info
                break


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
    hook_path = get_tooling().joinpath("hooks").resolve()
    for root, info in addons_path.items():
        try:
            all_existings = [file.name for file in root.joinpath(".git/hooks").iterdir() if "." not in file.name]
            if all_existings:
                logger.error("Skipped install git hooks in %(root)s. Supposedly active hooks: %(hooks)s", dict(root=root, hooks=", ".join(all_existings)))
                continue
        except OSError:
            pass

        if not has_node_modules(root):
            create_in_roots({root: info})

        done = False
        for cmd in ["git config --worktree core.hooksPath", "git config core.hooksPath"]:
            if subprocess.run(shlex.split(cmd) + [hook_path], cwd=root, check=False).returncode == 0:
                done = True
                logger.info("Set git hooks at %s (%s)", str(root), cmd)
                break
        if not done:
            logger.error("Failed to set git hooks for %s", str(root))


@defineCommand
class precommit:
    def execute(self, addons_path, operation, args):
        root_paths = dict(root_paths_from_addons_path(addons_path))
        if operation == "install":
            pre_commit_in_roots(root_paths)
        else:
            for root in root_paths:
                done = False
                for cmd in ["git config --worktree --unset core.hooksPath", "git config --worktree --unset core.hooksPath"]:
                    if subprocess.run(shlex.split(cmd), cwd=root, check=False).returncode == 0:
                        done = True
                        logger.info("Deactivated hooks in %s (%s)", str(root), cmd)
                        break
                if not done:
                    logger.error("Failed to remove git hooks for %s", root)

import ast
import logging
import os
import re
import subprocess

from odoo.tools import OrderedSet, config
from odoo.tools.which import which
from odoo.tests import BaseCase

_logger = logging.getLogger(__name__)

def get_repos() -> list[str]:
    """ get all git repos in the given path """
    repo_paths = OrderedSet()
    git = which('git')
    for addon_path in config['addons_path']:
        try:
            repo_path = subprocess.run(
                [git, 'rev-parse', '--show-toplevel'],
                capture_output=True,
                check=False,
                text=True,
                cwd=addon_path
            ).stdout.strip()
            if repo_path:
                repo_paths.add(repo_path)
        except Exception as e:
            continue
    return list(repo_paths)


def get_base_version(repo_path: str) -> str | None:
    """ use git to get the base version of the current Odoo branch """
    try:
        branch_name = subprocess.run(
            ['git', "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            check=False,
            text=True,
            cwd=repo_path
        ).stdout.strip()
    except Exception as e:
        return None

    # master-xxx / saas-18.1-xxx / 18.0-xxx
    pattern = r'^(master|saas-\d+\.\d+|\d+\.\d+)(?:-|$)'
    match = re.match(pattern, branch_name)
    if match:
        return match.group(1)
    return None


def get_diff_files(repo_path: str, base_version: str, filter: str | None = None) -> list[str]:
    files = []
    filter_cmd = ['--', filter] if filter else []
    try:
        git = which('git')
        result = subprocess.run(
            [git, 'diff', '--name-only', f'{base_version}'] + filter_cmd,
            capture_output=True,
            check=False,
            text=True,
            cwd=repo_path
        ).stdout.strip()
        if result:
            files = result.split('\n')
        return files
    except Exception as e:
        return files


def get_diff_lines(repo_path: str, file: str, base_version) -> set[int]:
    git = which('git')
    p1 = subprocess.Popen([git, "diff", "--unified=0", base_version, "--", file], stdout=subprocess.PIPE, cwd=repo_path)
    p2 = subprocess.Popen(["grep", "^@@"], stdin=p1.stdout, stdout=subprocess.PIPE, text=True)
    line_regex = re.compile(r'^@@ -[0-9,]+ \+(?P<start>[0-9]+),?(?P<count>[0-9]*) @@')
    lines = set()
    for diff in p2.communicate()[0].split('\n'):
        if match := line_regex.match(diff):
            start = int(match.group('start'))
            count = int(match.group('count')) if match.group('count') else 1
            lines |= set(range(start, start + count))
    return lines


class EnvRefVisitor(ast.NodeVisitor):
    def __init__(self, filepath, diff_lines):
        self.issues = []
        self.filepath = filepath
        self.diff_lines = diff_lines
        self.env_ref_names = set()  # Track variables that store env.ref

    def _is_node_in_diff(self, node):
        """Check if any line of the node is in the diff"""
        start_line = node.lineno
        end_line = node.end_lineno
        return any(line in self.diff_lines for line in range(start_line, end_line + 1))

    def _is_ref_raise_if_not_found(self, node):
        """Check if the node is a call to env.ref with raise_if_not_found=True"""
        raise_if_not_found = True  # default to True
        for keyword in node.keywords:
            if keyword.arg == 'raise_if_not_found':
                if isinstance(keyword.value, ast.Constant) and keyword.value.value is False:
                    raise_if_not_found = False
        return raise_if_not_found

    def visit_Assign(self, node):
        """ Track assignments of env.ref to variables to handle use cases like

            for name in names:
            ref('xxx', raise_if_not_found=False)
        """
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            value = node.value
            if (isinstance(value, ast.Attribute) and value.attr == 'ref' and
                isinstance(value.value, (ast.Name, ast.Attribute))):
                current = value.value
                is_env_ref = False

                if isinstance(current, ast.Attribute) and current.attr == 'env':
                    is_env_ref = True
                elif isinstance(current, ast.Name) and current.id == 'env':
                    is_env_ref = True

                if is_env_ref:
                    self.env_ref_names.add(node.targets[0].id)
        self.generic_visit(node)

    def visit_Call(self, node):
        """ check for env.ref calls """
        if isinstance(node.func, ast.Attribute) and node.func.attr == 'ref':
            current = node.func.value
            is_env_ref = False

            # Check if the call ends with env.ref
            if isinstance(current, ast.Attribute) and current.attr == 'env':
                is_env_ref = True
            elif isinstance(current, ast.Name) and current.id == 'env':
                is_env_ref = True

            if is_env_ref:
                if not self._is_node_in_diff(node):
                    return
                if self._is_ref_raise_if_not_found(node):
                    self.issues.append(f'"{self.filepath}", line {node.lineno}')
        elif isinstance(node.func, ast.Name) and node.func.id in self.env_ref_names:
            # Handle stored env.ref calls
            if not self._is_node_in_diff(node):
                return
            if self._is_ref_raise_if_not_found(node):
                self.issues.append(f'"{self.filepath}", line {node.lineno}')

        self.generic_visit(node)


class TestDiff(BaseCase):
    def test_env_ref_usage(self):
        """Check for env.ref calls without raise_if_not_found=True"""
        def check_file(filepath, diff_lines):
            with open(filepath, 'r') as f:
                content = f.read()
            try:
                tree = ast.parse(content)
                visitor = EnvRefVisitor(filepath, diff_lines)
                visitor.visit(tree)
                return visitor.issues
            except SyntaxError:
                return []

        diff_files = {}  # {repo_path: [file]}
        repos = get_repos()
        _logger.info(f"Found {len(repos)} repos")
        for repo_path in get_repos():
            base_version = get_base_version(repo_path)
            if not base_version:
                continue
            diff_files[(repo_path, base_version)] = get_diff_files(repo_path, base_version, '*py')

        issues = []
        for (repo_path, base_version), files in diff_files.items():
            for file in files:
                diff_lines = get_diff_lines(repo_path, file, base_version)
                file_path = os.path.join(repo_path, file)
                file_issues = check_file(file_path, diff_lines)
                if file_issues:
                    issues.extend(file_issues)

        self.assertFalse(
            bool(issues),
            "Found env.ref calls with raise_if_not_found=True:\n" + "\n".join(issues)
        )

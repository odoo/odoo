import ast
import logging
import os
import re
import subprocess

from collections import defaultdict
from lxml import etree

import odoo.addons

from odoo.modules.module import get_manifest
from odoo.tests import BaseCase
from odoo.tools import OrderedSet, config
from odoo.tools.which import which


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
    _logger.info(f"Found {len(repo_paths)} repos")
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
    """ get the files that are in the diff for the given base version """
    filter_cmd = ['--', filter] if filter else []
    try:
        git = which('git')
        result = subprocess.run(
            [git, 'diff', '--name-only', base_version] + filter_cmd,
            capture_output=True,
            check=False,
            text=True,
            cwd=repo_path
        ).stdout.strip()
        if not result:
            return []
        return result.split('\n')
    except Exception as e:
        return []


def get_diff_lines(git_path: str, repo_path: str, base_version: str) -> set[int]:
    """ get the lines of the diff for the given file
    
    :param repo_path: the absolute path of the git repo
    :param file: the relative path of the file to the git repo
    :param base_version: the base version to get the diff for

    :return: the lines of the diff for the given file
    """
    git = which('git')
    p1 = subprocess.Popen([git, "diff", "--unified=0", base_version, "--", git_path], stdout=subprocess.PIPE, cwd=repo_path)
    p2 = subprocess.Popen(["grep", "^@@"], stdin=p1.stdout, stdout=subprocess.PIPE, text=True)
    line_regex = re.compile(r'^@@ -[0-9,]+ \+(?P<start>[0-9]+),?(?P<count>[0-9]*) @@')
    lines = set()
    for diff in p2.communicate()[0].split('\n'):
        if match := line_regex.match(diff):
            start = int(match.group('start'))
            count = int(match.group('count')) if match.group('count') else 1
            lines |= set(range(start, start + count))
    return lines


class FileInfo:
    root_path = os.path.abspath(config.root_path)
    addons_paths = [
        os.path.normpath(os.path.normcase(addons_path)) + os.sep
        for addons_path in odoo.addons.__path__
    ]

    def __init__(self, /, *, repo_path: str = '', git_path: str = '', base_version: str = ''):
        self.base_version: str = base_version
        self.repo_path: str = repo_path and os.path.normpath(os.path.normcase(repo_path))  # /Users/username/project/odoo
        self.git_path: str = git_path and os.path.normpath(os.path.normcase(git_path))  # odoo/addons/base/models/res_partner.py
        self.abs_path = os.path.join(self.repo_path, self.git_path)  # /Users/username/project/odoo/odoo/addons/base/models/res_partner.py
        self.odoo_path: str = self.parse_odoo_path(self.abs_path) or ''  # base/models/res_partner.py
        self.module_name: str = self.odoo_path.split(os.sep)[0]  # base
        self.module_path: str = self.odoo_path[len(self.module_name) + len(os.sep):]  # models/res_partner.py

    @classmethod
    def parse_odoo_path(cls, abs_path: str) -> str | None:
        """ parse the odoo path from the given absolute path """
        for addons_path in cls.addons_paths:
            if abs_path.startswith(addons_path) and len(abs_path) > len(addons_path):
                odoo_path = abs_path[len(addons_path):].strip(os.sep)
                return odoo_path
        return None


class EvalRefVisitor(ast.NodeVisitor):
    def __init__(self, filepath, line=0):
        self.issues = []
        self.line = line
        self.filepath = filepath

    def _is_ref_raise_if_not_found(self, node):
        """Check if the node is a call to env.ref without raise_if_not_found=False"""
        raise_if_not_found = True  # default to True
        for keyword in node.keywords:
            if keyword.arg == 'raise_if_not_found':
                if isinstance(keyword.value, ast.Constant) and keyword.value.value is False:
                    raise_if_not_found = False
        return raise_if_not_found

    def visit_Call(self, node):
        """ check for env.ref calls """
        if isinstance(node.func, ast.Name) and node.func.id == 'ref':
            if self._is_ref_raise_if_not_found(node):
                # for ref() calls, check if the ref is for another module
                self.issues.append(f'"{self.filepath}", line {self.line}')
        
        self.generic_visit(node)


class FileEnvRefVisitor(EvalRefVisitor):
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

    def visit_Assign(self, node):
        """ Track assignments of env.ref to variables to handle use cases like

            ref = self.env.ref
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
                if self._is_node_in_diff(node) and self._is_ref_raise_if_not_found(node):
                    self.issues.append(f'"{self.filepath}", line {node.lineno}')
        elif isinstance(node.func, ast.Name) and node.func.id in self.env_ref_names:
            # Handle stored env.ref calls
            if self._is_node_in_diff(node) and self._is_ref_raise_if_not_found(node):
                self.issues.append(f'"{self.filepath}", line {node.lineno}')

        self.generic_visit(node)


def check_data_xml_ref(module_name, abs_path, diff_lines):
    issues = defaultdict(list)
    previous_tag_line = 0
    _logger.info(f"Checking {abs_path}")
    with open(abs_path, 'rb') as fp:
        context = etree.iterparse(fp, events=("start", "end"))
        for event, element in context:
            if event == "start":
                # elemen.source line is the last line of the tag declaration
                # start_line should be the first line of the tag declaration
                # the below is an estimation with one corner case
                #
                # ...  > <field ref='xxx'
                # ... />
                # 
                # where
                # 1. the end of the previous tag and the start line of the current tag are in the same line
                # 2. the current tag is multiline
                # 3. only the start line of the current tag is modified
                # usually in a easy to read xml, if a start tag follows the prvious tag in the same line,
                # its closing tag should be in the same line. So the corner case is acceptable.
                start_line = min(element.sourceline, previous_tag_line + 1)
                if not any(line in diff_lines for line in range(start_line, element.sourceline + 1)):
                    continue
                # check the element if the start tag is modified
                if element.tag == 'record':
                    record = element
                    id_attr = record.get('id')
                    force_create = record.get('force_create', 'True').lower()
                    if id_attr and '.' in id_attr and not id_attr.startswith(f'{module_name}.') and force_create not in ('0', 'false'):
                        issues['id'].append(f'{abs_path}, line {record.sourceline}')
                elif element.tag == 'field':
                    field = element
                    ref_attr = field.get('ref')
                    if ref_attr and '.' in ref_attr and not ref_attr.startswith(f'{module_name}.'):
                        issues['ref'].append(f'{abs_path}, line {field.sourceline}')
                    elif eval_attr := field.get('eval'):
                        # parse as python ast, check function ref
                        # add to issues if ref for another module without raise_if_not_found=False
                        tree = ast.parse(eval_attr)
                        visitor = EvalRefVisitor(abs_path, line=field.sourceline)
                        visitor.visit(tree)
                        if visitor.issues:
                            issues['eval'].append(visitor.issues[0])
                previous_tag_line = element.sourceline
            elif event == "end":
                previous_tag_line = element.sourceline
                element.clear()
                

    return issues


class TestDiff(BaseCase):
    def test_env_ref_usage(self):
        """Check for env.ref calls without raise_if_not_found=False"""
        def check_file(filepath, diff_lines):
            with open(filepath, 'r') as f:
                content = f.read()
            try:
                tree = ast.parse(content)
                visitor = FileEnvRefVisitor(filepath, diff_lines)
                visitor.visit(tree)
                return visitor.issues
            except SyntaxError:
                return []

        diff_files = []  # [FileInfo]
        for repo_path in get_repos():
            base_version = get_base_version(repo_path)
            if not base_version:
                continue
            diff_files.extend(
                FileInfo(repo_path=repo_path, base_version=base_version, git_path=file)
                for file in get_diff_files(repo_path, base_version, '*py')
            )

        issues = []
        for file_info in diff_files:
            diff_lines = get_diff_lines(file_info.git_path, file_info.repo_path, file_info.base_version)
            file_issues = check_file(file_info.abs_path, diff_lines)
            if file_issues:
                issues.extend(file_issues)

        self.assertFalse(
            bool(issues),
            "Found env.ref calls without raise_if_not_found=False\n" + "\n".join(issues)
        )

    def test_data_xml_ref_usage(self):
        """Check for ref for other modules"""
        diff_files: list[FileInfo] = []
        for repo_path in get_repos():
            base_version = get_base_version(repo_path)
            if not base_version:
                continue
            diff_files.extend(
                FileInfo(repo_path=repo_path, git_path=file, base_version=base_version)
                for file in get_diff_files(repo_path, base_version, '*.xml')
            )

        module_files: dict[str, list[FileInfo]] = defaultdict(list)  # {module_name: [file_info]}
        for file_info in diff_files:
            if file_info.odoo_path and file_info.module_name != 'base' and not file_info.module_name.startswith('test_'):
                module_files[file_info.module_name].append(file_info)

        issues: dict[str, list[str]] = defaultdict(list)
        for module_name, file_infos in module_files.items():
            manifest = get_manifest(module_name)
            data_files = set(manifest['data'])  # ignore manifest['demo']
            for file_info in file_infos:
                if file_info.module_path not in data_files:
                    continue
                diff_lines = get_diff_lines(file_info.git_path, file_info.repo_path,file_info.base_version)
                file_issues = check_data_xml_ref(module_name, file_info.abs_path, diff_lines)
                for type, messages in file_issues.items():
                    issues[type].extend(messages)

        messages = ''
        if issues['id']:
            messages += '\n\nFound id= for another module without force_create="0":\n' + "\n".join(issues['id'])
        if issues['ref']:
            messages += "\n\nFound ref= for another module:\n" + "\n".join(issues['ref'])
        if issues['eval']:
            messages += "\n\nFound eval uses ref( for another module without raise_if_not_found=False:\n" + "\n".join(issues['eval'])

        self.assertFalse(bool(messages), messages)

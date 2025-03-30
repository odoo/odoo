import ast
import typing
from collections import defaultdict

from odoo.modules.module import get_manifest
from .diff_case import DiffCase, FileInfo

if typing.TYPE_CHECKING:
    from lxml.etree import _Element


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


def check_ref_for_python_file(abs_path: str, diff_lines: set[int]) -> list[str]:
    with open(abs_path, 'r') as f:
        content = f.read()
    try:
        tree = ast.parse(content)
        visitor = FileEnvRefVisitor(abs_path, diff_lines)
        visitor.visit(tree)
        return visitor.issues
    except SyntaxError:
        return []


def check_ref_for_data_xml_element(element: '_Element', file_info: FileInfo) -> tuple[str, str] | None:
    # check the element if the start tag is modified
    if element.tag == 'record':
        record = element
        id_attr = record.get('id', None)
        force_create = record.get('force_create', 'True').lower()
        if id_attr and '.' in id_attr and not id_attr.startswith(f'{file_info.module_name}.') and force_create not in ('0', 'false'):
            return 'id', f'{file_info.abs_path}, line {record.sourceline}'
    elif element.tag == 'field':
        field = element
        ref_attr = field.get('ref', None)
        if ref_attr and '.' in ref_attr and not ref_attr.startswith(f'{file_info.module_name}.'):
            return 'ref', f'{file_info.abs_path}, line {field.sourceline}'
        elif eval_attr := field.get('eval', None):
            # parse as python ast, check function ref
            # add to issues if ref for another module without raise_if_not_found=False
            tree = ast.parse(eval_attr)
            visitor = EvalRefVisitor(file_info.abs_path, line=field.sourceline)
            visitor.visit(tree)
            if visitor.issues:
                return 'eval', visitor.issues[0]


class TestDiff(DiffCase):
    def test_env_ref_usage(self):
        """Check for env.ref calls without raise_if_not_found=False"""
        diff_files: list[FileInfo] = []
        for repo_path, base_version in self.repos.items():
            diff_files.extend(
                FileInfo(repo_path=repo_path, base_version=base_version, git_path=file)
                for file in self.get_diff_files(repo_path, base_version, '*py')
            )

        issues = []
        for file_info in diff_files:
            if not file_info.module_name or file_info.module_name.startswith('test_'):
                continue
            diff_lines = self.get_diff_lines(file_info.git_path, file_info.repo_path, file_info.base_version)
            file_issues = check_ref_for_python_file(file_info.abs_path, diff_lines)
            if file_issues:
                issues.extend(file_issues)

        self.assertFalse(
            bool(issues),
            "Found env.ref calls without raise_if_not_found=False\n" + "\n".join(issues)
        )

    def test_data_xml_ref_usage(self):
        """Check for ref for other modules"""
        diff_files: list[FileInfo] = []
        for repo_path, base_version in self.repos.items():
            diff_files.extend(
                FileInfo(repo_path=repo_path, git_path=file, base_version=base_version)
                for file in self.get_diff_files(repo_path, base_version, '*.xml')
            )

        module_files: dict[str, list[FileInfo]] = defaultdict(list)
        for file_info in diff_files:
            if file_info.module_name and file_info.module_name != 'base' and not file_info.module_name.startswith('test_'):
                module_files[file_info.module_name].append(file_info)

        issues: dict[str, list[str]] = defaultdict(list)
        for module_name, file_infos in module_files.items():
            manifest = get_manifest(module_name)
            data_files = set(manifest['data'])  # ignore manifest['demo']
            for file_info in file_infos:
                if file_info.module_path not in data_files:
                    continue
                diff_lines = self.get_diff_lines(file_info.git_path, file_info.repo_path,file_info.base_version)
                for element in self.yield_xml_diff_elements(file_info.abs_path, diff_lines):
                    if issue := check_ref_for_data_xml_element(element, file_info):
                        issues[issue[0]].append(issue[1])

        messages = ''
        if issues['id']:
            messages += '\n\nFound id= for another module without force_create="0":\n' + "\n".join(issues['id'])
        if issues['ref']:
            messages += "\n\nFound ref= for another module:\n" + "\n".join(issues['ref'])
        if issues['eval']:
            messages += "\n\nFound eval uses ref( for another module without raise_if_not_found=False:\n" + "\n".join(issues['eval'])

        self.assertFalse(bool(messages), messages)

import ast
import typing
import logging
from collections import defaultdict
from typing import Collection

from odoo.tests.diffcase import DiffCase, Element, FileInfo
from odoo.modules.module import get_manifest


_logger = logging.getLogger(__name__)

class EvalRefVisitor(ast.NodeVisitor):
    def __init__(self, line=(0, 0), protected_xml_ids=None):
        self.issues: list[tuple[int, int]] = []
        self.line = line
        self.protected_xml_ids = protected_xml_ids

    def _is_ref_risky(self, node):
        """Check if the node is risky"""
        if not node.args or node.args[0].value in self.protected_xml_ids:
            return False
        raise_if_not_found = True  # default to True
        for keyword in node.keywords:
            if keyword.arg == 'raise_if_not_found':
                if isinstance(keyword.value, ast.Constant) and keyword.value.value is False:
                    raise_if_not_found = False
        return raise_if_not_found

    def visit_Call(self, node):
        """ check for env.ref calls """
        if isinstance(node.func, ast.Name) and node.func.id == 'ref':
            if self._is_ref_risky(node):
                # for ref() calls, check if the ref is for another module
                self.issues.append(self.line)
        
        self.generic_visit(node)


class FileEnvRefVisitor(EvalRefVisitor):
    def __init__(self, filepath, diff_linenos, protected_xml_ids=None):
        self.issues: list[tuple[int, int]] = []
        self.filepath = filepath
        self.diff_linenos = diff_linenos
        self.env_ref_names = set()  # Track variables that store env.ref
        self.protected_xml_ids = protected_xml_ids

    def _is_node_in_diff(self, node):
        """Check if any line of the node is in the diff"""
        start_line = node.lineno
        end_line = node.end_lineno
        return any(line in self.diff_linenos for line in range(start_line, end_line + 1))

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

            if is_env_ref and self._is_node_in_diff(node) and self._is_ref_risky(node):
                self.issues.append((node.lineno, node.end_lineno))
        elif isinstance(node.func, ast.Name) and node.func.id in self.env_ref_names:
            # Handle stored env.ref calls
            if self._is_node_in_diff(node) and self._is_ref_risky(node):
                self.issues.append((node.lineno, node.end_lineno))

        self.generic_visit(node)


def check_ref_for_python_file(abs_path: str, diff_linenos: set[int], protected_xml_ids: Collection[str] = ()) -> list[tuple[int, int]]:
    with open(abs_path, 'r') as f:
        content = f.read()
    try:
        tree = ast.parse(content)
        visitor = FileEnvRefVisitor(abs_path, diff_linenos, protected_xml_ids)
        visitor.visit(tree)
        return visitor.issues
    except SyntaxError:
        return []


def check_ref_for_data_xml_element(element: Element, file_info: FileInfo, init: bool = True, protected_xml_ids: Collection[str] = ()) -> tuple[str, int, int] | None:
    """Check for references in xml files
    
    :param element: the xml element to check
    :param file_info: the file info of the xml file
    :param init: whether the file is used to init modules. If yes, we ignore references for the current module's records.
    :param protected_xml_ids: set of already protected xml ids
    """

    def is_ref_risky(ref: str) -> bool:
        xml_id = ref if '.' in ref else f'{file_info.module_name}.{ref}'
        if xml_id in protected_xml_ids:
            return False
        if init and xml_id.startswith(f'{file_info.module_name}.'):
            return False
        return True

    if element.tag == 'record':
        record = element
        id_attr = record.attrib.get('id')
        if not id_attr:
            return None
        if is_ref_risky(id_attr) and 'forcecreate' not in record.attrib:
            return 'inherit_id', record.start_lineno, record.end_lineno
    elif element.tag == 'field':
        field = element
        ref_attr = field.attrib.get('ref')
        if ref_attr:
            if is_ref_risky(ref_attr) and 'forcecreate' not in field.attrib:
                return 'ref', field.start_lineno, field.end_lineno
        elif eval_attr := field.attrib.get('eval'):
            # parse as python ast, check function ref
            # add to issues if ref for another module without raise_if_not_found=False
            tree = ast.parse(eval_attr)
            visitor = EvalRefVisitor(line=(field.start_lineno, field.end_lineno), protected_xml_ids=protected_xml_ids)
            visitor.visit(tree)
            if visitor.issues:
                return 'eval', visitor.issues[0][0], visitor.issues[0][1]
    elif element.tag == 'template':
        template = element
        id_attr = template.attrib.get('inherit_id')
        if not id_attr:
            return None
        if is_ref_risky(id_attr) and 'forcecreate' not in template.attrib:
            return 'inherit_id', template.start_lineno, template.end_lineno


def _get_protected_xml_ids():
    
    """Get protected records from imported Python files in addons directories.
    
    Scans for comments in the format "# PROTECT module.record_name" in Python files
    that are imported (directly or indirectly) through __init__.py files.
    
    Returns:
        set[str]: Set of protected record external IDs
    """
    import tokenize
    import os
    import odoo.addons
    from pathlib import Path

    def get_python_files(package_path):
        python_files = []
        for root, _, files in os.walk(package_path):
            for file in files:
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    python_files.append(full_path)
        return python_files

    protected = set()
    _logger.info("Getting protected records from Python files")
    for addons_path in odoo.addons.__path__:
        for addon_path in Path(addons_path).glob('*'):
            if not addon_path.is_dir():
                continue
            for py_file in get_python_files(addon_path):
                try:
                    if py_file.endswith('__init__.py') or py_file.endswith('__manifest__.py'):
                        continue
                    with tokenize.open(py_file) as f:
                        tokens = tokenize.generate_tokens(f.readline)
                        for token in tokens:
                            if token.type == tokenize.COMMENT and token.string.startswith('# PROTECT '):
                                external_id = token.string.split('PROTECT ', 1)[1].strip()
                                if external_id.count('.') == 1:
                                    protected.add(external_id)
                except tokenize.TokenError:
                    continue
    return protected


class TestRef(DiffCase):
    def __init__(self):
        super().__init__()
        # self.protected_xml_ids = set()
        self.protected_xml_ids = _get_protected_xml_ids()

    def test_env_ref_usage(self):
        """Check for env.ref calls without raise_if_not_found=False"""
        issues = []
        for file_info in self.diff_linenos['python'].values():
            if not file_info.module_name or file_info.module_name.startswith('test_'):
                continue
            file_issues = check_ref_for_python_file(file_info.abs_path, file_info.diff_linenos, self.protected_xml_ids)
            if file_issues:
                issues.extend((file_info.abs_path, *issue) for issue in file_issues)

        for issue in issues:
            self.report.append({
                'code': 'code_for_env_ref',
                'location': {
                    'row': issue[1],
                    'column': 1,
                },
                'end_location': {
                    'row': issue[2],
                    'column': 1,
                },
                'filename': issue[0],
                'message': 'Found env.ref calls without raise_if_not_found=False'
            })

    def test_data_xml_ref_usage(self):
        """Check for ref for other modules"""
        module_files: dict[str, list[FileInfo]] = defaultdict(list)
        for file_info in self.diff_linenos['xml'].values():
            if file_info.module_name and file_info.module_name != 'base' and not file_info.module_name.startswith('test_'):
                module_files[file_info.module_name].append(file_info)

        issues: dict[str, list[tuple[str, int, int]]] = defaultdict(list)
        for module_name, file_infos in module_files.items():
            manifest = get_manifest(module_name)
            data_files = set(manifest['data'])
            demo_files = set(manifest['demo'])
            for file_info in file_infos:
                if file_info.module_path in demo_files:
                    continue
                init = file_info.module_path in data_files
                for element in self.get_xml_diff_elements(file_info.abs_path):
                    if issue := check_ref_for_data_xml_element(element, file_info, init, self.protected_xml_ids):
                        issues[issue[0]].append((file_info.abs_path, *issue[1:]))

        for error_type, issues_ in issues.items():
            if error_type == 'id':
                code = 'code_for_id'
                message = 'Found id= for another module without force_create:'
            elif error_type == 'ref':
                code = 'code_for_ref'
                message = 'Found ref= for another module:'
            elif error_type == 'eval':
                code = 'code_for_eval'
                message = 'Found eval uses ref( for another module without raise_if_not_found=False:'
            elif error_type == 'inherit_id':
                code = 'code_for_inherit_id'
                message = 'Found inherit_id= for another module without force_create:'
            for issue in issues_:
                self.report.append({
                    'code': code,
                    'location': {
                        'row': issue[1],
                        'column': 1,
                    },
                    'end_location': {
                        'row': issue[2],
                        'column': 1,
                    },
                    'filename': issue[0],
                    'message': message
                })

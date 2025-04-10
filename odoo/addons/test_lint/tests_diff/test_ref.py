import ast
import logging
import os
from collections import defaultdict
from typing import Collection

from odoo.tests.diffcase import DiffCase, Element, DiffFile, DiagnosticKind, DiagnosticMessage
from odoo.modules.module import get_manifest


_logger = logging.getLogger(__name__)


PY_ENV_REF = DiagnosticKind(
    name='ref_env_call',
    body='Found env.ref calls without raise_if_not_found=False',
    suggestion='Add raise_if_not_found=False to the env.ref call'
)

XML_ID = DiagnosticKind(
    name='xml_id',
    body='Found id= for another module without force_create:',
    suggestion='Add force_create=True to the id='
)

XML_REF = DiagnosticKind(
    name='xml_ref',
    body='Found ref= for another module:',
    suggestion='Use eval'
)

XML_EVAL = DiagnosticKind(
    name='xml_eval',
    body='Found eval uses ref( for another module without raise_if_not_found=False:',
    suggestion='Add raise_if_not_found=False to the eval'
)

XML_INHERIT_ID = DiagnosticKind(
    name='xml_inherit_id',
    body='Found inherit_id= for another module without force_create:',
    suggestion='Add force_create'
)


class EvalRefVisitor(ast.NodeVisitor):
    def __init__(self, protected_xml_ids=None):
        self.diagnostic_kinds: list[DiagnosticKind] = []
        self.protected_xml_ids = protected_xml_ids

    def _is_ref_risky(self, node):
        """Check if the node is risky.
        
        Args:
            node: The AST node to check
            
        Returns:
            bool: True if the node is risky, False otherwise
        """
        if not node.args or node.args[0].value in self.protected_xml_ids:
            return False
        raise_if_not_found = True  # default to True
        for keyword in node.keywords:
            if keyword.arg == 'raise_if_not_found':
                if isinstance(keyword.value, ast.Constant) and keyword.value.value is False:
                    raise_if_not_found = False
        return raise_if_not_found

    def visit_Call(self, node):
        """Check for env.ref calls.
        
        Args:
            node: The AST node to visit
        """
        if isinstance(node.func, ast.Name) and node.func.id == 'ref':
            if self._is_ref_risky(node):
                # for ref() calls, check if the ref is for another module
                self.diagnostic_kinds.append(XML_REF)
        
        self.generic_visit(node)


class FileEnvRefVisitor(EvalRefVisitor):
    def __init__(self, diff_file: DiffFile, protected_xml_ids=None):
        self.diagnostics: list[DiagnosticMessage] = []
        self.diff_file = diff_file
        self.env_ref_names = set()  # Track variables that store env.ref
        self.protected_xml_ids = protected_xml_ids

    def _is_node_in_diff(self, node):
        """Check if any line of the node is in the diff"""
        return self.diff_file.is_lineno_in_diff(node.lineno, node.end_lineno)

    def visit_Assign(self, node):
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
        if isinstance(node.func, ast.Attribute) and node.func.attr == 'ref':
            current = node.func.value
            is_env_ref = False

            # Check if the call ends with env.ref
            if isinstance(current, ast.Attribute) and current.attr == 'env':
                is_env_ref = True
            elif isinstance(current, ast.Name) and current.id == 'env':
                is_env_ref = True

            if is_env_ref and self._is_node_in_diff(node) and self._is_ref_risky(node):
                self.diagnostics.append(PY_ENV_REF(self.diff_file, node.lineno, node.end_lineno))
        elif isinstance(node.func, ast.Name) and node.func.id in self.env_ref_names:
            # Handle stored env.ref calls
            if self._is_node_in_diff(node) and self._is_ref_risky(node):
                self.diagnostics.append(PY_ENV_REF(self.diff_file, node.lineno, node.end_lineno))

        self.generic_visit(node)


def check_ref_for_python_file(fileinfo: DiffFile, protected_xml_ids: Collection[str] = ()) -> list[DiagnosticMessage]:
    with open(fileinfo.path, 'r') as f:
        content = f.read()
    try:
        tree = ast.parse(content)
        visitor = FileEnvRefVisitor(fileinfo, protected_xml_ids)
        visitor.visit(tree)
        return visitor.diagnostics
    except SyntaxError:
        return []


def check_ref_for_data_xml_element(element: Element, diff_file: DiffFile, init: bool = True, protected_xml_ids: Collection[str] = ()) -> list[DiagnosticMessage]:

    def is_ref_risky(ref: str) -> bool:
        xml_id = ref if '.' in ref else f'{diff_file.module_name}.{ref}'
        if xml_id in protected_xml_ids:
            return False
        if init and xml_id.startswith(f'{diff_file.module_name}.'):
            return False
        return True

    result = []
    if element.tag == 'record':
        record = element
        id_attr = record.attrib.get('id')
        if id_attr and is_ref_risky(id_attr) and 'forcecreate' not in record.attrib:
            result.append(XML_INHERIT_ID(diff_file, record.start_lineno, record.end_lineno))
    elif element.tag == 'field':
        field = element
        ref_attr = field.attrib.get('ref')
        if ref_attr:
            if is_ref_risky(ref_attr) and 'forcecreate' not in field.attrib:
                result.append(XML_REF(diff_file, field.start_lineno, field.end_lineno))
        if eval_attr := field.attrib.get('eval'):
            # parse as python ast, check function ref
            # add to issues if ref for another module without raise_if_not_found=False
            tree = ast.parse(eval_attr)
            visitor = EvalRefVisitor(protected_xml_ids=protected_xml_ids)
            visitor.visit(tree)
            result.extend(dk(diff_file, field.start_lineno, field.end_lineno) for dk in visitor.diagnostic_kinds)
    elif element.tag == 'template':
        template = element
        id_attr = template.attrib.get('inherit_id')
        if id_attr and is_ref_risky(id_attr) and 'forcecreate' not in template.attrib:
            result.append(XML_INHERIT_ID(diff_file, template.start_lineno, template.end_lineno))
    return result


def _get_protected_xml_ids() -> set[str]:
    """Get protected records from all Python files in addons directories.
    
    Scans for comments in the format "# PROTECT module.record_name" in Python files
    
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
    _logger.info('Getting protected records from Python files')
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
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # cls.protected_xml_ids = set()
        cls.protected_xml_ids = _get_protected_xml_ids()

    def test_env_ref_usage(self):
        """Check for env.ref calls without raise_if_not_found=False."""
        for diff_file in self.diff_files['.py'].values():
            if not os.path.exists(diff_file.path):
                continue
            if not diff_file.module_name or diff_file.module_name.startswith('test_') or diff_file.path_to_module.startswith('tests/'):
                continue
            self.diagnostices.extend(check_ref_for_python_file(diff_file, self.protected_xml_ids))

    def test_data_xml_ref_usage(self):
        """Check for ref for other modules."""
        module_files: dict[str, list[DiffFile]] = defaultdict(list)
        for diff_file in self.diff_files['.xml'].values():
            if diff_file.module_name and diff_file.module_name != 'base' and not diff_file.module_name.startswith('test_'):
                module_files[diff_file.module_name].append(diff_file)

        for module_name, diff_files in module_files.items():
            manifest = get_manifest(module_name)
            if not manifest:
                continue
            data_files = set(manifest['data'])
            demo_files = set(manifest['demo'])
            for diff_file in diff_files:
                if diff_file.path_to_module in demo_files:
                    continue
                init = diff_file.path_to_module in data_files
                if not os.path.exists(diff_file.path):
                    continue
                for element in self.get_xml_diff_elements(diff_file.path):
                    self.diagnostices.extend(check_ref_for_data_xml_element(element, diff_file, init, self.protected_xml_ids))

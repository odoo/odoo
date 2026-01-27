import ast
import logging
import mmap
import os
import tokenize
from collections.abc import Collection
from lxml import etree
from pathlib import Path
from typing import Literal
from unidiff import PatchedFile

from odoo.tests.diffcase import DiffCase, DiffFile, DiagnosticKind, DiagnosticMessage
from odoo.modules.module import _get_manifest_cached, get_modules, get_module_path
from odoo.tools.convert import nodeattr2bool, xml_import

_logger = logging.getLogger(__name__)


PY_ENV_REF = DiagnosticKind(
    name='ref_env_call',
    body='Found env.ref() calls without raise_if_not_found=False',
    suggestion='Add raise_if_not_found=False to the env.ref() call'
)

PY_ENV_REF_DELETABLE = DiagnosticKind(
    name='ref_env_call_deletable',
    body='Found env.ref() calls without raise_if_not_found=False and the reference is handled with raise_if_not_found=False somewhere else',
    suggestion='Add raise_if_not_found=False to the env.ref() call'
)

XML_ID_FORCECREATE = DiagnosticKind(
    name='xml_id_forcecreate',
    body='Found record id for foreign module without forcecreate',
    suggestion='Add forcecreate="1" to the record'
)

XML_ID_NOUPDATE = DiagnosticKind(
    name='xml_id_noupdate',
    body='Found record id for foreign module with forcecreate="0" but not in "noupdate"',
    suggestion='Move the record data to noupdate="1"'
)

XML_REF = DiagnosticKind(
    name='xml_ref',
    body='Found field ref for foreign module',
    suggestion='Use eval()'
)

XML_REF_DELETABLE = DiagnosticKind(
    name='xml_ref_deletable',
    body='Found field ref for foreign module and the reference is handled with raise_if_not_found=False somewhere else',
    suggestion='Use eval()'
)

XML_EVAL = DiagnosticKind(
    name='xml_eval',
    body='Found eval uses ref() for foreign module without raise_if_not_found=False',
    suggestion='Add raise_if_not_found=False to the ref() call'
)

XML_EVAL_DELETABLE = DiagnosticKind(
    name='xml_eval_deletable',
    body='Found eval uses ref() for foreign module without raise_if_not_found=False and the reference is handled with raise_if_not_found=False somewhere else',
    suggestion='Add raise_if_not_found=False to the ref() call'
)


class EvalRefVisitor(ast.NodeVisitor):
    def __init__(self, protected_xml_ids=None, deletable_xml_ids=None, mode: Literal['diagnose', 'find_deletable'] = 'diagnose'):
        self.protected_xml_ids = set() if protected_xml_ids is None else protected_xml_ids
        self.deletable_xml_ids = set() if deletable_xml_ids is None else deletable_xml_ids
        self.mode = mode

        self.diagnostic_kinds: list[DiagnosticKind] = []

    def _check_ref(self, node) -> None:
        if not node.args:
            return None
        ref = node.args[0]
        if isinstance(ref, ast.Constant) and ref.value in self.protected_xml_ids:
            return None

        raise_if_not_found = True  # default to True
        for keyword in node.keywords:
            if keyword.arg == 'raise_if_not_found':
                if isinstance(keyword.value, ast.Constant) and keyword.value.value is False:
                    raise_if_not_found = False

        if raise_if_not_found:
            if self.mode == 'diagnose':
                if isinstance(ref, ast.Constant) and ref.value in self.deletable_xml_ids:
                    diagnostic_kind = PY_ENV_REF_DELETABLE
                else:
                    diagnostic_kind = PY_ENV_REF
                self.diagnostic_kinds.append(diagnostic_kind)
        elif self.mode == 'find_deletable' and isinstance(ref, ast.Constant):
            self.deletable_xml_ids.add(ref.value)

    def visit_Call(self, node):
        """Check for env.ref calls."""
        if isinstance(node.func, ast.Name) and node.func.id == 'ref':
            self._check_ref(node)

        self.generic_visit(node)


class FileEnvRefVisitor(ast.NodeVisitor):
    def __init__(self, diff_file: DiffFile, protected_xml_ids=None, deletable_xml_ids=None, mode: Literal['diagnose', 'find_deletable'] = 'diagnose'):
        self.diff_file = diff_file
        self.protected_xml_ids = set() if protected_xml_ids is None else protected_xml_ids
        self.deletable_xml_ids = set() if deletable_xml_ids is None else deletable_xml_ids
        self.mode = mode

        self.diagnostics: list[DiagnosticMessage] = []
        self.env_ref_names = set()  # Track variables that store env.ref
        self.try_except_value_error: list[dict] = []  # Track try ... except ValueError blocks

    def _check_ref(self, node) -> None:
        if self.mode == 'diagnose' and not self._is_node_in_diff(node):
            return None
        if not node.args:
            return None
        ref = node.args[0]
        if isinstance(ref, ast.Constant) and ref.value in self.protected_xml_ids:
            return None

        raise_if_not_found = True  # default to True
        for keyword in node.keywords:
            if keyword.arg == 'raise_if_not_found':
                if isinstance(keyword.value, ast.Constant) and keyword.value.value is False:
                    raise_if_not_found = False

        if raise_if_not_found and not self._is_in_value_error_handler(node):
            if self.mode == 'diagnose':
                if isinstance(ref, ast.Constant) and ref.value in self.deletable_xml_ids:
                    diagnostic_kind = PY_ENV_REF_DELETABLE
                else:
                    diagnostic_kind = PY_ENV_REF
                self.diagnostics.append(diagnostic_kind(self.diff_file, node.lineno, node.end_lineno))
        elif self.mode == 'find_deletable' and isinstance(ref, ast.Constant):
            self.deletable_xml_ids.add(ref.value)

    def _is_node_in_diff(self, node):
        """Check if any line of the node is in the diff"""
        return self.diff_file.is_lineno_in_diff(node.lineno, node.end_lineno)

    def _is_in_value_error_handler(self, node):
        """Check if the node is within a try block that handles ValueError."""
        for try_block in self.try_except_value_error:
            if try_block['start'] <= node.lineno <= try_block['end']:
                return True
        return False

    def visit_Try(self, node):
        """Record the try ... except ValueError block which can safely handle ref() calls"""
        except_value_error = False
        for handler in node.handlers:
            if isinstance(handler.type, ast.Name) and handler.type.id == 'ValueError':
                except_value_error = True
            elif isinstance(handler.type, ast.Tuple):
                for exc in handler.type.elts:
                    if isinstance(exc, ast.Name) and exc.id == 'ValueError':
                        except_value_error = True

        if except_value_error:
            self.try_except_value_error.append({
                'start': node.body[0].lineno,
                'end': node.body[-1].lineno,
            })
        self.generic_visit(node)
        if except_value_error:
            self.try_except_value_error.pop()

    def visit_Assign(self, node):
        """Record ref_=env.ref to check ref_() in visit_Call"""
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            value = node.value
            if (isinstance(value, ast.Attribute) and value.attr == 'ref' and
                isinstance(value.value, (ast.Name, ast.Attribute))):
                current = value.value

                if (isinstance(current, ast.Attribute) and current.attr == 'env') or \
                    (isinstance(current, ast.Name) and current.id == 'env'):
                    self.env_ref_names.add(node.targets[0].id)
        self.generic_visit(node)

    def visit_Call(self, node):
        """Check env.ref() and ref_() calls recorded in visit_Assign"""
        if isinstance(node.func, ast.Attribute) and node.func.attr == 'ref':
            current = node.func.value

            if isinstance(current, ast.Attribute) and current.attr == 'env':
                # xxx.env.ref()
                self._check_ref(node)
            elif isinstance(current, ast.Name) and current.id == 'env':
                # env.ref()
                self._check_ref(node)

        elif isinstance(node.func, ast.Name) and node.func.id in self.env_ref_names:
            # ref_=env.ref and check ref_()
            self._check_ref(node)

        self.generic_visit(node)


def check_ref_for_python_file(diff_file: DiffFile, protected_xml_ids: Collection[str] = (), deletable_xml_ids: Collection[str] = ()) -> list[DiagnosticMessage]:
    _logger.info('Checking %s', diff_file.path)
    with open(diff_file.path, encoding="utf-8") as f:
        content = f.read()
    try:
        tree = ast.parse(content)
        visitor = FileEnvRefVisitor(diff_file, protected_xml_ids, deletable_xml_ids)
        visitor.visit(tree)
        return visitor.diagnostics
    except SyntaxError:
        _logger.error('Syntax error in %s', diff_file.path)
        return []


def check_ref_for_data_xml_element(element: etree._Element, linenos: tuple[int, int], diff_file: DiffFile, noupdate: bool = False, protected_xml_ids: Collection[str] = (), deletable_xml_ids: Collection[str] = ()) -> list[DiagnosticMessage]:

    def is_ref_risky(ref: str) -> bool:
        xml_id = ref if '.' in ref else f'{diff_file.module_name}.{ref}'
        if xml_id in protected_xml_ids:
            return False
        # if the file is a data file we trust all reference for the current module's records,
        # in case these records are created in another file while installing the module
        return not xml_id.startswith(f'{diff_file.module_name}.')

    diagnostics = []
    if element.tag == 'record':
        id_attr = element.attrib.get('id')
        if not (id_attr and is_ref_risky(id_attr)):
            return diagnostics
        forcecreate = nodeattr2bool(element.attrib, 'forcecreate', True)
        # for non-existing risky foreign module xmlid
        if 'forcecreate' not in element.attrib:
            # ``Exception("Cannot update missing record")``
            diagnostics.append(XML_ID_FORCECREATE(diff_file, *linenos))
        elif not noupdate and not forcecreate:
            # ``Exception("Cannot update missing record")``
            diagnostics.append(XML_ID_NOUPDATE(diff_file, *linenos))

    elif element.tag == 'field':
        ref_attr = element.attrib.get('ref')
        if ref_attr:
            if is_ref_risky(ref_attr):
                diagnostics.append(XML_REF(diff_file, *linenos))
        if eval_attr := element.attrib.get('eval'):
            # parse as python ast, check function ref
            # add to issues if ref for foreign module without raise_if_not_found=False
            tree = ast.parse(eval_attr.strip())
            visitor = EvalRefVisitor(protected_xml_ids=protected_xml_ids, deletable_xml_ids=deletable_xml_ids)
            visitor.visit(tree)
            diagnostics.extend({
                PY_ENV_REF: XML_EVAL,
                PY_ENV_REF_DELETABLE: XML_EVAL_DELETABLE,
            }[dk](diff_file, *linenos)
            for dk in visitor.diagnostic_kinds)
    return diagnostics


def _get_module_model_files(module: str) -> list[str]:
    """get all python files in module/ and module/models/ directory"""
    if not (module_path := get_module_path(module)):
        return []
    python_files = [str(f) for f in Path(module_path).glob('*.py') if not f.name.startswith('__')]
    for root, _, files in os.walk(os.path.join(module_path, 'models')):
        python_files.extend(os.path.join(root, f) for f in files if f.endswith('.py'))
    return python_files


def _get_module_data_xml_files(module: str) -> list[str]:
    """get all data xml files in manifest['data']"""
    if not (module_path := get_module_path(module)):
        return []
    manifest = _get_manifest_cached(module)
    return [
        os.path.join(module_path, data_file)
        for data_file in manifest['data']
        if data_file.endswith('.xml')
    ]


def _get_protected_xml_ids() -> set[str]:
    """Get protected records from all python files in addons.

    Scans for comments in the format "# PROTECT module.record_name" in Python files

    Returns:
        set[str]: Set of protected record external IDs
    """

    protected = set()
    _logger.info('Getting protected records from Python files')

    for module in get_modules():
        if module.startswith('test_'):
            continue
        for py_file in _get_module_model_files(module):
            with open(py_file, 'rb') as f:
                try:
                    with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                        if mm.find(b'# PROTECT ') == -1:
                            continue
                except ValueError as e:
                    if e.args == ('cannot mmap an empty file',):
                        continue
                    raise
            try:
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


def _get_deletable_xml_ids(protected_xml_ids: set[str]) -> set[str]:
    """Get deletable records from all python files in addons.

    Scans codes with ``ref(xmlid, raise_if_not_found=False)`` in Python files and xml files
    and with ``ref(xmlid)`` in ``try ... except ValueError`` blocks in Python files
    these xmlids are treated as deletable

    Returns:
        set[str]: Set of deletable record external IDs
    """
    deletable_xml_ids = set()
    for module in get_modules():
        if module.startswith('test_'):
            continue
        for py_file in _get_module_model_files(module):
            with open(py_file, encoding='utf-8') as f:
                content = f.read()
            try:
                tree = ast.parse(content)
                visitor = FileEnvRefVisitor(DiffFile('', PatchedFile()), protected_xml_ids, deletable_xml_ids, mode='find_deletable')
                visitor.visit(tree)
            except etree.XMLSyntaxError:
                # usually because the xml is empty
                continue
        for xml_file in _get_module_data_xml_files(module):
            with open(xml_file, 'rb') as f:
                try:
                    elements = etree.parse(f, None)
                except etree.XMLSyntaxError:
                    # usually because the xml is empty
                    continue
            for element in elements.iter():
                if element.tag == 'field' and (eval_attr := element.attrib.get('eval')):
                    tree = ast.parse(eval_attr.strip())
                    visitor = EvalRefVisitor(protected_xml_ids, deletable_xml_ids, mode='find_deletable')
                    visitor.visit(tree)
    return deletable_xml_ids


class TestRef(DiffCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.protected_xml_ids = _get_protected_xml_ids()
        cls.deletable_xml_ids = _get_deletable_xml_ids(cls.protected_xml_ids)

    def test_env_ref_usage(self):
        """Check for env.ref calls without raise_if_not_found=False."""
        for diff_file in self.diff_files['.py'].values():
            if not os.path.exists(diff_file.path):
                continue
            if not diff_file.module_name or diff_file.module_name.startswith('test_') or diff_file.path_to_module.startswith('tests/'):
                continue
            self.diagnostices.extend(check_ref_for_python_file(diff_file, self.protected_xml_ids, self.deletable_xml_ids))

    def test_data_xml_ref_usage(self):
        """Check for ref for foreign modules."""
        for diff_file in self.diff_files['.xml'].values():
            if not os.path.exists(diff_file.path):
                continue
            manifest = _get_manifest_cached(diff_file.module_name)
            if not manifest or diff_file.module_name == 'base' or diff_file.module_name.startswith('test_'):
                continue
            if not diff_file.path_to_module in manifest['data']:
                continue
            protected_xml_ids = set(self.protected_xml_ids)
            elements, elements_info = self.parse_xml_file(diff_file.path)

            _logger.info('Checking %s', diff_file.path)
            noupdates = {None: False}  # dummy element None as the parent for the root element
            for element in elements.iter():
                if not isinstance(element.tag, str):
                    # skip comment and pi
                    continue
                element_info = elements_info[element]
                parent = element.getparent()
                if element.tag in xml_import.DATA_ROOTS:
                    noupdate = noupdates[element] = nodeattr2bool(element, 'noupdate', noupdates[parent])
                else:
                    noupdate = noupdates[element] = noupdates[parent]

                if element.tag == 'record':
                    # Check if this record can be created. If creatable, it becomes a valid reference for subsequent data in
                    # this file, so add it to the local protected_xml_ids
                    if not (id_attr := element.attrib.get('id')):
                        continue
                    xml_id = id_attr if '.' in id_attr else f'{diff_file.module_name}.{id_attr}'
                    forcecreate = nodeattr2bool(element, 'forcecreate')  # explicit truthy forcecreate
                    if not xml_id.startswith(diff_file.module_name + '.') and forcecreate:
                        # forcecreated records for foreign modules can be safely referenced
                        protected_xml_ids.add(xml_id)

                if element_info.start_tag_in_diff:
                    self.diagnostices.extend(check_ref_for_data_xml_element(element, element_info.start_tag_linenos, diff_file, noupdate, protected_xml_ids, self.deletable_xml_ids))

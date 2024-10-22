import csv
import functools
import io
import logging
import re
from ast import literal_eval
from collections import defaultdict, namedtuple
from typing import Iterator

from lxml import etree

from odoo.addons.base.models.ir_model import model_xmlid
from odoo.models import MetaModel
from odoo.tools import config

_logger = logging.getLogger('makeiraccess')
_silent = logging.getLogger('silent')
_silent.setLevel(logging.CRITICAL)

Access = namedtuple('Access', 'id, name, model, group, operations, domain')
IrRule = namedtuple('IrRule', 'id, name, model, groups, operations, domain')

REF_RE = re.compile(r"ref\(['\"]([\w\.]+)['\"]\)")
TRUE_RE = re.compile(r"\[\]|\[\(1, *'=', *1\)\]")

XML_TAGS = ('delete', 'function', 'menuitem', 'record', 'template')

MODES = {
    'r': 'perm_read',
    'w': 'perm_write',
    'c': 'perm_create',
    'd': 'perm_unlink',
}

WELCOME_MESSAGE = """
This script is generating ir.access.csv files from existing data files.

The logging messages should be interpreted as:
 - INFO: normal operation
 - WARNING: partially handled case, should be checked and potentially fixed up
 - ERROR: not handled case, requires manual fixup

This script converts ir.rule records to corresponding ir.access records,
limiting the operations to the ones allowed by ir.model.access records from
the module and its dependencies.
"""


#
# upgrade(file_manager) creates an object that performs the upgrade at creation
#
class upgrade:
    def __init__(self, file_manager):
        self.file_manager = file_manager

        modules = {file.addon.name: None for file in file_manager}
        if not modules:
            return

        # set up addons_path, in order to enable importing modules
        addons_path = ','.join(file_manager.addons_path)
        config.parse_config([f'--addons-path={addons_path}'])

        print(WELCOME_MESSAGE)

        file_manager.print_progress(0, len(modules))
        for index, module in enumerate(modules):
            self.generate(module)
            file_manager.print_progress(index + 1, len(modules))

    def generate(self, module: str):
        """ Generate a file ``ir.access.csv`` for the given module. """
        logger = logging.getLogger(module)

        manifest = self.get_manifest(module)
        if not any('security' in fname for fname in manifest['data']):
            return
        if 'security/ir.access.csv' in manifest['data'] or 'ir.access.csv' in manifest['data']:
            logger.info("File security/ir.access.csv exists already, skipping")
            return

        # determine filename before files are removed from manifest
        has_security = any(fname.startswith('security/') for fname in manifest['data'])
        file_name = 'security/ir.access.csv' if has_security else 'ir.access.csv'

        logger.info("extracting existing accesses")

        #
        # First determine permitted operations in module.
        #
        # Let's see how ACLs "propagate" from group to group.  If group A implies
        # group B (in terms of sets: A ≤ B), then every ir.model.access on B also
        # applies to A.  It's exactly what has_permission() below tests.
        #
        permissions = self.get_permissions(module)
        group_implied = self.get_group_definitions()

        @functools.cache
        def has_permission(model, group, operation):
            return (model, group, operation) in permissions or any(
                has_permission(model, implied, operation)
                for implied in group_implied[group]
            )

        #
        # Second, infer ir.access records from ir.model.access and ir.rule.
        #
        # For every Model, Group, Operation, we have:
        #
        # ir.rule(Model, Group, Operation, Domain) and has_permission(Model, Group, Operation)
        #   => ir.access(Model, Group, Operation, Domain)
        #
        # no ir.rule(Model, Group, Operation, Domain) and has_permission(Model, Group, Operation)
        #   => ir.access(Model, Group, Operation, [])
        #

        # first, consider explicit entries from ir.rules
        # {model: {group: [(operations, domain, name)]}}
        explicit = defaultdict(lambda: defaultdict(list))
        for rule in self.extract_rules(module):
            model = rule.model
            for group in rule.groups or [None]:
                if group is None:
                    operations = set(rule.operations)
                else:
                    operations = {op for op in rule.operations if has_permission(model, group, op)}
                    if not operations:
                        logger.warning("ir.access without operations for model %s and group %s", model, group)
                explicit[model][group].append((operations, rule.domain, rule.name))

        # second, consider implicit entries from ir.model.access
        # {model: {group: [(operations, domain, name)]}}
        ir_access = defaultdict(lambda: defaultdict(list))
        for acl in self.extract_accesses(module):
            # this prepares entries in the same order as in ir.model.access
            implicit = ir_access[acl.model][acl.group]
            # only consider operations from acl that do not appear in explicit accesses
            operations = set(acl.operations).difference(*(
                access[0] for access in explicit[acl.model][acl.group]
            ))
            if operations:
                implicit.append((operations, make_domain(), acl.name))

        # third, merge both (implicit then explicit)
        for model, model_accesses in explicit.items():
            for group, accesses in model_accesses.items():
                ir_access[model][group].extend(accesses)

        if not ir_access:
            return

        #
        # Create ir.access.csv
        #

        logger.info("generating ir.access.csv")

        with io.StringIO(newline='') as output:
            writer = csv.writer(output, lineterminator='\n')
            writer.writerow(["id", "model_id", "group_id/id", "mode", "domain", "name"])
            xids = set()
            for model, model_accesses in ir_access.items():
                for group, accesses in model_accesses.items():
                    full_xids = len(accesses) > 1
                    for operations, domain, name in accesses:
                        mode = "".join(char for char, op in MODES.items() if op in operations)
                        xid = make_access_xid(model, group, mode if full_xids else "")
                        if xid in xids:
                            logger.error(
                                "duplicate external id %r for %r in %r, please fix it",
                                xid, model, group,
                            )
                        xids.add(xid)
                        writer.writerow([xid, model, group, mode, domain, name])
            content = output.getvalue()

        self.set_file_content(module, file_name, content)
        self.add_to_manifest(module, file_name)

    def get_file_content(self, module: str, file_name: str) -> str:
        """ Return the content of the given file. """
        return self.file_manager.get_file(module, file_name).content

    def set_file_content(self, module: str, file_name: str, content: str | None):
        """ Update the content of the given file; set it to ``None`` to delete it. """
        self.file_manager.get_file(module, file_name).content = content

    @functools.cache
    def get_manifest(self, module: str) -> dict:
        """ Return the manifest dict of the given module. """
        content = self.get_file_content(module, "__manifest__.py")
        manifest = literal_eval(content)
        manifest.setdefault('depends', [])
        manifest.setdefault('data', [])
        return manifest

    def add_to_manifest(self, module: str, file_name: str):
        """ Add the given file to its module's manifest. """

        # add it to the manifest's dict
        manifest = self.get_manifest(module)
        assert file_name not in manifest['data'], f"File {file_name!r} found in manifest['data']"
        manifest['data'].append(file_name)

        # add it to the manifest's file
        content = self.get_file_content(module, "__manifest__.py")

        if match := re.search(r"""(["']data["']\s*:\s*)(\[\s*)(\])""", content):
            # empty list, insert just before closing bracket
            position = match.start(3)
            content = f"{content[:position]}'{file_name}'{content[position:]}"

        elif match := re.search(r"""(["']data["']\s*:\s*)(\[[^\]]*\n)(\s*\])""", content):
            # non-empty list on several lines, add a line before closing bracket
            position = match.start(3)
            spaces = match[3][:-1] + '    '
            content = f"{content[:position]}{spaces}'{file_name}',\n{content[position:]}"

        elif match := re.search(r"""(["']data["']\s*:\s*)(\[[^\]]*)(\])""", content):
            # badly written non-empty list, insert just before closing bracket
            position = match.start(3)
            content = f"{content[:position]}, '{file_name}'{content[position:]}"

        else:
            logging.getLogger(module).error("Cannot add %s to manifest, please add manually", file_name)
            return

        self.set_file_content(module, "__manifest__.py", content)

    def remove_from_manifest(self, module: str, file_name: str):
        """ Remove the given file from its module's manifest. """

        # remove it from the manifest's dict
        manifest = self.get_manifest(module)
        assert file_name in manifest['data'], f"File {file_name!r} not found in manifest['data']"
        manifest['data'].remove(file_name)

        # remove it from the manifest's file
        file_pattern = re.escape(str(file_name))
        pattern = rf"\s*(\"{file_pattern}\"|'{file_pattern}'),?"

        content = self.get_file_content(module, "__manifest__.py")
        content = re.sub(pattern, "", content, flags=re.MULTILINE)
        self.set_file_content(module, "__manifest__.py", content)

    def get_permissions(self, module: str) -> set[tuple[str, str, str]]:
        """ Return all the permissions that are available when the given module
        is installed.  The result is a set of triples ``(model, group, operation)``.
        """
        # determine all (direct and indirect) dependencies
        todo = [module]
        deps = {'base'}
        while todo:
            mod = todo.pop()
            if mod not in deps:
                deps.add(mod)
                todo.extend(self.get_manifest(mod)['depends'])

        return set().union(*(self._get_permissions(mod) for mod in deps))

    @functools.cache
    def _get_permissions(self, module: str) -> list[tuple[str, str, str]]:
        """ Return the permissions that are defined by the given module.
        The result is a list of triples ``(model, group, operation)``.
        """
        return [
            (access.model, access.group, operation)
            for access in self.extract_accesses(module, remove=False)
            if access.group
            for operation in access.operations
        ]

    def extract_accesses(self, module: str, remove=True) -> Iterator[Access]:
        """ Extract ir.model.access or ir.access records from the given module. """
        manifest = self.get_manifest(module)
        for file_name in manifest['data']:
            if 'security' in file_name or 'access' in file_name:
                if file_name.endswith('.csv'):
                    yield from self.extract_accesses_from_csv(module, file_name, remove)
                elif file_name.endswith('.xml'):
                    yield from self.extract_accesses_from_xml(module, file_name, remove)

    def extract_accesses_from_csv(self, module: str, file_name: str, remove: bool) -> Iterator[Access]:
        logger = logging.getLogger(module) if remove else _silent

        if file_name.endswith('ir.model.access.csv'):
            def get_operations(line_data):
                return [op for op in MODES.values() if int(line_data[op] or "0")]

        elif file_name.endswith('ir.access.csv'):
            def get_operations(line_data):
                mode = line_data['mode']
                return [op for char, op in MODES.items() if char in mode]

        else:
            logger.error("unexpected CSV file, skipping %s", file_name)
            return

        content = self.get_file_content(module, file_name)
        reader = csv.reader(io.StringIO(content, newline=''), lineterminator='\n')

        fields = next(reader)
        model_field = next(field for field in fields if field.startswith('model_id'))
        group_field = next(field for field in fields if field.startswith('group_id'))

        for line in reader:
            if not line:
                continue

            line_data = dict(zip(fields, line, strict=True))
            name = line_data['name']

            xid = with_prefix(module, line_data['id'])
            if not xid.startswith(f"{module}."):
                logger.error("modified ir.model.access, skipping %s in %s", xid, file_name)
                continue

            model = self.get_model_name(module, line_data[model_field])
            if not model:
                logger.error("ir.model.access without model, skipping %s in %s", xid, file_name)
                continue

            operations = get_operations(line_data)
            if not operations:
                logger.warning("ir.model.access without operations, skipping %s in %s", xid, file_name)
                continue

            domain = make_domain(line_data.get('domain'))

            group = line_data[group_field]

            if group:
                yield Access(xid, name, model, with_prefix(module, group), operations, domain)
            else:
                logger.info("ir.model.access without group, using groups employee, portal, public instead: %s in %s", xid, file_name)
                yield Access(xid, name, model, 'base.group_user', operations, domain)
                yield Access(xid, name, model, 'base.group_portal', operations, domain)
                yield Access(xid, name, model, 'base.group_public', operations, domain)

        if remove:
            self.set_file_content(module, file_name, None)
            self.remove_from_manifest(module, file_name)

    def extract_accesses_from_xml(self, module: str, file_name: str, remove: bool) -> Iterator[Access]:
        logger = logging.getLogger(module) if remove else _silent
        tree = etree.fromstring(self.get_file_content(module, file_name).encode())
        nodes = []

        for node in tree.xpath("//record[@model='ir.model.access']"):
            xid = with_prefix(module, node.get('id'))
            if not xid.startswith(f"{module}."):
                logger.error("modified ir.model.access, skipping %s in %s", xid, file_name)
                continue

            if node.find("./field[@name='active']") is not None:
                logger.error("ir.model.access with field 'active', skipping %s in %s", xid, file_name)
                continue

            name = name_node.text if (name_node := node.find("./field[@name='name']")) is not None else None

            model = self.get_model_name(module, get_xml_model_xid(node))
            if not model:
                logger.error("ir.model.access without model, skipping %s in %s", xid, file_name)
                continue

            operations = [
                op
                for op in MODES.values()
                if (opnode := node.find(f"./field[@name='{op}']")) is not None
                and literal_eval(opnode.get('eval') or opnode.text)
            ]
            if not operations:
                logger.warning("ir.model.access without operations, skipping %s in %s", xid, file_name)
                continue

            domain = make_domain()

            group = get_xml_group_xid(node)

            if group:
                yield Access(xid, name, model, with_prefix(module, group), operations, domain)
            else:
                logger.info("ir.model.access without group, using groups employee, portal, public instead: %s in %s", xid, file_name)
                yield Access(xid, name, model, 'base.group_user', operations, domain)
                yield Access(xid, name, model, 'base.group_portal', operations, domain)
                yield Access(xid, name, model, 'base.group_public', operations, domain)

            nodes.append(node)

        if remove and nodes:
            self.remove_from_xml_file(module, file_name, tree, nodes)

    def extract_rules(self, module: str, remove=True) -> Iterator[IrRule]:
        """ Extract ir.rule records from the given module. """
        manifest = self.get_manifest(module)
        for file_name in manifest['data']:
            if 'security' in file_name and file_name.endswith('.xml'):
                yield from self.extract_rules_from_xml(module, file_name, remove)

    def extract_rules_from_xml(self, module: str, file_name: str, remove: bool) -> Iterator[IrRule]:
        logger = logging.getLogger(module) if remove else _silent
        tree = etree.fromstring(self.get_file_content(module, file_name).encode())
        nodes = []

        for node in tree.xpath("//record[@model='ir.rule']"):
            xid = with_prefix(module, node.get('id'))
            if not xid.startswith(f"{module}."):
                logger.error("modified ir.rule, skipping %s in %s", xid, file_name)
                continue

            if node.find("./field[@name='active']") is not None:
                logger.error("ir.rule with field 'active', skipping %s in %s", xid, file_name)
                continue

            name = name_node.text if (name_node := node.find("./field[@name='name']")) is not None else None

            model = self.get_model_name(module, get_xml_model_xid(node))
            if not model:
                logger.error("ir.rule without model, skipping %s in %s", xid, file_name)
                continue

            groups = [
                with_prefix(module, match[1])
                for group_node in node.findall("./field[@name='groups']")
                for match in REF_RE.finditer(group_node.get('eval'))
            ]

            operations = [
                op
                for op in MODES.values()
                if (opnode := node.find(f"./field[@name='{op}']")) is None
                or literal_eval(opnode.get('eval'))
            ]
            if not operations:
                logger.warning("ir.rule without operations, skipping %s in %s", xid, file_name)
                continue

            domain = make_domain(node.findtext("./field[@name='domain_force']"))

            yield IrRule(xid, name, model, groups, operations, domain)
            nodes.append(node)

        if remove and nodes:
            self.remove_from_xml_file(module, file_name, tree, nodes)

    def remove_from_xml_file(self, module: str, file_name: str, tree: etree.Element, nodes: list):
        """ Remove the given nodes from the XML tree, and save the result to file. """
        for node in nodes:
            while (parent := node.getparent()) is not None:
                parent.remove(node)
                node = parent
                if len(node):
                    break

        if any(tree.find(f".//{tag}") is not None for tag in XML_TAGS):
            content = etree.tostring(tree).decode() + "\n"
            self.set_file_content(module, file_name, content)
        else:
            self.set_file_content(module, file_name, None)
            self.remove_from_manifest(module, file_name)

    def get_model_name(self, module: str, xid: str | None) -> str | None:
        """ Retrieve the model name from a model's external id or model name. """
        if not xid:
            return None
        model_xid = with_prefix(module, xid)
        return self.get_model_xids().get(model_xid, xid)

    @functools.cache
    def get_model_xids(self) -> dict[str, str]:
        """ Return a mapping from model external ids to model names. """
        _logger.info("Building mapping for model xids")
        for module in self.file_manager.get_modules():
            try:
                __import__(f'odoo.addons.{module}')
            except Exception:
                pass

        return {
            model_xmlid(module, cls._name): cls._name
            for module, classes in MetaModel.module_to_models.items()
            for cls in classes
        }

    @functools.cache
    def get_group_definitions(self) -> dict[str, list[str]]:
        """ Return a mapping from groups to their implied groups. """
        group_implied = defaultdict(list)
        for module in self.file_manager.get_modules():
            manifest = self.get_manifest(module)
            for file_name in manifest['data']:
                if 'security' in file_name and file_name.endswith('.xml'):
                    for xid, implied_xids in self.extract_groups_from_xml(module, file_name):
                        group_implied[xid].extend(implied_xids)
        return group_implied

    def extract_groups_from_xml(self, module: str, file_name: str) -> Iterator[tuple[str, list[str]]]:
        """ Retrieve group definitions from a given XML file. """
        tree = etree.fromstring(self.get_file_content(module, file_name).encode())

        for node in tree.xpath("//record[@model='res.groups']"):
            xid = with_prefix(module, node.get('id'))
            implied_xids = [
                with_prefix(module, match[1])
                for implied_node in node.findall("./field[@name='implied_ids']")
                for match in REF_RE.finditer(implied_node.get('eval'))
            ]
            yield (xid, implied_xids)


def with_prefix(module: str, xid: str) -> str:
    """ Return a fully qualified external id. """
    return xid and (xid if '.' in xid else f"{module}.{xid}")


def get_xml_model_xid(node) -> str | None:
    """ Retrieve the value of field 'model_id' from the given XML record. """
    model_node = node.find("./field[@name='model_id']")
    if model_node is None:
        return None
    if (model := model_node.get('ref')):
        return model
    domain = model_node.get('search')
    for item in literal_eval(domain):
        if item[0] == 'model' and item[1] == '=':
            return f"model_{item[2].replace('.', '_')}"
    return None


def get_xml_group_xid(node) -> str | None:
    """ Retrieve the value of field 'group_id' from the given XML record. """
    group_node = node.find("./field[@name='group_id']")
    if group_node is None:
        return None
    return group_node.get('ref')


def make_domain(domain: str | None = None) -> str:
    """ Normalize the given domain. """
    return "" if domain is None or TRUE_RE.match(domain) else domain


def make_access_xid(model: str, group: str, mode: str) -> str:
    """ Make an external id for the given model, group and mode. """
    model_part = model.replace('.', '_')
    group_part = group.split('.', 1)[1] if group else "global"
    if mode:
        return f"access_{model_part}_{group_part}_{mode}"
    return f"access_{model_part}_{group_part}"

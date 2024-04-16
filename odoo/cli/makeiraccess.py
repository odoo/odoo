from __future__ import annotations
from typing import TYPE_CHECKING

import csv
import functools
import logging
import optparse
import re
from ast import literal_eval
from collections import defaultdict, namedtuple
from pathlib import Path

from lxml import etree

from . import Command
from odoo.addons.base.models.ir_model import model_xmlid
from odoo.models import MetaModel
from odoo.modules import get_modules, get_module_path, get_manifest
from odoo.tools import config

if TYPE_CHECKING:
    from typing import Iterator

_logger = logging.getLogger(__name__)
_extract_logger = logging.getLogger(f"{__name__}.extract")

REF_RE = re.compile(r"ref\(['\"]([\w\.]+)['\"]\)")
TRUE_RE = re.compile(r"\[\]|\[\(1, *'=', *1\)\]")
GROUP_PART_RE = re.compile(r"\w+\.group_(.+)|\w+\.(.+)")

MODES = {
    'c': 'perm_create',
    'r': 'perm_read',
    'w': 'perm_write',
    'd': 'perm_unlink',
}

WELCOME_MESSAGE = """
This script is generating ir.access.csv files from existing data files.

The logging messages should be interpreted as:
 - INFO: normal operation
 - WARNING: partially handled case, should be checked and potentially fixed up
 - ERROR: not handled case, require manual fixup

This script converts ir.rule records to corresponding ir.access records,
limiting the operations to the ones allowed by ir.model.access records from
the module and its dependencies.
"""


class MakeIrAccess(Command):
    """ Generate ir.access.csv for modules. """
    def run(self, args):
        parser = optparse.OptionParser(
            usage=f"%prog {self.name} [options] [modules]",
            description=(
                "For each module, generate some ir.access.csv file based on "
                "existing ir.model.access and ir.rule records in data files. "
                "The modules are given by positional arguments (separated by commas or spaces). "
                "If none are given, the command uses all modules in addons-path."
            ),
        )
        parser.add_option(
            "--addons-path", dest="addons_path",
            help="specify additional addons paths (separated by commas).",
        )
        parser.add_option(
            "--purge", action="store_true", default=False,
            help="purge existing ir.model.access and ir.rule records from data files. "
        )
        options, args = parser.parse_args(args)

        # set up addons_path, and other things
        config.parse_config([f'--addons-path={options.addons_path}'] if options.addons_path else [])

        self.purge = options.purge

        print(WELCOME_MESSAGE)

        modules = [mod for arg in args for mod in arg.split(",")] or get_modules()
        for module in modules:
            self.generate(module)

    def generate(self, module: str):
        """ Generate a file ``ir.access.csv`` for the given module. """
        manifest = get_manifest(module)
        if not any('security' in file_name for file_name in manifest['data']):
            return

        module_path = Path(get_module_path(module))
        if (module_path / 'security' / 'ir.access.csv').is_file():
            _logger.info("Skip module %s, file security/ir.access.csv exists already", module)
            return

        _logger.info("Process module %s: generating ir.access.csv", module)

        #
        # First determine permitted operations in module
        #
        permissions = get_permissions(module)
        group_implied = get_group_definitions()

        @functools.cache
        def has_permission(model, group, operation):
            return (model, group, operation) in permissions or any(
                has_permission(model, implied, operation)
                for implied in group_implied[group]
            )

        #
        # Extract ir.model.access and ir.rule records from input files
        #
        ir_model_accesses = list(extract_accesses(module, self.purge))
        ir_rules = list(extract_rules(module, self.purge))

        #
        # Convert inputs to equivalent ir.access records
        #
        # First, let's see how ACLs "propagate" from group to group.  If group A
        # implies group B (in terms of sets: A ≤ B), then every ir.model.access on
        # B also applies to A.
        #
        # Second, let's infer ir.access records from ir.model.access and ir.rule:
        #
        # no ir.rule(A, model, operation, domain) and ir.model.access(A, model operation)
        #   => ir.access(A, model, operation, [])
        #
        # ir.rule(A, model, operation, domain) and ir.model.access(A, model, operation)
        #   => ir.access(A, model, operation, domain)
        #
        # ir.rule(A, model, operation, domain) and A implies B and ir.model.access(B, model, operation)
        #   => ir.access(A, model, operation, domain)
        #

        # {model: {group: Implex()}}
        ir_access = defaultdict(lambda: defaultdict(Implex))

        # first, prepare entries from ir.model.access
        for acl in ir_model_accesses:
            ir_access[acl.model][acl.group]

        # second, insert explicit entries from ir.rules
        for rule in ir_rules:
            model = rule.model
            for group in rule.groups or [None]:
                if group is None:
                    operations = set(rule.operations)
                else:
                    operations = {op for op in rule.operations if has_permission(model, group, op)}
                    if not operations:
                        _logger.warning("ir.access without operations, please check ir.rule %s", rule.id)
                explicit = ir_access[model][group].explicit
                explicit.append((operations, rule.domain, rule.name))

        # third, insert implicit entries from ir.model.access
        for acl in ir_model_accesses:
            accesses = ir_access[acl.model][acl.group]
            explicit_operations = set().union(*[access[0] for access in accesses.explicit])
            implicit_operations = set(acl.operations) - explicit_operations
            if implicit_operations:
                accesses.implicit.append((implicit_operations, make_domain(), acl.name))

        if not ir_access:
            return

        #
        # Create ir.access.csv
        #
        file_path = module_path
        if (module_path / 'security').is_dir():
            file_path = file_path / 'security'
        file_path = file_path / 'ir.access.csv'
        with file_path.open('w', newline='') as csvfile:
            writer = csv.writer(csvfile, lineterminator='\n')
            writer.writerow(["id", "model_id", "group_id/id", "mode", "domain", "name"])
            xids = set()

            for model, model_access in ir_access.items():
                for group, implex in model_access.items():
                    accesses = implex.implicit + implex.explicit
                    full_xids = len(accesses) > 1
                    for operations, domain, name in accesses:
                        mode = "".join(char for char, op in MODES.items() if op in operations)
                        xid = make_access_xid(model, group, full_xids and mode)
                        if xid in xids:
                            _logger.error("using duplicate external id %r for %r in %r", xid, model, group)
                        xids.add(xid)
                        writer.writerow([xid, model, group, mode, domain, name])

        # replace ir.model.access.csv by ir.access.csv in manifest
        if self.purge:
            if not any('ir.model.access.csv' in file_name for file_name in manifest['data']):
                _logger.error("Cannot add ir.access.csv to manifest, please add manually")
                return
            manifest_path = module_path / "__manifest__.py"
            with manifest_path.open() as file:
                content = file.read()
            content = content.replace('ir.model.access.csv', 'ir.access.csv')
            with manifest_path.open('w') as file:
                file.write(content)


#
# Helper types and functions
#
Access = namedtuple('Access', 'id, name, model, group, operations, domain')
IrRule = namedtuple('IrRule', 'id, name, model, groups, operations, domain')


class Implex:
    __slots__ = ['implicit', 'explicit']

    def __init__(self):
        self.implicit = []
        self.explicit = []


def extract_accesses(module: str, purge: bool = False) -> Iterator[Access]:
    """ Extract ir.model.access or ir.access records from the given module. """
    module_path = Path(get_module_path(module))
    manifest = get_manifest(module)
    for file_name in manifest['data']:
        if 'security' in file_name or 'access' in file_name:
            if file_name.endswith('.csv'):
                yield from extract_accesses_from_csv(module, module_path / file_name, purge)
            elif file_name.endswith('.xml'):
                yield from extract_accesses_from_xml(module, module_path / file_name, purge)


def extract_accesses_from_csv(module: str, file_path: Path, purge: bool = False) -> Iterator[Access]:
    if file_path.name == 'ir.model.access.csv':
        def get_operations(line_data):
            return [op for op in MODES.values() if int(line_data[op] or "0")]

    elif file_path.name == 'ir.access.csv':
        def get_operations(line_data):
            mode = line_data['mode']
            return [op for char, op in MODES.items() if char in mode]

    else:
        _extract_logger.error("unexpected CSV file, skipping %s", file_path)
        return

    with file_path.open(newline='') as csvfile:
        reader = csv.reader(csvfile)

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
                _extract_logger.error("modified ir.model.access, skipping %s", xid)
                continue

            model = get_model(module, line_data[model_field])
            if not model:
                _extract_logger.error("ir.model.access without model, skipping %s", xid)
                continue

            operations = get_operations(line_data)
            if not operations:
                _extract_logger.warning("ir.model.access without operations, skipping %s", xid)
                continue

            domain = make_domain(line_data.get('domain'))

            group = with_prefix(module, line_data[group_field])

            if group:
                yield Access(xid, name, model, group, operations, domain)
            else:
                _extract_logger.info("ir.model.access without group, using groups employee, portal, public instead: %s", xid)
                yield Access(xid, name, model, 'base.group_user', operations, domain)
                yield Access(xid, name, model, 'base.group_portal', operations, domain)
                yield Access(xid, name, model, 'base.group_public', operations, domain)

    if purge:
        file_path.unlink()


def extract_accesses_from_xml(module: str, file_path: Path, purge: bool = False) -> Iterator[Access]:
    tree = etree.parse(str(file_path))
    nodes = []

    for node in tree.xpath("//record[@model='ir.model.access']"):
        xid = with_prefix(module, node.get('id'))
        if not xid.startswith(f"{module}."):
            _extract_logger.error("modified ir.model.access, skipping %s", xid)
            continue

        if node.find("./field[@name='active']") is not None:
            _extract_logger.error("ir.model.access with field 'active', skipping %s", xid)
            continue

        name = name_node.text if (name_node := node.find("./field[@name='name']")) is not None else None

        model = get_model(module, get_xml_model_xid(node))
        if not model:
            _extract_logger.error("ir.model.access without model, skipping %s", xid)
            continue

        operations = [
            op
            for op in MODES.values()
            if (opnode := node.find(f"./field[@name='{op}']")) is not None
            and literal_eval(opnode.get('eval') or opnode.text)
        ]
        if not operations:
            _extract_logger.warning("ir.model.access without operations, skipping %s", xid)
            continue

        domain = make_domain()

        group = with_prefix(module, get_xml_group_xid(node))

        if group:
            yield Access(xid, name, model, group, operations, domain)
        else:
            _extract_logger.info("ir.model.access without group, using groups employee, portal, public instead: %s", xid)
            yield Access(xid, name, model, 'base.group_user', operations, domain)
            yield Access(xid, name, model, 'base.group_portal', operations, domain)
            yield Access(xid, name, model, 'base.group_public', operations, domain)

        nodes.append(node)

    if purge and nodes:
        for node in nodes:
            node.getparent().remove(node)

        with file_path.open(mode='w') as file:
            file.write(etree.tostring(tree).decode())
            file.write("\n")


def extract_rules(module: str, purge: bool = False) -> Iterator[IrRule]:
    """ Extract ir.rule records from the given module. """
    module_path = Path(get_module_path(module))
    manifest = get_manifest(module)
    for file_name in manifest['data']:
        if 'security' in file_name and file_name.endswith('.xml'):
            yield from extract_rules_from_xml(module, module_path / file_name, purge)


def extract_rules_from_xml(module: str, file_path: Path, purge: bool = False) -> Iterator[IrRule]:
    tree = etree.parse(str(file_path))
    nodes = []

    for node in tree.xpath("//record[@model='ir.rule']"):
        xid = with_prefix(module, node.get('id'))
        if not xid.startswith(module):
            _extract_logger.error("modified ir.rule, skipping %s", xid)
            continue

        if node.find("./field[@name='active']") is not None:
            _extract_logger.error("ir.rule with field 'active', skipping %s", xid)
            continue

        name = name_node.text if (name_node := node.find("./field[@name='name']")) is not None else None

        model = get_model(module, get_xml_model_xid(node))
        if not model:
            _extract_logger.error("ir.rule without model, skipping %s", xid)
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
            _extract_logger.warning("ir.rule without operations, skipping %s", xid)
            continue

        domain = make_domain(node.findtext("./field[@name='domain_force']"))

        yield IrRule(xid, name, model, groups, operations, domain)
        nodes.append(node)

    if purge and nodes:
        for node in nodes:
            node.getparent().remove(node)

        with file_path.open(mode='w') as file:
            file.write(etree.tostring(tree).decode())
            file.write("\n")


def get_permissions(module: str) -> set[tuple[str, str, str]]:
    """ Return all the permissions that are available when the given module is
    installed.  The result is a set of triples ``(model, group, operation)``.
    """
    old_level = _extract_logger.level
    try:
        _extract_logger.setLevel(logging.CRITICAL)
        return get_base_permissions(module).union(*[
            get_permissions(dependency)
            for dependency in get_manifest(module)['depends']
        ])
    finally:
        _extract_logger.setLevel(old_level)


@functools.cache
def get_base_permissions(module: str) -> set[tuple[str, str, str]]:
    """ Return all the permissions that are defined by the given module.  The
    result is a set of triples ``(model, group, operation)``.
    """
    return {
        (access.model, access.group, operation)
        for access in extract_accesses(module)
        if access.group
        for operation in access.operations
    }


def with_prefix(module: str, xid: str) -> str:
    """ Return a fully qualified external id. """
    return xid and (xid if '.' in xid else f"{module}.{xid}")


def get_xml_model_xid(node) -> str | None:
    """ Retrieve the value of field 'model_id' from the given XML record. """
    model_node = node.find("./field[@name='model_id']")
    if model_node is None:
        return
    if (model := model_node.get('ref')):
        return model
    domain = model_node.get('search')
    for item in literal_eval(domain):
        if item[0] == 'model' and item[1] == '=':
            return f"model_{item[2].replace('.', '_')}"


def get_xml_group_xid(node) -> str | None:
    """ Retrieve the value of field 'group_id' from the given XML record. """
    group_node = node.find("./field[@name='group_id']")
    if group_node is None:
        return
    return group_node.get('ref')


def get_model(module: str, xid: str) -> str:
    """ Retrieve the model name from a model's external id or model name. """
    model_xid = with_prefix(module, xid)
    return get_model_xids().get(model_xid, xid)


def make_domain(domain: str | None = None) -> str:
    """ Normalize the given domain. """
    return "" if domain is None or TRUE_RE.match(domain) else domain


def make_access_xid(model: str, group: str, mode: str) -> str:
    """ Make an external id for the given model, group and mode. """
    model_part = model.replace('.', '_')
    if group:
        group_match = GROUP_PART_RE.match(group)
        group_part = group_match[1] or group_match[2]
    else:
        group_part = "global"
    if mode:
        return f"access_{model_part}_{group_part}_{mode}"
    return f"access_{model_part}_{group_part}"


@functools.cache
def get_model_xids() -> dict[str, str]:
    """ Return a mapping from model external ids to model names. """
    _logger.info("Building mapping for model xids")
    for module in get_modules():
        module_path = Path(get_module_path(module))
        if any((module_path / subdir).is_dir() for subdir in ('models', 'wizard', 'report')):
            __import__(f'odoo.addons.{module}')

    return {
        model_xmlid(module, cls._name): cls._name
        for module, classes in MetaModel.module_to_models.items()
        for cls in classes
    }


@functools.cache
def get_group_definitions() -> dict[str, list[str]]:
    """ Return a mapping from groups to their implied groups. """
    group_implied = defaultdict(list)
    for module in get_modules():
        manifest = get_manifest(module)
        module_path = Path(get_module_path(module))
        for file_name in manifest['data']:
            if file_name.startswith('security') and file_name.endswith('.xml'):
                file_path = module_path / file_name
                for xid, implied_xids in extract_groups_from_xml(module, file_path):
                    group_implied[xid].extend(implied_xids)
    return group_implied


def extract_groups_from_xml(module: str, file_path: Path) -> Iterator[tuple[str, list[str]]]:
    """ Retrieve group definitions from a given XML file. """
    tree = etree.parse(str(file_path))

    for node in tree.xpath("//record[@model='res.groups']"):
        xid = with_prefix(module, node.get('id'))
        implied_xids = [
            with_prefix(module, match[1])
            for implied_node in node.findall("./field[@name='implied_ids']")
            for match in REF_RE.finditer(implied_node.get('eval'))
        ]
        yield (xid, implied_xids)

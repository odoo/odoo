from __future__ import annotations

import csv
import functools
import io
import itertools
import logging
import re
import typing
from ast import literal_eval
from collections import defaultdict

from lxml import etree

from odoo.tools import SetDefinitions, groupby

if typing.TYPE_CHECKING:
    from collections.abc import Iterator


_logger = logging.getLogger(__name__)
_silent = logging.getLogger('silent')
_silent.setLevel(logging.CRITICAL)

REF_RE = re.compile(r"""ref\((?P<quote>["'])(?P<ref>[\w\.]+)(?P=quote)\)""")
TRUE_DOMAIN_RE = re.compile(r"""\[\]|\[\(1,\s*(?P<quote>["'])=(?P=quote),\s*1\)\]""")
FALSE_DOMAIN_RE = re.compile(r"""\[\(0,\s*(?P<quote>["'])=(?P=quote),\s*1\)\]""")
EXCLUSIVE_GROUPS = {'base.group_user', 'base.group_portal', 'base.group_public'}

XML_TAGS = ('delete', 'function', 'menuitem', 'record', 'template')

MODES = {
    'c': 'perm_create',
    'r': 'perm_read',
    'u': 'perm_write',
    'd': 'perm_unlink',
}


class Access:
    """ A common data structure to represent access records. """
    def __init__(
        self,
        id: str | int,
        name: str,
        model: str | int,
        group: str | int | None,
        operations: set[str],
        domain: str = "",
        type: str = 'ir.access',
        should_migrate: bool = True,
        from_perm: Access | None = None,  # result of migration
        from_rule: Access | None = None,  # result of migration
    ):
        self.id = id
        self.name = name
        self.model = model
        self.group = group
        self.operations = operations
        self.domain = domain
        self.type = type
        self.should_migrate = should_migrate
        self.from_perm = from_perm
        self.from_rule = from_rule

    def replace(self, **kwargs):
        return self.__class__(**(self.__dict__ | kwargs))

    def active_when(self, access):
        """ Returns whether `self` applies when `access` is present. """
        return True


A = typing.TypeVar('A', bound=Access)


def convert[A](permrules: list[A], group_defs: SetDefinitions) -> list[A]:
    """ Return ir.access records that are equivalent to the given permissions and rules. """

    def get_implied(group):
        """ Return all groups implied by the given ``group``, including ``group``. """
        yield group
        yield from group_defs.get_superset_ids([group])

    def get_implying(group):
        """ Return all groups implying the given ``group``, including ``group``. """
        yield group
        yield from group_defs.get_subset_ids([group])

    def get_disjoint(group):
        """ Return all groups disjoint from the given ``group``. """
        return group_defs.get_disjoint_ids([group])

    perms = [access for access in permrules if access.type == 'ir.model.access']
    rules = [access for access in permrules if access.type == 'ir.rule']

    perms_by_model = dict(groupby(perms, lambda perm: perm.model))
    rules_by_model = dict(groupby(rules, lambda rule: rule.model))

    #
    # detect misconfigurations
    #
    for model, model_perms in perms_by_model.items():
        model_rules = rules_by_model.get(model, ())
        if not (model_perms and model_rules):
            continue
        for operation in MODES:
            # determines acls that do not imply having rules, and non-trivial rules
            for perm in model_perms:
                if operation not in perm.operations or any(
                    operation in rule.operations
                    and rule.group in get_implied(perm.group)
                    and rule.active_when(perm)
                    for rule in model_rules
                ):
                    continue
                disjoint_groups = set(get_disjoint(perm.group))
                rules_with_domain = [
                    rule
                    for rule in model_rules
                    if rule.should_migrate and operation in rule.operations and rule.domain
                    and rule.group and rule.group not in disjoint_groups
                ]
                if not rules_with_domain:
                    continue
                # This perm give some permission to all records in the model,
                # but when combined with another group with rules, those
                # permissions are granted to less records.
                perm_groups = {perm.group for perm in model_perms if operation in perm.operations}
                perm_groups = {g for pg in perm_groups for g in get_implying(pg)}
                _logger.warning(
                    "WARNING with model=%s, operation=%s\n"
                    "    acl group without rules, giving access to ALL records:\n"
                    "     - %s: acl %s\n"
                    "    may interact with rules in groups, giving access to LESS records:\n"
                    "%s\n",
                    model, operation,
                    perm.group, perm.id,
                    "\n".join(
                        f"     - {rule.group}: rule {rule.id}{" (with acl)" if rule.group in perm_groups else ""}"
                        for rule in sorted(rules_with_domain, key=lambda rule: rule.group)
                    ),
                )

    #
    # Let's infer ir.access records from ir.model.access and ir.rule. The
    # result should reproduce as closely as possible the effects of the
    # existing mechanism based on access and rules. The basic principle
    # is: if group A implies group B, every access in group B is valid in
    # group A.
    #
    # Consider groups A, B, C such that A implies B, which itself implies C.
    # In terms of set of users, this means A ≤ B ≤ C. All the inference
    # cases can be rewritten as the following example, where we consider
    # access and rules for a given model, and there is no ir.rule for
    # operation "r".
    #
    #       group A           ≤     group B           ≤     group C
    #
    #   ir.rule("cu", DomA)     ir.model.access("ru")   ir.rule("cu", DomC)
    #
    #   ir.access("u", DomA)    ir.access("r", [])
    #                           ir.access("u", DomC)
    #

    # generate equivalent access records
    accesses = []
    migrated = set()

    for perm in perms:
        perm_groups = set(get_implied(perm.group))

        # operations permitted without rules
        unrestricted_operations = {
            op for op in perm.operations if not any(
                op in rule.operations
                and rule.group in perm_groups
                and rule.active_when(perm)
                for rule in rules_by_model.get(perm.model, ())
            )
        }
        if perm.should_migrate and unrestricted_operations:
            accesses.append(perm.replace(operations=unrestricted_operations, from_perm=perm))

        # operations permitted with rules
        for rule in rules_by_model.get(perm.model, ()):
            if not (perm.should_migrate or rule.should_migrate):
                continue
            if not rule.group:
                continue
            # determine operations
            if not (operations := rule.operations & perm.operations):
                continue
            # determine which group rule should belong to
            if rule.group in get_implied(perm.group):
                group = perm.group
            elif perm.group in get_implied(rule.group):
                group = rule.group
            else:
                continue
            # determine which module the access belongs to
            if not (perm.active_when(rule) or rule.active_when(perm)):
                continue
            migrated.add(rule.id)
            if operations <= unrestricted_operations:
                continue
            accesses.append(rule.replace(
                group=group, operations=operations, from_rule=rule, from_perm=perm,
            ))

    # add global rules, and check for orphan rules
    for rule in rules:
        if not rule.should_migrate:
            continue
        if not rule.group:
            accesses.append(rule.replace(from_rule=rule))
            continue
        if rule.id in migrated or FALSE_DOMAIN_RE.match(rule.domain):
            continue
        # orphan ir.rules with a non-falsy domain look like a bug; mention
        # alternative groups that provide access and could be implied
        groups_with_perm = {
            perm.group
            for perm in perms_by_model.get(rule.model, ())
            if perm.group is not None and (perm.operations & rule.operations)
        } - {
            *get_disjoint(rule.group),
        }
        _logger.warning(
            "WARNING ir.rule %s without effective operations for group %s\n"
            "    compatible ir.model.access found in groups: %s",
            rule.id, rule.group, ", ".join(map(str, sorted(groups_with_perm or ["none!"]))),
        )

    return accesses


class FAccess(Access):
    """ Specific subclass for file-based access. """
    def __init__(
        self,
        id: str | int,
        name: str,
        model: str | int,
        group: str | int | None,
        operations: set[str],
        domain: str = "",
        type: str = 'ir.access',
        should_migrate: bool = True,
        from_perm: Access | None = None,  # result of migration
        from_rule: Access | None = None,  # result of migration
        modified_by: str | None = None,   # the module that modifies the access
        module_deps: set[str] | None = None,  # self.module's dependencies
    ):
        super().__init__(
            id, name, model, group, operations, domain, type, should_migrate, from_perm, from_rule,
        )
        self.modified_by = modified_by
        self.module_deps = module_deps

    @property
    def module(self):
        return self.id.split('.', 1)[0]

    @module.setter
    def module(self, mod):
        _prefix, suffix = self.id.split('.', 1)
        self.id = f"{mod}.{suffix}"

    def active_when(self, access):
        """ Returns whether `self` applies when `access` is present. """
        modules = access.module_deps
        if self.modified_by:
            return self.module in modules and self.modified_by not in modules
        return self.module in modules


WELCOME_MESSAGE = """
This script is generating ir.access.csv files from existing data files.

The logging messages should be interpreted as:
 - INFO: normal operation
 - WARNING: partially handled case, should be checked and potentially manually fixed up
 - ERROR: not handled case

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

        _logger.info(WELCOME_MESSAGE)

        modules = self.file_manager.get_modules()

        # determine which modules have a security directory before removing files
        has_security = {
            module
            for module in modules
            if any(fname.startswith('security/') for fname in self.get_manifest(module)['data'])
        }

        # extract ir.model.access and ir.rule (rules)
        permrules = []
        modifs = {}
        for module in sorted(modules):
            for access in self.extract(module):
                if access.modified_by:
                    assert access.id not in modifs, f"{access.id} modified twice"
                    modifs[access.id] = access.modified_by
                elif access.type == 'ir.model.access':
                    if access.group and access.operations:
                        permrules.append(access)
                elif access.type == 'ir.rule':
                    if access.operations:
                        permrules.append(access)

        # process modifications
        for access in permrules:
            access.modified_by = modifs.get(access.id)
            access.module_deps = self.get_all_module_dependencies(access.module)

        # determine groups and their implications
        group_defs = self.get_group_definitions()

        accesses = convert(permrules, group_defs)

        # group accesses by module, model (in the same order as permissions)
        ir_accesses = defaultdict(lambda: defaultdict(list))
        for access in permrules:
            if access.type == 'ir.model.access':
                ir_accesses[access.module][access.model]

        def subsumes(acc1, acc2):
            """ Return whether `acc1` subsumes `acc2`, i.e., `acc2` is redundant. """
            assert acc1.model == acc2.model
            return (
                # acc1 is present when acc2 is
                acc1.active_when(acc2)
                # acc1 applies to the users where acc2 applies
                and (
                    acc1.group == acc2.group
                    or acc1.group in group_defs.get_superset_ids([acc2.group])
                )
                # acc1 applies to all the operations of acc2
                and acc1.operations >= acc2.operations
                # acc1's domain is implied by acc2's domain
                and (not acc1.domain or acc1.domain == acc2.domain)
            )

        # group and deduplicate accesses subsumed by other accesses
        for access in accesses:
            if (rule := access.from_rule) and (perm := access.from_perm) and not perm.active_when(rule):
                # rule only applies when perm is present; move access to perm's module
                access.module = perm.module

            access.module_deps = self.get_all_module_dependencies(access.module)

            accs = ir_accesses[access.module][access.model]
            if access.group:
                if any(subsumes(acc, access) for acc in accs):
                    continue
                if any(subsumes(access, acc) for acc in accs):
                    accs[:] = (acc for acc in accs if not subsumes(access, acc))
            accs.append(access)

        # create ir.access.csv files
        xids = set()

        def uniquify(xid):
            if xid not in xids:
                return xids.add(xid) or xid
            for index in range(1, 100):
                xid2 = f"{xid}_{index}"
                if xid2 not in xids:
                    return xids.add(xid2) or xid2
            raise ValueError(f"Too many occurrences of {xid}")

        for module, bymodule in ir_accesses.items():
            with io.StringIO(newline='') as output:
                writer = csv.writer(output, lineterminator='\n')
                writer.writerow(["id", "name", "model_id", "group_id/id", "operation", "domain"])
                for access in itertools.chain.from_iterable(bymodule.values()):
                    writer.writerow([
                        uniquify(access.id).removeprefix(f"{module}."),
                        access.name,
                        access.model,
                        access.group,
                        "".join(op for op in MODES if op in access.operations),
                        access.domain,
                    ])
                content = output.getvalue()

            file_name = 'security/ir.access.csv' if module in has_security else 'ir.access.csv'
            self.file_manager.get_file(module, file_name).content = content
            self.add_to_manifest(module, file_name)

    @functools.cache
    def get_manifest(self, module: str) -> dict:
        """ Return the manifest dict of the given module. """
        file = self.file_manager.get_file(module, "__manifest__.py")
        manifest = literal_eval(file.content)
        manifest.setdefault('depends', [])
        manifest.setdefault('data', [])
        return manifest

    def add_to_manifest(self, module: str, file_name: str):
        """ Add the given 'data' file to its module's manifest. """

        # add it to the manifest's dict
        manifest = self.get_manifest(module)
        assert file_name not in manifest['data'], f"ERROR {module}: file {file_name!r} found in manifest['data']"
        manifest['data'].append(file_name)

        # add it to the manifest's file
        file = self.file_manager.get_file(module, "__manifest__.py")
        content = file.content

        pattern = r"""
            ^ (?P<indent>\s*) (?P<quote>['"]) data (?P=quote) \s* : \s*
            \[ (?P<items>[^\]]*[^\]\s,])? (?P<comma>,?) (?P<newline>\n?) (?P<spaces>\s*) \]
        """
        match = re.search(pattern, content, re.MULTILINE | re.VERBOSE)
        if not match:
            _logger.error("ERROR %s: Cannot add %s to manifest, please add manually", module, file_name)
            return

        if match['newline']:  # list on several lines, add a line
            pos = match.start('newline')
            comma = "," if match['items'] and not match['comma'] else ""
            indent = match['indent']
            content = f"{content[:pos]}{comma}\n{indent}    {file_name!r},{content[pos:]}"
        elif match['items']:  # non-empty list, add an item
            pos = match.start('spaces')
            comma = "," if not match['comma'] else ""
            content = f"{content[:pos]}{comma} {file_name!r}{content[pos:]}"
        else:  # empty list
            pos = match.start('spaces')
            content = f"{content[:pos]}{file_name!r}{content[pos:]}"

        file.content = content

    def remove_from_manifest(self, module: str, file_name: str):
        """ Remove the given file from its module's manifest. """

        # remove it from the manifest's dict
        manifest = self.get_manifest(module)
        assert file_name in manifest['data'], f"File {file_name!r} not found in manifest['data']"
        manifest['data'].remove(file_name)

        # remove it from the manifest's file
        file_pattern = re.escape(str(file_name))
        pattern = rf"""\s*(?P<quote>['"]){file_pattern}(?P=quote),?"""

        file = self.file_manager.get_file(module, "__manifest__.py")
        file.content = re.sub(pattern, "", file.content, flags=re.MULTILINE)

    @functools.cache
    def get_all_module_dependencies(self, module: str) -> set[str]:
        """ Return ``module`` with all its transitive dependencies. """
        todo = [module]
        result = {'base'}
        for mod in todo:
            if mod not in result:
                result.add(mod)
                todo.extend(self.get_manifest(mod)['depends'])
        return result

    def extract(self, module: str) -> Iterator[FAccess]:
        """ Extract ir.model.access or ir.rule records from the given module. """
        manifest = self.get_manifest(module)
        # beware: manifest['data'] may be modified in-place
        for file_name in list(manifest['data']):
            if 'security' in file_name or 'access' in file_name:
                if file_name.endswith('ir.model.access.csv'):
                    yield from self.extract_from_csv(module, file_name)
                elif file_name.endswith('.xml'):
                    yield from self.extract_from_xml(module, file_name)

    def extract_from_csv(self, module: str, file_name: str) -> Iterator[FAccess]:
        assert file_name.endswith('ir.model.access.csv'), f"Unexpected CSV file {file_name}"

        file = self.file_manager.get_file(module, file_name)
        reader = csv.reader(io.StringIO(file.content, newline=''), lineterminator='\n')

        fields = next(reader)
        model_field = next(field for field in fields if field.startswith('model_id'))
        group_field = next(field for field in fields if field.startswith('group_id'))

        lines_to_keep = []

        for line in reader:
            if not line:
                continue
            line_data = dict(zip(fields, line, strict=True))

            xid = with_prefix(module, line_data['id'])
            if not xid.startswith(f"{module}."):
                _logger.warning("WARNING %s: modified ir.model.access, skipping %s in %s", module, xid, file_name)
                lines_to_keep.append(line)
                continue
            name = line_data['name']
            model = self.get_model_name(module, line_data[model_field])
            if not model:
                _logger.error("ERROR %s: ir.model.access without model, skipping %s in %s", module, xid, file_name)
                lines_to_keep.append(line)
                continue
            operations = {op for op, fname in MODES.items() if int(line_data[fname] or "0")}
            group = line_data[group_field]
            if not group:
                _logger.info("INFO %s: ir.model.access without group, base.group_everyone instead: %s in %s", module, xid, file_name)
                group = 'base.group_everyone'
            group = with_prefix(module, group)

            yield FAccess(xid, name or model, model, group, operations, type='ir.model.access')

        if lines_to_keep:
            with io.StringIO(newline='') as output:
                writer = csv.writer(output, lineterminator='\n')
                writer.writerow(fields)
                for line in lines_to_keep:
                    writer.writerow(line)
                content = output.getvalue()
            file.content = content
        else:
            file.content = None
            self.remove_from_manifest(module, file_name)

    def extract_from_xml(self, module: str, file_name: str) -> Iterator[FAccess]:
        file = self.file_manager.get_file(module, file_name)
        tree = etree.fromstring(file.content.encode())
        nodes = []

        for node in tree.xpath("//record[@model='ir.model.access']"):
            xid = with_prefix(module, node.get('id'))
            if not xid.startswith(f"{module}."):
                _logger.warning("WARNING %s: modified ir.model.access, skipping %s in %s", module, xid, file_name)
                yield FAccess(xid, "", "", "", set(), type='ir.model.access', modified_by=module)
                continue
            if (
                (field := node.find("./field[@name='active']")) is not None
                and (field.text in ("0", "false", "off") or field.get('eval') in ("0", "False"))
            ):
                _logger.error("WARNING %s: ir.model.access with field 'active', skipping %s in %s", module, xid, file_name)
                continue
            name = name_node.text if (name_node := node.find("./field[@name='name']")) is not None else None
            model = self.get_model_name(module, get_xml_model_xid(node))
            if not model:
                _logger.error("ERROR %s: ir.model.access without model, skipping %s in %s", module, xid, file_name)
                continue
            operations = {
                op
                for op, fname in MODES.items()
                if (opnode := node.find(f"./field[@name='{fname}']")) is not None
                and literal_eval(opnode.get('eval') or opnode.text)
            }
            group = get_xml_group_xid(node)
            if not group:
                _logger.info("INFO %s: ir.model.access without group, base.group_everyone instead: %s in %s", module, xid, file_name)
                group = 'base.group_everyone'
            group = with_prefix(module, group)

            yield FAccess(xid, name or model, model, group, operations, type='ir.model.access')
            nodes.append(node)

        for node in tree.xpath("//record[@model='ir.rule']"):
            xid = with_prefix(module, node.get('id'))
            if not xid.startswith(f"{module}."):
                _logger.warning("WARNING %s: modified ir.rule, skipping %s in %s", module, xid, file_name)
                yield FAccess(xid, "", "", "", set(), type='ir.rule', modified_by=module)
                continue
            if (
                (field := node.find("./field[@name='active']")) is not None
                and (field.text in ("0", "false", "off") or field.get('eval') in ("0", "False"))
            ):
                _logger.error("WARNING %s: ir.rule with field 'active', skipping %s in %s", module, xid, file_name)
                continue
            name = node.findtext("./field[@name='name']")
            model = self.get_model_name(module, get_xml_model_xid(node))
            if not model:
                _logger.error("ERROR %s: ir.rule without model, skipping %s in %s", module, xid, file_name)
                continue
            groups = [
                with_prefix(module, match['ref'])
                for group_node in node.findall("./field[@name='groups']")
                for match in REF_RE.finditer(group_node.get('eval'))
            ]
            operations = {
                op
                for op, fname in MODES.items()
                if (opnode := node.find(f"./field[@name='{fname}']")) is None
                or literal_eval(opnode.get('eval'))
            }
            domain = make_domain(node.findtext("./field[@name='domain_force']"))
            if groups:
                for group in groups:
                    yield FAccess(xid, name or model, model, group, operations, domain, type='ir.rule')
            else:
                yield FAccess(xid, name or model, model, None, operations, domain, type='ir.rule')

            nodes.append(node)

        if nodes:
            # remove nodes from tree
            for node in nodes:
                while (parent := node.getparent()) is not None:
                    # remove preceding comments
                    while (pred := node.getprevious()) is not None and pred.tag is etree.Comment:
                        parent.remove(pred)
                    parent.remove(node)
                    node = parent
                    if len(node):
                        break

            if any(tree.find(f".//{tag}") is not None for tag in XML_TAGS):
                file.content = etree.tostring(tree).decode() + "\n"
            else:
                file.content = None
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
        result = {}
        for file in self.file_manager:
            if file.path.suffix == '.py':
                module = file.addon.name
                for model_name in extract_model_names(file):
                    result[model_xmlid(module, model_name)] = model_name
        return result

    @functools.cache
    def get_group_definitions(self) -> SetDefinitions:
        definitions: dict[str, dict] = {}

        for module in self.file_manager.get_modules():
            for file_name in self.get_manifest(module)['data']:
                if not file_name.endswith('.xml'):
                    continue
                for info in self._get_group_from_xml(module, file_name):
                    xid = info['ref']
                    group = definitions.get(xid)
                    if group is None:
                        definitions[xid] = group = {'ref': xid, 'supersets': [], 'disjoints': []}
                    group['supersets'].extend(info.get('supersets', ()))
                    group['disjoints'].extend(info.get('disjoints', ()))

        # those ones may be missing from data files
        definitions['base.group_user']['disjoints'].extend(['base.group_portal'])
        definitions['base.group_portal']['disjoints'].extend(['base.group_public'])
        definitions['base.group_public']['disjoints'].extend(['base.group_user'])

        return SetDefinitions(definitions)  # type: ignore[arg-type]

    def _get_group_from_xml(self, module: str, file_name: str) -> Iterator[dict]:
        """ Retrieve the group definitions from a given XML file. """
        try:
            file = self.file_manager.get_file(module, file_name)
            tree = etree.fromstring(file.content.encode())
        except UnicodeDecodeError:
            _logger.info("Unexpected encoding, skip %s/%s", module, file_name)
            return

        for node in tree.xpath("//record[@model='res.groups']"):
            xid = with_prefix(module, node.get('id'))
            yield {
                'ref': xid,
                'supersets': [
                    with_prefix(module, match['ref'])
                    for field_node in node.findall("./field[@name='implied_ids']")
                    for match in REF_RE.finditer(field_node.get('eval'))
                ],
                'disjoints': [
                    with_prefix(module, match['ref'])
                    for field_node in node.findall("./field[@name='disjoint_ids']")
                    for match in REF_RE.finditer(field_node.get('eval'))
                ],
            }
            for field_node in node.findall("./field[@name='implied_by_ids']"):
                for match in REF_RE.finditer(field_node.get('eval')):
                    yield {
                        'ref': with_prefix(module, match['ref']),
                        'supersets': [xid],
                    }


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
    return "" if domain is None or TRUE_DOMAIN_RE.match(domain) else domain


# matches all the lines like one of those:
#   class <identifier> (... Model ...
#       _name = <str>
#       _inherit = <str>
RE_MODEL_DEF = re.compile(
    r"""
        (
            ^class \s+ (?P<class>\w+) \s* \( [^)]* \b \w*Model \b
        )|(
            ^\s{4,8} (?P<attr>_name|_inherit) \s* = \s*
            (?P<attrs> (\w+ \s* = \s*)*)
            (?P<quote>['"]) (?P<model>[\w.]+) (?P=quote)
        )
    """,
    re.VERBOSE)

# matches the places where to insert a '.' in class_name_to_model_name()
RE_DOT_PLACE = re.compile(r"(?<=[^_])([A-Z])")


def extract_model_names(file) -> list[str]:
    """ Return a list of model names defined in the given file. """
    result: list[str] = []
    class_name = None
    name = None
    inherit = None

    def flush():
        if class_name:
            result.append(name or inherit or RE_DOT_PLACE.sub(r'.\1', class_name).lower())

    for line in file.content.splitlines():
        match = RE_MODEL_DEF.match(line)
        if not match:
            continue

        if match['class']:
            # we found a new class definition
            flush()
            class_name, name, inherit = match['class'], None, None

        elif class_name and match['model']:
            # we found a model name (_name)
            if match['attr'] == '_name':
                name = match['model']
            else:
                inherit = match['model']

    flush()
    return result


def model_xmlid(module, model_name):
    """ Return the XML id of the given model. """
    return '%s.model_%s' % (module, model_name.replace('.', '_'))

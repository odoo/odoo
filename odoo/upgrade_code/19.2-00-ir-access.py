from __future__ import annotations

import csv
import functools
import io
import logging
import re
import typing
from ast import literal_eval
from collections import defaultdict
from dataclasses import dataclass, replace

from lxml import etree

from odoo.tools import SetDefinitions

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
    'r': 'perm_read',
    'w': 'perm_write',
    'c': 'perm_create',
    'd': 'perm_unlink',
}


@dataclass
class Access:
    """ A common data structure to represent ir.model.access, ir.rule and ir.access records. """
    id: str
    name: str
    model: str
    group: str | None
    operations: set[str]
    domain: str = ""

    @property
    def module(self):
        return self.id.split('.', 1)[0]


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

        _logger.info(WELCOME_MESSAGE)
        self.check()

        modules = file_manager.get_modules()
        file_manager.print_progress(0, len(modules))
        for count, module in enumerate(modules, start=1):
            self.generate(module)
            file_manager.print_progress(count, len(modules))

    def generate(self, module: str):
        """ Generate a file ``ir.access.csv`` for the given module. """
        manifest = self.get_manifest(module)
        if not any('security' in fname or 'access' in fname for fname in manifest['data']):
            return
        if 'security/ir.access.csv' in manifest['data'] or 'ir.access.csv' in manifest['data']:
            return

        # determine filename before files are removed from manifest
        has_security = any(fname.startswith('security/') for fname in manifest['data'])
        file_name = 'security/ir.access.csv' if has_security else 'ir.access.csv'

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
        #   ir.rule("wc", DomA)     ir.model.access("rw")   ir.rule("wc", DomC)
        #
        #   ir.access("w", DomA)    ir.access("r", [])
        #                           ir.access("w", DomC)
        #
        permissions = self.get_permissions(module)
        group_defs = self.get_group_definitions()

        # first consider ir.access entries derived from ir.rules
        # {model: {group: [access]}}
        from_rules: dict[str, dict[str | None, list[Access]]] = defaultdict(lambda: defaultdict(list))

        for rule in self.extract_rules(module, remove=True):
            if not rule.operations:
                continue

            if rule.group is None:
                from_rules[rule.model][rule.group].append(rule)
                continue

            # add rule in all groups that have a corresponding ir.model.access
            added = False

            for subgroup in group_defs.implying(rule.group):
                # determine what operations are permitted by ir.model.access; on
                # rule.group, we combine all access from implied groups, while
                # on implying groups we consider group-specific permissions:
                #
                #  subgroup   ir.model.access("rwc")   =>  ir.access("rwc", domain)
                #     ↓
                # rule.group  ir.rule("rwcd", domain)  =>  ir.access("r", domain)
                #     ↓
                # supergroup  ir.model.access("r")
                #             ir.rule(...)
                #
                if subgroup == rule.group:
                    operations = rule.operations & set().union(*(
                        permissions[rule.model, supergroup]
                        for supergroup in group_defs.implied(subgroup)
                    ))
                else:
                    operations = rule.operations & permissions[rule.model, subgroup]
                if not operations:
                    continue

                added = True
                from_rules[rule.model][subgroup].append(
                    replace(rule, group=subgroup, operations=operations))

            if not added and not FALSE_DOMAIN_RE.match(rule.domain or ""):
                # ir.rules with a non-falsy domain that never apply look like a
                # configuration bug; mention alternative groups that provide
                # access and could be implied
                groups_with_permission = sorted(
                    group
                    for (model, group), operations in permissions.items()
                    if model == rule.model and group is not None
                    if not operations.isdisjoint(rule.operations)
                ) or ["none!"]
                _logger.warning(
                    "WARNING %s: ir.rule(%s) without effective operations for group(%s)\n"
                    "    compatible ir.model.access found in groups: %s",
                    module, rule.id, rule.group, ", ".join(groups_with_permission),
                )

        # second, consider ir.access entries ("perm") derived from ir.model.access
        # {model: {group: [access]}}
        ir_access: dict[str, dict[str | None, list[Access]]] = defaultdict(lambda: defaultdict(list))
        for perm in self.extract_accesses(module, remove=True):
            if not perm.operations:
                continue

            # this prepares entries in the same order as in ir.model.access
            entries = ir_access[perm.model][perm.group]
            # only consider operations from perm that do not appear in rules
            operations = perm.operations - set().union(*(
                rule.operations for rule in from_rules[perm.model][perm.group]
            ))
            if operations:
                entries.append(replace(perm, operations=operations))

        # third, merge both (ir.access from ir.model.access then from ir.rule)
        for model, model_rule_entries in from_rules.items():
            for group, rule_entries in model_rule_entries.items():
                ir_access[model][group].extend(rule_entries)

        if not ir_access:
            return

        #
        # Create ir.access.csv
        #
        xids = set()

        def uniquify(xid):
            if xid not in xids:
                return xids.add(xid) or xid
            for index in range(1, 100):
                xid2 = f"{xid}_{index}"
                if xid2 not in xids:
                    return xids.add(xid2) or xid2
            raise Exception(f"Too many occurrences of {xid}")

        with io.StringIO(newline='') as output:
            writer = csv.writer(output, lineterminator='\n')
            writer.writerow(["id", "name", "model_id", "group_id/id", "operation", "domain"])
            for access in (y for xs in ir_access.values() for ys in xs.values() for y in ys):
                writer.writerow([
                    uniquify(access.id).removeprefix(f"{module}."),
                    access.name,
                    access.model,
                    access.group,
                    "".join(op for op in MODES if op in access.operations),
                    access.domain,
                ])
            content = output.getvalue()

        self.file_manager.get_file(module, file_name).content = content
        self.add_to_manifest(module, file_name)

    def check(self) -> None:
        """ Warn about non-monotonic access with possible group combinations. """
        group_defs = self.get_group_definitions()

        ignored_groups = {None, *group_defs.implied('base.group_public', 'base.group_portal')}

        # {(model, operation): {group: perms}}
        model_group_perms = defaultdict(lambda: defaultdict(list))
        # {(model, operation): {group: rules}}
        model_group_rules = defaultdict(lambda: defaultdict(list))
        for module in self.file_manager.get_modules():
            for perm in self.extract_accesses(module):
                if perm.group not in ignored_groups:
                    for operation in perm.operations:
                        model_group_perms[perm.model, operation][perm.group].append(perm)
            for rule in self.extract_rules(module):
                if rule.group not in ignored_groups:
                    for operation in rule.operations:
                        model_group_rules[rule.model, operation][rule.group].append(rule)

        # check all model and operations on which we have both acls and rules
        for model_operation in sorted(model_group_perms.keys() & model_group_rules.keys()):
            model, operation = model_operation
            perm_groups = model_group_perms[model_operation]
            rule_groups = model_group_rules[model_operation]

            # determines acls that do not imply having rules, and non-trivial rules
            perms_without_rule = [
                perm
                for perm_group, perms in perm_groups.items()
                if not any(
                    group in rule_groups
                    for group in group_defs.implied(perm_group)
                )
                for perm in perms
            ]
            rules_with_domain = [
                rule
                for rules in rule_groups.values()
                for rule in rules
                if rule.domain
            ]
            if perms_without_rule and rules_with_domain:
                # Those acls give some permission to all records in the model.
                # But when combined with another group with rules, those
                # permissions are granted to less records.
                lines = [f"/!\\ {model=}, {operation=}"]
                lines.append("    acl groups without rules, giving access to ALL records:")
                for perm in sorted(perms_without_rule, key=lambda perm: perm.group):
                    lines.append(f"     - {perm.group}: acl {perm.id}")
                lines.append("    may interact with rules in groups, giving access to LESS records:")
                for rule in sorted(rules_with_domain, key=lambda rule: rule.group):
                    has_acl = any(
                        group in perm_groups
                        for group in group_defs.implied(rule.group)
                    )
                    extra = " (with acl)" if has_acl else ""
                    lines.append(f"     - {rule.group}: rule {rule.id}{extra}")
                lines.append("")
                _logger.warning("\n".join(lines))

    def set_file_content(self, module: str, file_name: str, content: str | None):
        """ Update the content of the given file; set it to ``None`` to delete it. """
        self.file_manager.get_file(module, file_name).content = content

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

    def get_permissions(self, module: str) -> defaultdict[tuple[str, str], set[str]]:
        """ Return all the permissions that are available when the given module
        is installed.  The result is a dict ``{(model, group): operations}}``.
        """
        # determine all (direct and indirect) dependencies
        todo = [module]
        deps = {'base'}
        for mod in todo:
            if mod not in deps:
                deps.add(mod)
                todo.extend(self.get_manifest(mod)['depends'])

        result = defaultdict(set)
        for mod in sorted(deps):
            for model, group, operations in self._get_permissions(mod):
                result[model, group].update(operations)
        return result

    @functools.cache
    def _get_permissions(self, module: str) -> list[tuple[str, str, set[str]]]:
        """ Return the permissions that are defined by the given module.
        The result is a list of triples ``(model, group, operation)``.
        """
        return [
            (access.model, access.group, access.operations)
            for access in self.extract_accesses(module)
            if access.group
        ]

    def extract_accesses(self, module: str, remove=False) -> Iterator[Access]:
        """ Extract ir.model.access or ir.access records from the given module. """
        manifest = self.get_manifest(module)
        # beware: manifest['data'] may be modified in-place
        for file_name in list(manifest['data']):
            if 'security' in file_name or 'access' in file_name:
                if file_name.endswith('.csv'):
                    yield from self.extract_accesses_from_csv(module, file_name, remove)
                elif file_name.endswith('.xml'):
                    yield from self.extract_accesses_from_xml(module, file_name, remove)

    def extract_accesses_from_csv(self, module: str, file_name: str, remove: bool) -> Iterator[Access]:
        logger = _logger if remove else _silent

        if file_name.endswith('ir.model.access.csv'):
            access_model = 'ir.model.access'
        elif file_name.endswith('ir.access.csv'):
            access_model = 'ir.access'
        else:
            # ignore that CSV file
            return

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

            name = line_data['name']
            xid = with_prefix(module, line_data['id'])
            if not xid.startswith(f"{module}."):
                logger.error("ERROR %s: modified %s, skipping %s in %s", module, access_model, xid, file_name)
                lines_to_keep.append(line)
                continue
            model = self.get_model_name(module, line_data[model_field])
            if not model:
                logger.error("ERROR %s: %s without model, skipping %s in %s", module, access_model, xid, file_name)
                lines_to_keep.append(line)
                continue
            if access_model == 'ir.model.access':
                operations = {op for op, fname in MODES.items() if int(line_data[fname] or "0")}
            else:
                operations = set(line_data['operation'])
            domain = make_domain(line_data.get('domain'))
            group = line_data[group_field]

            if group:
                yield Access(xid, name, model, with_prefix(module, group), operations, domain)
            elif access_model == 'ir.access':
                yield Access(xid, name, model, group, operations, domain)
            else:
                logger.info("INFO %s: ir.model.access without group, base.group_everyone instead: %s in %s", module, xid, file_name)
                yield Access(xid, name, model, 'base.group_everyone', operations, domain)

        if remove:
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

    def extract_accesses_from_xml(self, module: str, file_name: str, remove: bool) -> Iterator[Access]:
        logger = _logger if remove else _silent
        file = self.file_manager.get_file(module, file_name)
        tree = etree.fromstring(file.content.encode())
        nodes = []

        for node in tree.xpath("//record[@model='ir.model.access']"):
            xid = with_prefix(module, node.get('id'))
            if not xid.startswith(f"{module}."):
                logger.error("ERROR %s: modified ir.model.access, skipping %s in %s", module, xid, file_name)
                continue
            if (
                (field := node.find("./field[@name='active']")) is not None
                and (field.text in ("0", "false", "off") or field.get('eval') in ("0", "False"))
            ):
                logger.error("ERROR %s: ir.model.access with field 'active', skipping %s in %s", module, xid, file_name)
                continue
            name = name_node.text if (name_node := node.find("./field[@name='name']")) is not None else None
            model = self.get_model_name(module, get_xml_model_xid(node))
            if not model:
                logger.error("ERROR %s: ir.model.access without model, skipping %s in %s", module, xid, file_name)
                continue
            operations = {
                op
                for op, fname in MODES.items()
                if (opnode := node.find(f"./field[@name='{fname}']")) is not None
                and literal_eval(opnode.get('eval') or opnode.text)
            }
            domain = make_domain()
            group = get_xml_group_xid(node)

            if group:
                yield Access(xid, name, model, with_prefix(module, group), operations, domain)
            else:
                logger.info("INFO %s: ir.model.access without group, base.group_everyone instead: %s in %s", module, xid, file_name)
                yield Access(xid, name, model, 'base.group_everyone', operations, domain)

            nodes.append(node)

        for node in tree.xpath("//record[@model='ir.access']"):
            xid = with_prefix(module, node.get('id'))
            if not xid.startswith(f"{module}."):
                logger.error("ERROR %s: modified ir.access, skipping %s in %s", module, xid, file_name)
                continue
            if (
                (field := node.find("./field[@name='active']")) is not None
                and (field.text in ("0", "false", "off") or field.get('eval') in ("0", "False"))
            ):
                logger.error("ERROR %s: ir.access with field 'active', skipping %s in %s", module, xid, file_name)
                continue
            name = node.findtext("./field[@name='name']")
            model = self.get_model_name(module, get_xml_model_xid(node))
            if not model:
                logger.error("ERROR %s: ir.access without model, skipping %s in %s", module, xid, file_name)
                continue
            operations = set(node.findtext("./field[@name='operation']") or "")
            domain = make_domain(node.findtext("./field[@name='domain']"))
            group = get_xml_group_xid(node)
            if group:
                group = with_prefix(module, group)

            yield Access(xid, name, model, group, operations, domain)

            nodes.append(node)

        if remove and nodes:
            self.remove_from_etree(tree, nodes)
            if any(tree.find(f".//{tag}") is not None for tag in XML_TAGS):
                file.content = etree.tostring(tree).decode() + "\n"
            else:
                file.content = None
                self.remove_from_manifest(module, file_name)

    def extract_rules(self, module: str, remove=False) -> Iterator[Access]:
        """ Extract ir.rule records from the given module. """
        manifest = self.get_manifest(module)
        # beware: manifest['data'] may be modified in-place
        for file_name in list(manifest['data']):
            if 'security' in file_name and file_name.endswith('.xml'):
                yield from self.extract_rules_from_xml(module, file_name, remove)

    def extract_rules_from_xml(self, module: str, file_name: str, remove: bool) -> Iterator[Access]:
        logger = _logger if remove else _silent
        file = self.file_manager.get_file(module, file_name)
        tree = etree.fromstring(file.content.encode())
        nodes = []

        for node in tree.xpath("//record[@model='ir.rule']"):
            xid = with_prefix(module, node.get('id'))
            if not xid.startswith(f"{module}."):
                logger.error("ERROR %s: modified ir.rule, skipping %s in %s", module, xid, file_name)
                continue
            if (
                (field := node.find("./field[@name='active']")) is not None
                and (field.text in ("0", "false", "off") or field.get('eval') in ("0", "False"))
            ):
                logger.error("ERROR %s: ir.rule with field 'active', skipping %s in %s", module, xid, file_name)
                continue
            name = node.findtext("./field[@name='name']")
            model = self.get_model_name(module, get_xml_model_xid(node))
            if not model:
                logger.error("ERROR %s: ir.rule without model, skipping %s in %s", module, xid, file_name)
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
                    yield Access(xid, name, model, group, operations, domain)
            else:
                yield Access(xid, name, model, None, operations, domain)

            nodes.append(node)

        if remove and nodes:
            self.remove_from_etree(tree, nodes)
            if any(tree.find(f".//{tag}") is not None for tag in XML_TAGS):
                file.content = etree.tostring(tree).decode() + "\n"
            else:
                file.content = None
                self.remove_from_manifest(module, file_name)

    def remove_from_etree(self, tree: etree.Element, nodes: list):
        """ Remove the given nodes from the XML tree, and return it serialized. """
        for node in nodes:
            while (parent := node.getparent()) is not None:
                parent.remove(node)
                node = parent
                if len(node):
                    break

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
    def get_group_definitions(self) -> GroupDefinitions:
        definitions: dict[str, dict] = {}
        for module in self.file_manager.get_modules():
            for file_name in self.get_manifest(module)['data']:
                if not file_name.endswith('.xml'):
                    continue
                for xid, implied_xids in self._get_group_from_xml(module, file_name):
                    group = definitions.get(xid)
                    if group is None:
                        definitions[xid] = {'ref': xid, 'supersets': implied_xids}
                    else:
                        group['supersets'].extend(implied_xids)
        return GroupDefinitions(definitions)  # type: ignore[arg-type]

    def _get_group_from_xml(self, module: str, file_name: str) -> Iterator[tuple[str, list[str]]]:
        """ Retrieve the group definitions from a given XML file. """
        try:
            file = self.file_manager.get_file(module, file_name)
            tree = etree.fromstring(file.content.encode())
        except UnicodeDecodeError:
            _logger.info("Unexpected encoding, skip %s/%s", module, file_name)
            return

        for node in tree.xpath("//record[@model='res.groups']"):
            xid = with_prefix(module, node.get('id'))
            yield (xid, [
                with_prefix(module, match['ref'])
                for field_node in node.findall("./field[@name='implied_ids']")
                for match in REF_RE.finditer(field_node.get('eval'))
            ])
            for field_node in node.findall("./field[@name='implied_by_ids']"):
                for match in REF_RE.finditer(field_node.get('eval')):
                    yield (with_prefix(module, match['ref']), [xid])


class GroupDefinitions(SetDefinitions):
    """ Simple extension for methods ``implied`` and ``implying``. """

    def implied(self, *groups):
        """ Return all groups implied by the given ``groups``, including ``groups``. """
        yield from groups
        yield from self.get_superset_ids(groups)

    def implying(self, *groups):
        """ Return all groups implying the given ``groups``, including ``groups``. """
        yield from groups
        yield from self.get_subset_ids(groups)


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


def make_access_xid(model: str, group: str, operation: str) -> str:
    """ Make an external id for the given model, group and operation. """
    model_part = model.replace('.', '_')
    group_part = group.split('.', 1)[1] if group else "global"
    if operation:
        return f"access_{model_part}_{group_part}_{operation}"
    return f"access_{model_part}_{group_part}"


# matches all the lines like one of those:
#   class <identifier> (... Model ...
#       _name = <str>
#       _inherit = <str>
RE_MODEL_DEF = re.compile(
    r"""
        (
            ^class \s+ (?P<class>\w+) \s* \( .*
            \b (Model|TransientModel|AbstractModel|BaseModel) \b
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

import csv
import functools
import io
import itertools
import logging
import re
from ast import literal_eval
from collections import defaultdict
from typing import Iterable, Iterator

from lxml import etree

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


class Access:
    """ A common data structure to represent ir.model.access, ir.rule and ir.access records. """
    id: str
    name: str
    model: str
    group: str | None
    operations: set[str]
    domain: str | None

    def __init__(self, id, name, model, group, operations, domain):
        self.id = id
        self.name = name
        self.model = model
        self.group = group
        self.operations = operations
        self.domain = domain


class BinaryRelation:
    """ Represents a binary relation. """
    def __init__(self, items: Iterable[tuple[str, str]]):
        self._map = rel = defaultdict(dict)
        for x, y in items:
            rel[x].setdefault(y, None)

    def __getitem__(self, x: str) -> Iterable[str]:
        """ Return the elements related to `x`. """
        return self._map.get(x, ())

    @functools.cache
    def follow(self, x: str) -> Iterable[str]:
        """ Return `x` followed by all the elements reachable by relation `self`. """
        result = {x: None}
        for y in self._map.get(x, ()):
            result.update(self.follow(y))
        return result

    @functools.cache
    def inverse(self) -> "BinaryRelation":
        """ Return the inverse relation of `self`. """
        return BinaryRelation(
            (y, x)
            for x, ys in self._map.items()
            for y in ys
        )


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

        modules_to_upgrade = sorted({
            file.addon.name: None
            for file in file_manager
            if file.path.name == 'ir.model.access.csv' or file.path.suffix == '.xml'
        })
        if not modules_to_upgrade:
            return

        _logger.info(WELCOME_MESSAGE)
        self.log_before()

        file_manager.print_progress(0, len(modules_to_upgrade))
        for count, module in enumerate(modules_to_upgrade, start=1):
            self.generate(module)
            file_manager.print_progress(count, len(modules_to_upgrade))

        self.log_after()

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
        # existing mechanism based on access and rules.  The basic principle
        # is: if group A implied group B, every ir.model.access on B applies to
        # A, and thus every ir.rule on B also applies to A.
        #
        # The base case is what happens when you have some access and rules on
        # the same group.  In the example below, "read" access is granted
        # without rule, which leads to an access with domain "[]".  The other
        # operations are permitted with a rule, except for operation "delete",
        # which has no permission at all.
        #
        #   group_stuff     ir.model.access("rwc")      =>  ir.access("r", [])
        #                   ir.rule("wcd", domain)          ir.access("wc", domain)
        #
        # Now consider groups with implication.  In a typical configuration, the
        # base (implied) group comes with the base access for both groups, and
        # each group has its own rules.  In that case, the access permissions
        # are applied to all groups, and each rule is converted like in the
        # base case above.
        #
        #   group_system    ir.rule("rwcd", [])         =>  ir.access("rwcd", [])
        #       |
        #       | implies
        #       v
        #   group_user      ir.model.access("rwcd")     =>  ir.access("rwcd", domain)
        #                   ir.rule("rwcd", domain)
        #
        # We can also have one rule with several accesses.  Each group permits a
        # different set of operations: the most restricted the group, the more
        # operations are permitted.  In the following example (based on a real
        # case), all the accesses are restricted by a common rule that belongs
        # to a group implied by all of them.  In that case, the rule is applied
        # to all groups, and it is converted in each group like in the base
        # case above.
        #
        #   group_high      ir.model.access("rwcd")     =>  ir.access("rwcd", domain)
        #       |
        #       | implies
        #       v
        #   group_medium    ir.model.access("r")        =>  ir.access("r", domain)
        #       |
        #       | implies
        #       v
        #   group_low       ir.rule("rwcd", domain)
        #
        permissions = self.get_permissions(module)
        implied = self.get_groups_implied()
        implying = implied.inverse()

        # first consider ir.access entries derived from ir.rules
        # {model: {group: [(operations, domain, name)]}}
        ir_access_rules = defaultdict(lambda: defaultdict(list))

        for rule in self.extract_rules(module, remove=True):
            if not rule.operations:
                continue

            if rule.group is None:
                ir_access_rules[rule.model][rule.group].append(
                    (rule.operations, rule.domain, rule.name)
                )
                continue

            # add rule in all groups that have a corresponding ir.model.access
            added = False

            for index, group in enumerate(implying.follow(rule.group)):
                # determine what operations are permitted by ir.model.access; on the
                # base group, we combine all access from implied groups, while on
                # implying groups we consider group-specific permissions
                if index == 0:
                    operations = rule.operations & {
                        op
                        for impl in implied.follow(group)
                        for op in permissions[rule.model, impl]
                    }
                else:
                    operations = rule.operations & permissions[rule.model, group]
                if not operations:
                    continue

                added = True
                entries = ir_access_rules[rule.model][group]

                # ignore the rule if superseded by existing entries (with empty domain)
                if operations <= {op for ops, dom, _ in entries if not dom for op in ops}:
                    continue

                # discard existing entries that are superseded by the rule
                if not rule.domain:
                    entries[:] = [entry for entry in entries if not (entry[0] <= operations)]

                entries.append((operations, rule.domain, rule.name))

            if not added and not FALSE_DOMAIN_RE.match(rule.domain):
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

        # second, consider ir.access entries derived from ir.model.access
        # {model: {group: [(operations, domain, name)]}}
        ir_access = defaultdict(lambda: defaultdict(list))
        for access in self.extract_accesses(module, remove=True):
            if not access.operations:
                continue

            # this prepares entries in the same order as in ir.model.access
            entries = ir_access[access.model][access.group]
            # only consider operations from access that do not appear in rules
            operations = access.operations - {
                op for ops, _, _ in ir_access_rules[access.model][access.group] for op in ops
            }
            if operations:
                entries.append((operations, make_domain(), access.name))

        # third, merge both (ir.access from ir.model.access then from ir.rule)
        for model, model_rule_entries in ir_access_rules.items():
            for group, rule_entries in model_rule_entries.items():
                ir_access[model][group].extend(rule_entries)

        if not ir_access:
            return

        #
        # Create ir.access.csv
        #
        with io.StringIO(newline='') as output:
            writer = csv.writer(output, lineterminator='\n')
            writer.writerow(["id", "model_id", "group_id/id", "operation", "domain", "name"])
            xids = set()
            for model, model_accesses in ir_access.items():
                for group, accesses in model_accesses.items():
                    full_xids = len(accesses) > 1
                    for operations, domain, name in accesses:
                        operation = "".join(op for op in MODES if op in operations)
                        xid = make_access_xid(model, group, operation if full_xids else "")
                        if xid in xids:
                            xid = next(
                                f"{xid}{index}"
                                for index in itertools.count(1)
                                if f"{xid}{index}" not in xids
                            )
                        xids.add(xid)
                        writer.writerow([xid, model, group, operation, domain, name])
            content = output.getvalue()

        self.set_file_content(module, file_name, content)
        self.add_to_manifest(module, file_name)

    def log_before(self):
        """ Log the effective access domains in all possible group combinations. """

        # {(model, operation): groups}
        acls = defaultdict(set)
        # {(model, operation): {group: domains}}
        rules = defaultdict(lambda: defaultdict(list))
        for module in self.file_manager.get_modules():
            for acl in self.extract_accesses(module):
                if acl.group:
                    for operation in acl.operations:
                        acls[acl.model, operation].add(acl.group)
            for rule in self.extract_rules(module):
                if rule.group:
                    for operation in rule.operations:
                        domain = rule.domain
                        if domain:
                            domain = " ".join(line.strip() for line in domain.splitlines())
                        rules[rule.model, operation][rule.group].append(domain)

        # for each model and operation, determine all group combinations that
        # lead to different accesses
        implied = self.get_groups_implied()

        # {(model, operation, groups): domains}
        result = defaultdict(lambda: defaultdict(list))
        for model_operation in sorted(acls.keys() | rules.keys()):
            acl_groups = acls.get(model_operation)
            if not acl_groups:
                continue  # no user access at all
            rule_groups = rules.get(model_operation) or {}
            acl_rule_groups = acl_groups | rule_groups.keys()

            for combination in powerset(acl_rule_groups):
                # actual user groups include all combination's implied groups
                user_groups = {
                    implied_group
                    for group in combination
                    for implied_group in implied.follow(group)
                }
                if len(EXCLUSIVE_GROUPS & user_groups) > 1:
                    continue
                if 'base.group_public' in user_groups and len(user_groups) > 1:
                    continue
                if 'base.group_portal' in user_groups and len(user_groups) > 1:
                    continue
                if user_groups.isdisjoint(acl_groups):
                    continue

                # a user with user_groups has some access
                user_groups = sorted(user_groups & acl_rule_groups)
                key = (*model_operation, tuple(user_groups))
                if key not in result:
                    domains = sorted(
                        domain
                        for group in user_groups
                        for domain in rule_groups.get(group, ())
                    )
                    # trick: a falsy domain is the TRUE domain
                    result[key] = domains if domains and all(domains) else ["[]"]

        base_path = self.file_manager.get_file('base', '__manifest__.py').addon
        (base_path.parent.parent / 'access_before.log').write_text("\n".join(
            f"{model}, {operation} on {', '.join(groups)}: {' OR '.join(domains)}"
            for (model, operation, groups), domains in sorted(result.items())
        ))

    def log_after(self):
        """ Log the effective access domains in all possible group combinations. """

        # {(model, operation): {group: domains}}
        accesses = defaultdict(lambda: defaultdict(list))
        for module in self.file_manager.get_modules():
            for access in self.extract_accesses(module):
                if access.group:
                    for operation in access.operations:
                        domain = access.domain
                        if domain:
                            domain = " ".join(line.strip() for line in domain.splitlines())
                        accesses[access.model, operation][access.group].append(domain)

        # for each model and operation, determine all group combinations that
        # lead to different accesses
        implied = self.get_groups_implied()

        # {(model, operation, groups): domains}
        result = defaultdict(lambda: defaultdict(list))
        for (model, operation), group_domains in accesses.items():
            for combination in powerset(group_domains):
                # actual user groups include all combination's implied groups
                user_groups = {
                    implied_group
                    for group in combination
                    for implied_group in implied.follow(group)
                }
                if len(EXCLUSIVE_GROUPS & user_groups) > 1:
                    continue
                if 'base.group_public' in user_groups and len(user_groups) > 1:
                    continue
                if 'base.group_portal' in user_groups and len(user_groups) > 1:
                    continue
                if user_groups.isdisjoint(group_domains):
                    continue

                # a user with user_groups has some access
                user_groups = sorted(user_groups & group_domains.keys())
                key = (model, operation, tuple(user_groups))
                if key not in result:
                    domains = sorted(
                        domain
                        for group in sorted(user_groups)
                        for domain in group_domains[group]
                    )
                    result[key] = domains if domains and all(domains) else ["[]"]

        base_path = self.file_manager.get_file('base', '__manifest__.py').addon
        (base_path.parent.parent / 'access_after.log').write_text("\n".join(
            f"{model}, {operation} on {', '.join(groups)}: {' OR '.join(domains)}"
            for (model, operation, groups), domains in sorted(result.items())
        ))

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
        """ Add the given 'data' file to its module's manifest. """

        # add it to the manifest's dict
        manifest = self.get_manifest(module)
        assert file_name not in manifest['data'], f"ERROR {module}: file {file_name!r} found in manifest['data']"
        manifest['data'].append(file_name)

        # add it to the manifest's file
        content = self.get_file_content(module, "__manifest__.py")

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

        self.set_file_content(module, "__manifest__.py", content)

    def remove_from_manifest(self, module: str, file_name: str):
        """ Remove the given file from its module's manifest. """

        # remove it from the manifest's dict
        manifest = self.get_manifest(module)
        assert file_name in manifest['data'], f"File {file_name!r} not found in manifest['data']"
        manifest['data'].remove(file_name)

        # remove it from the manifest's file
        file_pattern = re.escape(str(file_name))
        pattern = rf"""\s*(?P<quote>['"]){file_pattern}(?P=quote),?"""

        content = self.get_file_content(module, "__manifest__.py")
        content = re.sub(pattern, "", content, flags=re.MULTILINE)
        self.set_file_content(module, "__manifest__.py", content)

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

            def get_operations(line_data):
                return {op for op, fname in MODES.items() if int(line_data[fname] or "0")}

        elif file_name.endswith('ir.access.csv'):
            access_model = 'ir.access'

            def get_operations(line_data):
                return set(line_data['operation'])

        else:
            # ignore that CSV file
            return

        content = self.get_file_content(module, file_name)
        reader = csv.reader(io.StringIO(content, newline=''), lineterminator='\n')

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

            operations = get_operations(line_data)

            domain = make_domain(line_data.get('domain'))

            group = line_data[group_field]

            if group:
                yield Access(xid, name, model, with_prefix(module, group), operations, domain)
            elif access_model == 'ir.access':
                yield Access(xid, name, model, group, operations, domain)
            else:
                logger.info("INFO %s: ir.model.access without group, using groups employee, portal, public instead: %s in %s", module, xid, file_name)
                yield Access(xid, name, model, 'base.group_user', operations, domain)
                yield Access(xid, name, model, 'base.group_portal', operations, domain)
                yield Access(xid, name, model, 'base.group_public', operations, domain)

        if remove:
            if lines_to_keep:
                with io.StringIO(newline='') as output:
                    writer = csv.writer(output, lineterminator='\n')
                    writer.writerow(fields)
                    for line in lines_to_keep:
                        writer.writerow(line)
                    content = output.getvalue()
                self.set_file_content(module, file_name, content)
            else:
                self.set_file_content(module, file_name, None)
                self.remove_from_manifest(module, file_name)

    def extract_accesses_from_xml(self, module: str, file_name: str, remove: bool) -> Iterator[Access]:
        logger = _logger if remove else _silent
        tree = etree.fromstring(self.get_file_content(module, file_name).encode())
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
                logger.info("INFO %s: ir.model.access without group, using groups employee, portal, public instead: %s in %s", module, xid, file_name)
                yield Access(xid, name, model, 'base.group_user', operations, domain)
                yield Access(xid, name, model, 'base.group_portal', operations, domain)
                yield Access(xid, name, model, 'base.group_public', operations, domain)

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
            self.remove_from_xml_file(module, file_name, tree, nodes)

    def extract_rules(self, module: str, remove=False) -> Iterator[Access]:
        """ Extract ir.rule records from the given module. """
        manifest = self.get_manifest(module)
        # beware: manifest['data'] may be modified in-place
        for file_name in list(manifest['data']):
            if 'security' in file_name and file_name.endswith('.xml'):
                yield from self.extract_rules_from_xml(module, file_name, remove)

    def extract_rules_from_xml(self, module: str, file_name: str, remove: bool) -> Iterator[Access]:
        logger = _logger if remove else _silent
        tree = etree.fromstring(self.get_file_content(module, file_name).encode())
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

            for group in groups or [None]:
                yield Access(xid, name, model, group, operations, domain)

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
        result = {}
        for module in self.file_manager.get_modules():
            module_path = self.file_manager.get_file(module, '__manifest__.py').addon
            for path in module_path.glob('**/*.py'):
                file = self.file_manager.get_file(module, path.relative_to(module_path))
                for model_name in extract_model_names(file):
                    result[model_xmlid(module, model_name)] = model_name
        return result

    @functools.cache
    def get_groups_implied(self) -> BinaryRelation:
        """ Return the implication relation of all groups. """
        return BinaryRelation(
            (xid, implied_xid)
            for module in self.file_manager.get_modules()
            for file_name in self.get_manifest(module)['data']
            if file_name.endswith('.xml')
            for xid, implied_xids in self._get_groups_from_xml(module, file_name)
            for implied_xid in implied_xids
        )

    def _get_groups_from_xml(self, module: str, file_name: str) -> Iterator[tuple[str, list[str]]]:
        """ Retrieve group definitions from a given XML file. """
        try:
            tree = etree.fromstring(self.get_file_content(module, file_name).encode())
        except UnicodeDecodeError:
            _logger.info("Unexpected encoding, skip %s/%s", module, file_name)
            return

        for node in tree.xpath("//record[@model='res.groups']"):
            xid = with_prefix(module, node.get('id'))
            implied_xids = [
                with_prefix(module, match['ref'])
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


def powerset(items: Iterable) -> Iterator[set]:
    bitmap = {item: 1 << index for index, item in enumerate(items)}
    for number in range(1 << len(bitmap)):
        yield {item for item, bit in bitmap.items() if number & bit}

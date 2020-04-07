# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import collections
from itertools import groupby

from odoo.tests.common import TransactionCase, tagged
import logging
_logger = logging.getLogger(__name__)

def value(rule):
    return sum(int(rule[perm]) for perm in ['perm_read', 'perm_write', 'perm_create', 'perm_unlink']) if rule else 0

@tagged('post_install', '-at_install')
class TestIrRules(TransactionCase):

    def test_useless_ir_rules(self):
        """Finds and logs duplicated ir_rule.

        Such rules should be grouped in one, or one of the two should extend the other.
        """
        self.env.cr.execute("""
            SELECT DISTINCT
                r1.id, r2.id
            FROM
                ir_rule r1,
                ir_rule r2
            WHERE
                r1.id > r2.id
                AND r1.model_id = r2.model_id
                AND r1.domain_force = r2.domain_force
        """)
        IrRule = self.env['ir.rule'].sudo()
        result = self.env.cr.fetchall()
        for r1_id, r2_id in result:
            rule1 = IrRule.browse(r1_id)
            rule2 = IrRule.browse(r2_id)
            joined_groups = rule1.groups & rule2.groups
            if joined_groups:
                _logger.warning("Duplicate rules for model %s, groups %s (%s), %i --> %i, %s" % (
                    rule1.model_id.model,
                    joined_groups.mapped('name'),
                    joined_groups.mapped('full_name'),
                    value(rule1),
                    value(rule2),
                    (rule1 + rule2).mapped('name'))
                )

@tagged('post_install', '-at_install')
class TestIrModelAccess(TransactionCase):

    # def test_useless_accesses(self):
    #     """Finds and logs useless ir.model.access.
    #
    #     Those ACL can either be removed, or merged, or one could extend the other.
    #     NB: even in csv files, you can extend records from other modules ;).
    #     """
    #     models = self.env['ir.model'].sudo().search([])
    #     mapping = dict()
    #     # tuple(group, implied_group) --> [(rule, implied_rule)]
    #     for model in models:
    #         useless_rules = self.env['ir.model.access']
    #         main_public_rules = public_rules = model.access_ids.filtered(lambda a: not a.group_id)
    #         if len(public_rules) > 1:
    #             for public_rule in public_rules:
    #                 for r in (public_rules - public_rule):
    #                     if value(public_rule) <= value(r) and public_rule._is_loaded_after(r):
    #                         _logger.warning(
    #                             "Public rule %s has no impact because loaded after %s",
    #                             public_rule.csv_id,
    #                             r.csv_id,
    #                         )
    #                         main_public_rules -= public_rule
    #
    #         def is_implied_by_public_rules(rule):
    #             if any(
    #                 value(rule) <= value(public_rule)
    #                 and rule._is_loaded_after(public_rule)
    #                 for public_rule in main_public_rules
    #             ):
    #                 return True
    #             return False
    #
    #         for rule in (model.access_ids - public_rules):
    #             if is_implied_by_public_rules(rule):
    #                 useless_rules += rule
    #             elif rule.group_id:
    #                 implied_accesses = rule.group_id.trans_implied_ids.model_access.filtered(lambda r: r.model_id == model)
    #                 for implied_rule in implied_accesses:
    #                     if value(implied_rule) >= value(rule) and rule._is_loaded_after(implied_rule):
    #                         key = (rule.group_id.id, implied_rule.group_id.id)
    #                         mapping.setdefault(key, [])
    #                         mapping[key] += [(rule.csv_id, implied_rule.csv_id)]
    #
    #         if useless_rules:
    #             _logger.warning(
    #                 "Model %s has public rules giving more or as much rights as rules: %s",
    #                 model.model, useless_rules.mapped('csv_id'),
    #             )
    #
    #     Groups = self.env["res.groups"]
    #     for key, values in mapping.items():
    #         group, implied_group = Groups.browse(key[0]), Groups.browse(key[1])
    #         _logger.warning("Group %s implies group %s:", group.xml_id, implied_group.xml_id)
    #         for pair in values:
    #             _logger.warning("\t Rule %s is useless because of %s", pair[0], pair[1])

    def test_useless_accesses_by_module(self):
        """Finds and logs useless ir.model.access.

        Those ACL can either be removed, or merged, or one could extend the other.
        NB: even in csv files, you can extend records from other modules ;).
        """
        MSG = "Rule %s is loaded before and gives as much or more rights."
        MSG_GROUP = "Group %s implies group %s having rule %s, loaded before and giving as much or more rights."
        models = self.env["ir.model"].sudo().search([])
        mapping = collections.defaultdict(dict)
        # tuple(group, implied_group) --> [(rule, implied_rule)]
        # module_name --> xml_id --> reason
        for model in models:
            rules_to_check = model.access_ids
            # Catch duplicate public rules for model
            public_rules = rules_to_check.filtered(lambda a: not a.group_id)
            main_public_rules = self.env["ir.model.access"]
            if len(public_rules) > 1:
                for rule in public_rules:
                    implying_rule = rule._is_implied_by(public_rules - rule)
                    if implying_rule:
                        mapping[rule.module_name][rule.csv_id] = MSG % implying_rule.csv_id
                    else:
                        main_public_rules += rule

            # Catch rules useless because implied by public rule
            # OR implied by the rule of an implied group
            rules_to_check -= public_rules
            for rule in rules_to_check:
                # access already given by a public rule
                implying_rule = rule._is_implied_by(main_public_rules)
                if not implying_rule:
                    # access given by other rule of same group, loaded before
                    implying_rule = rule._is_implied_by(
                        rule.group_id.model_access.filtered(lambda r: r.model_id == model) - rule
                    )
                if not implying_rule:
                    # access given by an implied group
                    implying_rule = rule._is_implied_by(
                        rule.group_id.trans_implied_ids.model_access.filtered(lambda r: r.model_id == model)
                    )

                if implying_rule and not implying_rule.group_id:
                    mapping[rule.module_name][rule.csv_id] = MSG % implying_rule.csv_id
                    rules_to_check -= rule
                elif implying_rule and implying_rule.group_id:
                    mapping[rule.module_name][rule.csv_id] = MSG_GROUP % (
                        rule.group_id.xml_id,
                        implying_rule.group_id.xml_id,
                        implying_rule.csv_id,
                    )
                    rules_to_check -= rule

            # Catch duplicates targeting same group/model in the data of a module
            for keys, accesses in groupby(rules_to_check, key=lambda x: [x.group_id.xml_id, x.module_name]):
                records = list(accesses)
                if len(records) > 1:
                    _logger.error(
                        "Defining multiple rules for same group/model %s/%s in same module %s : %s",
                        keys[0], model.model, keys[1], [access.data_name for access in records],
                    )
                    for a in accesses:
                        rules_to_check -= a

            # Catch duplicate rules targeting same group/model
            for group, accesses in groupby(rules_to_check, key=lambda x: x.group_id):
                records = list(accesses)
                for rule in accesses:
                    implying_rule = rule._is_implied_by(accesses)
                    if implying_rule:
                        mapping[rule.module_name][rule.csv_id] = MSG % implying_rule.csv_id

        for module, accesses_dict in mapping.items():
            _logger.warning("Module %s: useless ACLs", module)
            for csv_id, log in accesses_dict.items():
                _logger.warning("\t %s: %s", csv_id, log)


    # TODO how to be sure an implied_group has been set before the useless rule of the current group ????
    # A deeper investigation of rule and module dependencies is maybe needed...
    # VFE TODO migration test ensuring for all groups the same abilities for each model ?

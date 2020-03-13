# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
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
        # TODO do it in a better way for perfs ?
        rules = self.env['ir.rule'].sudo().search([])
        for rule in rules:
            for group in rule.groups:
                same_model_group_rules = rule.model_id.rule_ids.filtered_domain([
                    ('groups', 'in', group.id),
                    ('domain_force', '=', rule.domain_force)])
                if len(same_model_group_rules) > 1:
                    _logger.warning("Duplicate rules for model %s, group %s (%s), %i --> %i, %s" % (
                        rule.model_id.model, group.name, group.full_name,
                        value(rule), value((same_model_group_rules-rule)[0]),
                        same_model_group_rules.mapped('name')))

@tagged('post_install', '-at_install')
class TestIrModelAccess(TransactionCase):

    def test_useless_accesses(self):
        """Finds and logs useless ir.model.access.

        Those ACL can either be removed, or merged, or one could extend the other.
        NB: even in csv files, you can extend records from other modules ;).
        """
        models = self.env['ir.model'].sudo().search([])
        mapping = dict()
        # tuple(group, implied_group) --> [(rule, implied_rule)]
        for model in models:
            useless_rules = self.env['ir.model.access']
            main_public_rules = public_rules = model.access_ids.filtered(lambda a: not a.group_id)
            if len(public_rules) > 1:
                for public_rule in public_rules:
                    for r in (public_rules - public_rule):
                        if value(public_rule) <= value(r) and public_rule._is_loaded_after(r):
                            _logger.warning(
                                "Public rule %s has no impact because loaded after %s",
                                public_rule.csv_id,
                                r.csv_id,
                            )
                            main_public_rules -= public_rule

            def is_implied_by_public_rules(rule):
                if any(
                    value(rule) <= value(public_rule)
                    and rule._is_loaded_after(public_rule)
                    for public_rule in main_public_rules
                ):
                    return True
                return False

            for rule in (model.access_ids - public_rules):
                if is_implied_by_public_rules(rule):
                    useless_rules += rule
                elif rule.group_id:
                    implied_accesses = rule.group_id.trans_implied_ids.model_access.filtered(lambda r: r.model_id == model)
                    for implied_rule in implied_accesses:
                        if value(implied_rule) >= value(rule) and rule._is_loaded_after(implied_rule):
                            key = (rule.group_id.id, implied_rule.group_id.id)
                            mapping.setdefault(key, [])
                            mapping[key] += [(rule.csv_id, implied_rule.csv_id)]

            if useless_rules:
                _logger.warning(
                    "Model %s has public rules giving more or as much rights as rules: %s",
                    model.model, useless_rules.mapped('csv_id'),
                )

        Groups = self.env["res.groups"]
        for key, values in mapping.items():
            group, implied_group = Groups.browse(key[0]), Groups.browse(key[1])
            _logger.warning("Group %s implies group %s:", group.xml_id, implied_group.xml_id)
            for pair in values:
                _logger.warning("\t Rule %s is useless because of %s", pair[0], pair[1])

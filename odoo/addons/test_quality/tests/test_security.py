# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests.common import TransactionCase, tagged
from collections import defaultdict
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
        # Child of stock purchase
        modules_take_in_account = "stock_dropshipping,partner_commission,approvals_purchase_stock,mrp_subcontracting,pos_blackbox_be,stock_barcode_picking_batch,l10n_in_purchase_stock,sale_purchase_stock,pos_mercury,sale_timesheet_purchase,stock_picking_batch,pos_hr,pos_account_reports,mrp_product_expiry,purchase_intrastat,sale_amazon_delivery,quality_iot,mrp_subcontracting_account,mrp,pos_epson_printer_restaurant,helpdesk_stock,purchase,sale_mrp,delivery_barcode,delivery,quality,purchase_requisition_stock,purchase_requisition,delivery_fedex,sale_purchase_inter_company_rules,mrp_landed_costs,sale_purchase,quality_mrp_workorder,repair,stock_barcode_quality_control,pos_six,l10n_in_sale_stock,stock,website_sale_delivery,mrp_workorder_iot,account_invoice_extract_purchase,pos_sale,stock_account_enterprise,pos_hr_l10n_be,quality_control,pos_discount,stock_barcode_quality_control_picking_batch,account_3way_match,stock_account,l10n_co_pos,mrp_subcontracting_dropshipping,sale_amazon_taxcloud,mrp_workorder,mrp_plm,product_expiry,purchase_enterprise,helpdesk_repair,pos_adyen,quality_control_picking_batch,delivery_iot,l10n_in_stock,mrp_mps,stock_sms,purchase_stock,pos_coupon,point_of_sale,pos_restaurant,delivery_ups,purchase_mrp,quality_mrp,website_sale_stock_product_configurator,mrp_account_enterprise,pos_epson_printer,website_delivery_ups,approvals_purchase,l10n_mx_edi_landing,sale_stock_renting,quality_mrp_workorder_iot,stock_landed_costs,website_sale_coupon_delivery,pos_cache,pos_iot,delivery_usps,website_sale_taxcloud_delivery,sale_coupon_delivery,stock_intrastat,mrp_account,stock_accountant,purchase_mrp_workorder_quality,mrp_workorder_expiry,sale_amazon,sale_stock_margin,stock_barcode_mrp_subcontracting,industry_fsm_stock,delivery_easypost,website_sale_stock,delivery_bpost,pos_enterprise,purchase_stock_enterprise,sale_coupon_taxcloud_delivery,l10n_fr_pos_cert,quality_control_iot,pos_restaurant_iot,l10n_in_pos,pos_hr_mobile,stock_barcode_mobile,stock_enterprise,pos_loyalty,delivery_dhl,mrp_maintenance,sale_ebay,stock_barcode,sale_stock,l10n_in_purchase,purchase_product_matrix,pos_restaurant_adyen"
        modules_take_in_account = set(modules_take_in_account.split(","))

        models = self.env['ir.model'].sudo().search([])
        mapping = defaultdict(list)
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
                            if rule.module not in modules_take_in_account:
                                continue
                            key = (rule.group_id.id, implied_rule.group_id.id)
                            mapping[key] += [(rule.csv_id, implied_rule.csv_id)]

            if useless_rules:
                _logger.warning(
                    "Model %s has public rules giving more or as much rights as rules: %s",
                    model.model, useless_rules.mapped('csv_id'),
                )

        Groups = self.env["res.groups"]
        for key, values in mapping.items():
            group, implied_group = Groups.browse(key[0]), Groups.browse(key[1])
            print("Because group %s implies group %s:" % (group.xml_id, implied_group.xml_id))
            for pair in values:
                print(" - Rule %s.%s is useless because of %s.%s" % (pair[0].split(".")[0], pair[0].split(".")[1], pair[1].split(".")[0], pair[1].split(".")[1]))

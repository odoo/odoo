from collections import defaultdict

from odoo import api, models, _
from odoo.tools import frozendict


class StockRule(models.Model):
    _inherit = 'stock.rule'

    @api.model
    def _get_lead_days_for_combinations(self, combinations):
        """ Batched version of _get_lead_days taking a sequence of
        triplets (stock.rules, product, value_dict)
        """
        combinations = {(rules, product, frozendict(value_dict)) for rules, product, value_dict in combinations}
        subcontracting_combinations = set()
        other_combinations = set()
        bypass_delay_description = self.env.context.get('bypass_delay_description')
        seen_buy_rules = {}
        seen_sellers = {}
        products_sellers_by_company = defaultdict(
            lambda: {
                "products": self.env["product.product"],
                "sellers": self.env["product.supplierinfo"],
            }
        )
        for rules, product, value_dict in combinations:
            if rules not in seen_buy_rules:
                seen_buy_rules[rules] = rules.filtered(lambda r: r.action == 'buy')
            buy_rule = seen_buy_rules[rules]
            if (product, value_dict, buy_rule) not in seen_sellers:
                seller = (
                    ("supplierinfo" in value_dict and value_dict["supplierinfo"])
                    or product.with_company(buy_rule.company_id)._select_seller(quantity=None)
                )
                seen_sellers[product, value_dict, buy_rule] = (seller and seller[0])
            seller = seen_sellers[product, value_dict, buy_rule]
            if not buy_rule or not seller:
                other_combinations.add((rules, product, value_dict))
                continue
            company = buy_rule.picking_type_id.company_id
            products_sellers_by_company[company]['products'] |= product
            products_sellers_by_company[company]['sellers'] |= seller
        # Group by company to call _bom_subcontract_find in batches.
        bom_by_company_subcontractor_product = {}
        for company, products_sellers in products_sellers_by_company.items():
            bom_dict = self.env['mrp.bom'].sudo()._bom_subcontract_find_for_products(
                products_sellers['products'],
                company_id=company.id,
                bom_type='subcontract',
                subcontractors=products_sellers['sellers'].partner_id,
            )
            for (product, partner_id), bom in bom_dict.items():
                bom_by_company_subcontractor_product[company, product, partner_id] = bom
        # Check if combinations have a subcontracting bom
        subcontracting_combinations_without_rule = set()
        rule_combinations = set()
        for rules, product, value_dict in (combinations - other_combinations):
            buy_rule = seen_buy_rules[rules]
            subcontractor = seen_sellers[product, value_dict, buy_rule].partner_id
            if (buy_rule.picking_type_id.company_id, product, subcontractor) in bom_by_company_subcontractor_product:
                subcontracting_combinations.add((rules, product, value_dict))
                subcontracting_combinations_without_rule.add((rules - buy_rule, product, value_dict))
                rule_combinations.add((buy_rule, product, value_dict))
            else:
                other_combinations.add((rules, product, value_dict))
        lead_days_delays = super()._get_lead_days_for_combinations(other_combinations)
        subcontracting_lead_days_delays = super()._get_lead_days_for_combinations(subcontracting_combinations_without_rule)
        extra_lead_days_delays = super(
            StockRule,
            self.with_context(ignore_vendor_lead_time=True, global_visibility_days=0),
        )._get_lead_days_for_combinations(rule_combinations)
        # Compute lead_days for combinations with Manufacturing Time + Vendor Lead Time.
        for rules, product, value_dict in subcontracting_combinations:
            buy_rule = seen_buy_rules[rules]
            seller = seen_sellers[product, value_dict, buy_rule]
            bom = bom_by_company_subcontractor_product[buy_rule.picking_type_id.company_id, product, seller.partner_id]
            delays, delay_description = subcontracting_lead_days_delays[(rules - buy_rule), product, value_dict]
            extra_delays, extra_delay_description = extra_lead_days_delays[buy_rule, product, value_dict]
            if seller.delay >= bom.produce_delay + bom.days_to_prepare_mo:
                delays['total_delay'] += seller.delay
                delays['purchase_delay'] += seller.delay
                if not bypass_delay_description:
                    delay_description.append((_('Vendor Lead Time'), _('+ %d day(s)', seller.delay)))
            else:
                manufacture_delay = bom.produce_delay
                delays['total_delay'] += manufacture_delay
                # set manufacture_delay to purchase_delay so that PO can be created with correct date
                delays['purchase_delay'] += manufacture_delay
                if not bypass_delay_description:
                    delay_description.append((_('Manufacturing Lead Time'), _('+ %d day(s)', manufacture_delay)))
                days_to_order = bom.days_to_prepare_mo
                delays['total_delay'] += days_to_order
                # add dtpmo to purchase_delay so that PO can be created with correct date
                delays['purchase_delay'] += days_to_order
                if not bypass_delay_description:
                    extra_delay_description.append((_('Days to Supply Components'), _('+ %d day(s)', days_to_order)))
            for key, value in extra_delays.items():
                delays[key] += value
            lead_days_delays[rules, product, value_dict] = (delays, delay_description + extra_delay_description)
        return lead_days_delays

    def _get_lead_days(self, product, **values):
        """For subcontracting, we need to consider both vendor lead time and
        manufacturing lead time, and DTPMO (Days To Prepare MO).
        Subcontracting delay =
            max(Vendor lead time, Manufacturing lead time + DTPMO) + Days to Purchase + Purchase security lead time
        """
        return super()._get_lead_days(product, **values)

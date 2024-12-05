from odoo import models, _


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _get_lead_days(self, product, **values):
        """For subcontracting, we need to consider both vendor lead time and
        manufacturing lead time, and DTPMO (Days To Prepare MO).
        Subcontracting delay =
            max(Vendor lead time, Manufacturing lead time + DTPMO) + Days to Purchase + Purchase security lead time
        """
        bypass_delay_description = self.env.context.get('bypass_delay_description')
        buy_rule = self.filtered(lambda r: r.action == 'buy')
        seller = 'supplierinfo' in values and values['supplierinfo'] or product.with_company(buy_rule.company_id)._select_seller(quantity=None)
        if not buy_rule or not seller:
            return super()._get_lead_days(product, **values)
        seller = seller[0]
        bom = self.env['mrp.bom'].sudo()._bom_subcontract_find(
            product,
            company_id=buy_rule.picking_type_id.company_id.id,
            bom_type='subcontract',
            subcontractor=seller.partner_id)
        if not bom:
            return super()._get_lead_days(product, **values)

        delays, delay_description = super(StockRule, self - buy_rule)._get_lead_days(product, **values)
        extra_delays, extra_delay_description = super(StockRule, buy_rule.with_context(ignore_vendor_lead_time=True, global_visibility_days=0))._get_lead_days(product, **values)
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
        return delays, delay_description + extra_delay_description

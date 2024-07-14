# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.crm.tests import common as crm_common
from odoo.tests.common import Form, users


class TestLead(crm_common.TestCrmCommon):

    @users('user_sales_leads')
    def test_propagation_lead_user_to_rental_order(self):
        """ Priority for default salesperson on rental order from a lead should be
        1) The one on the lead 2) The one on the partner 3) The current user """
        SaleOrder = self.env['sale.order']
        lead = self.env['crm.lead'].browse(self.lead_1.ids)
        partner = self.contact_1
        lead.partner_id = partner

        lead.user_id = self.user_sales_manager
        partner.user_id = self.user_sales_salesman
        rental_order_form = Form(SaleOrder.with_context(lead._get_action_rental_context()))
        rental_order = rental_order_form.save()
        self.assertEqual(rental_order.user_id, self.user_sales_manager, 'The salesperson of the lead is set and should be propagated on the rental order.')

        lead.user_id = False
        rental_order_form = Form(SaleOrder.with_context(lead._get_action_rental_context()))
        rental_order = rental_order_form.save()
        self.assertEqual(rental_order.user_id, self.user_sales_salesman, 'The salesperson of contact is set and should be propagated on the rental order.')

        partner.user_id = False
        rental_order_form = Form(SaleOrder.with_context(lead._get_action_rental_context()))
        rental_order = rental_order_form.save()
        self.assertEqual(rental_order.user_id, self.user_sales_leads, 'The salesperson of the current user should be propagated on the rental order.')

    @users('user_sales_leads')
    def test_rental_and_sale_fields(self):
        lead = self.env['crm.lead'].browse(self.lead_1.ids)
        recurrence_day = self.env['sale.temporal.recurrence'].sudo().create({'duration': 1, 'unit': 'day'})
        rental_product = self.env['product.product'].sudo().create({
            'extra_daily': 10,
            'extra_hourly': 5,
            'list_price': 100,
            'name': 'Rent Product',
            'rent_ok': True,
            'type': 'consu',
            'product_pricing_ids': self.env['product.pricing'].sudo().create({
                'recurrence_id': recurrence_day.id,
                'price': 100,
            }),
        })

        base_order_vals = {
            'is_rental_order': True,
            'order_line': [
                (0, 0, {'product_id': rental_product.id,
                        'product_uom_qty': 2,
                       }
                )],
            'opportunity_id': lead.id,
            'partner_id': self.contact_1.id,
        }

        orders = self.env['sale.order'].create([
            dict(base_order_vals),
            dict(base_order_vals),
            dict(base_order_vals)
        ])
        orders.order_line.update({'is_rental': True})
        orders[0:2].action_confirm()
        self.env.flush_all()

        self.assertEqual(lead.rental_quotation_count, 1)
        self.assertEqual(lead.rental_order_count, 2)
        self.assertEqual(lead.rental_amount_total, 2*2*100)

        # Check that sale_order_count and, quotation_count and sale_amount_total
        # fields on the lead does not include rental quotations / orders
        del base_order_vals['is_rental_order']
        orders = self.env['sale.order'].create([
            base_order_vals,
            base_order_vals,
        ])
        self.assertEqual(len(lead.order_ids), 5, "'order_ids' contains all the linked orders(rental or not)")
        self.assertEqual(lead.quotation_count, 2, "'quotation_count' should exclude data of rental quotations")
        self.assertEqual(lead.sale_order_count, 0, "'sale_order_count' should exclude data of rental orders")
        self.assertEqual(lead.sale_amount_total, 0, "'sale_amount_total' should exclude data of rental orders")
        orders[1].action_confirm()
        self.assertEqual(lead.quotation_count, 1, "there should be only one regular(non rental) quotation left")
        self.assertEqual(lead.sale_order_count, 1, "there should be one regular(non rental) sale order(s)")
        self.assertEqual(lead.sale_amount_total, 2*100, "should give total for the regular(non rental) sale order(s) only")

        # Check that all the rental related computations are not affected
        self.assertEqual(lead.rental_quotation_count, 1)
        self.assertEqual(lead.rental_order_count, 2)
        self.assertEqual(lead.rental_amount_total, 2*2*100)

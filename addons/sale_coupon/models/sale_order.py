# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools.misc import formatLang


class SaleOrder(models.Model):
    _inherit = "sale.order"

    applied_coupon_ids = fields.One2many('coupon.coupon', 'sales_order_id', string="Applied Coupons", copy=False)
    generated_coupon_ids = fields.One2many('coupon.coupon', 'order_id', string="Offered Coupons", copy=False)
    reward_amount = fields.Float(compute='_compute_reward_total')
    no_code_promo_program_ids = fields.Many2many('coupon.program', string="Applied Immediate Promo Programs",
        domain="[('promo_code_usage', '=', 'no_code_needed'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]", copy=False)
    code_promo_program_id = fields.Many2one('coupon.program', string="Applied Promo Program",
        domain="[('promo_code_usage', '=', 'code_needed'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]", copy=False)
    promo_code = fields.Char(related='code_promo_program_id.promo_code', help="Applied program code", readonly=False)

    @api.depends('order_line')
    def _compute_reward_total(self):
        for order in self:
            order.reward_amount = sum([line.price_subtotal for line in order._get_reward_lines()])

    def _get_no_effect_on_threshold_lines(self):
        self.ensure_one()
        lines = self.env['sale.order.line']
        return lines

    def recompute_coupon_lines(self):
        for order in self:
            order._remove_invalid_reward_lines()
            if order.state != 'cancel':
                order._create_new_no_code_promo_reward_lines()
            order._update_existing_reward_lines()

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        order = super(SaleOrder, self).copy(default)
        reward_line = order._get_reward_lines()
        if reward_line:
            reward_line.unlink()
            order._create_new_no_code_promo_reward_lines()
        return order

    def action_confirm(self):
        self.generated_coupon_ids.write({'state': 'new'})
        self.applied_coupon_ids.write({'state': 'used'})
        self._send_reward_coupon_mail()
        return super(SaleOrder, self).action_confirm()

    def _action_cancel(self):
        res = super()._action_cancel()
        self.generated_coupon_ids.write({'state': 'expired'})
        self.applied_coupon_ids.write({'state': 'new'})
        self.applied_coupon_ids.sales_order_id = False
        self.recompute_coupon_lines()
        return res

    def action_draft(self):
        res = super(SaleOrder, self).action_draft()
        self.generated_coupon_ids.write({'state': 'reserved'})
        return res

    def _get_reward_lines(self):
        self.ensure_one()
        return self.order_line.filtered(lambda line: line.is_reward_line)

    def _is_reward_in_order_lines(self, program):
        self.ensure_one()
        order_quantity = sum(self.order_line.filtered(lambda line:
            line.product_id == program.reward_product_id).mapped('product_uom_qty'))
        return order_quantity >= program.reward_product_quantity

    def _is_global_discount_already_applied(self):
        applied_programs = self.no_code_promo_program_ids + \
                           self.code_promo_program_id + \
                           self.applied_coupon_ids.mapped('program_id')
        return applied_programs.filtered(lambda program: program._is_global_discount_program())

    def _get_reward_values_product(self, program):
        price_unit = self.order_line.filtered(lambda line: program.reward_product_id == line.product_id)[0].price_reduce

        order_lines = (self.order_line - self._get_reward_lines()).filtered(lambda x: program._get_valid_products(x.product_id))
        max_product_qty = sum(order_lines.mapped('product_uom_qty')) or 1
        total_qty = sum(self.order_line.filtered(lambda x: x.product_id == program.reward_product_id).mapped('product_uom_qty'))
        # Remove needed quantity from reward quantity if same reward and rule product
        if program._get_valid_products(program.reward_product_id):
            # number of times the program should be applied
            program_in_order = max_product_qty // (program.rule_min_quantity + program.reward_product_quantity)
            # multipled by the reward qty
            reward_product_qty = program.reward_product_quantity * program_in_order
            # do not give more free reward than products
            reward_product_qty = min(reward_product_qty, total_qty)
            if program.rule_minimum_amount:
                order_total = sum(order_lines.mapped('price_total')) - (program.reward_product_quantity * program.reward_product_id.lst_price)
                reward_product_qty = min(reward_product_qty, order_total // program.rule_minimum_amount)
        else:
            program_in_order = max_product_qty // program.rule_min_quantity
            reward_product_qty = min(program.reward_product_quantity * program_in_order, total_qty)

        reward_qty = min(int(int(max_product_qty / program.rule_min_quantity) * program.reward_product_quantity), reward_product_qty)
        # Take the default taxes on the reward product, mapped with the fiscal position
        taxes = program.reward_product_id.taxes_id.filtered(lambda t: t.company_id.id == self.company_id.id)
        taxes = self.fiscal_position_id.map_tax(taxes)
        return {
            'product_id': program.discount_line_product_id.id,
            'price_unit': - price_unit,
            'product_uom_qty': reward_qty,
            'is_reward_line': True,
            'name': _("Free Product") + " - " + program.reward_product_id.name,
            'product_uom': program.reward_product_id.uom_id.id,
            'tax_id': [(4, tax.id, False) for tax in taxes],
        }

    def _get_paid_order_lines(self):
        """ Returns the sale order lines that are not reward lines.
            It will also return reward lines being free product lines. """
        free_reward_product = self.env['coupon.program'].search([('reward_type', '=', 'product')]).mapped('discount_line_product_id')
        return self.order_line.filtered(lambda x: not x._is_not_sellable_line() or x.product_id in free_reward_product)

    def _get_base_order_lines(self, program):
        """ Returns the sale order lines not linked to the given program.
        """
        return self.order_line.filtered(lambda x: not x._is_not_sellable_line() or (x.is_reward_line and x.product_id != program.discount_line_product_id))

    def _get_reward_values_discount_fixed_amount(self, program):
        total_amount = sum(self._get_base_order_lines(program).mapped('price_total'))
        fixed_amount = program._compute_program_amount('discount_fixed_amount', self.currency_id)
        if total_amount < fixed_amount:
            return total_amount
        else:
            return fixed_amount

    def _get_coupon_program_domain(self):
        return []

    def _get_cheapest_line(self):
        # Unit prices tax included
        return min(self.order_line.filtered(lambda x: not x._is_not_sellable_line() and x.price_reduce > 0), key=lambda x: x['price_reduce'])

    def _get_reward_values_discount_percentage_per_line(self, program, line):
        discount_amount = line.product_uom_qty * line.price_reduce * (program.discount_percentage / 100)
        return discount_amount

    def _get_max_reward_values_per_tax(self, program, taxes):
        lines = self.order_line.filtered(lambda l: l.tax_id == taxes and l.product_id != program.discount_line_product_id)
        return sum(lines.mapped(lambda l: l.price_reduce * l.product_uom_qty))

    def _get_reward_values_fixed_amount(self, program):
        discount_amount = self._get_reward_values_discount_fixed_amount(program)

        # In case there is a tax set on the promotion product, we give priority to it.
        # This allow manual overwrite of taxes for promotion.
        if program.discount_line_product_id.taxes_id:
            line_taxes = self.fiscal_position_id.map_tax(program.discount_line_product_id.taxes_id) if self.fiscal_position_id else program.discount_line_product_id.taxes_id
            return [{
                'name': _("Discount: %s", program.name),
                'product_id': program.discount_line_product_id.id,
                'price_unit': -discount_amount,
                'product_uom_qty': 1.0,
                'product_uom': program.discount_line_product_id.uom_id.id,
                'is_reward_line': True,
                'tax_id': [(4, tax.id, False) for tax in line_taxes],
            }]

        lines = self._get_paid_order_lines()
        # Remove Free Lines
        lines = lines.filtered('price_reduce')
        reward_lines = {}

        tax_groups = set([line.tax_id for line in lines])
        max_discount_per_tax_groups = {tax_ids: self._get_max_reward_values_per_tax(program, tax_ids) for tax_ids in tax_groups}

        for tax_ids in sorted(tax_groups, key=lambda tax_ids: max_discount_per_tax_groups[tax_ids], reverse=True):

            if discount_amount <= 0:
                return reward_lines.values()

            curr_lines = lines.filtered(lambda l: l.tax_id == tax_ids)
            lines_price = sum(curr_lines.mapped(lambda l: l.price_reduce * l.product_uom_qty))
            lines_total = sum(curr_lines.mapped('price_total'))

            discount_line_amount_price = min(max_discount_per_tax_groups[tax_ids], (discount_amount * lines_price / lines_total))

            if not discount_line_amount_price:
                continue

            discount_amount -= discount_line_amount_price * lines_total / lines_price

            reward_lines[tax_ids] = {
                'name': _(
                    "Discount: %(program)s - On product with following taxes: %(taxes)s",
                    program=program.name,
                    taxes=", ".join(tax_ids.mapped('name')),
                ),
                'product_id': program.discount_line_product_id.id,
                'price_unit': -discount_line_amount_price,
                'product_uom_qty': 1.0,
                'product_uom': program.discount_line_product_id.uom_id.id,
                'is_reward_line': True,
                'tax_id': [(4, tax.id, False) for tax in tax_ids],
                }
        return reward_lines.values()

    def _get_reward_values_discount(self, program):
        if program.discount_type == 'fixed_amount':
            return self._get_reward_values_fixed_amount(program)
        else:
            return self._get_reward_values_percentage_amount(program)

    def _get_reward_values_percentage_amount(self, program):
        # Invalidate multiline fixed_price discount line as they should apply after % discount
        fixed_price_products = self._get_applied_programs().filtered(
            lambda p: p.discount_type == 'fixed_amount'
        ).mapped('discount_line_product_id')
        self.order_line.filtered(lambda l: l.product_id in fixed_price_products).write({'price_unit': 0})

        reward_dict = {}
        lines = self._get_paid_order_lines()
        amount_total = sum([any(line.tax_id.mapped('price_include')) and line.price_total or line.price_subtotal
                            for line in self._get_base_order_lines(program)])
        if program.discount_apply_on == 'cheapest_product':
            line = self._get_cheapest_line()
            if line:
                discount_line_amount = min(line.price_reduce * (program.discount_percentage / 100), amount_total)
                if discount_line_amount:
                    taxes = self.fiscal_position_id.map_tax(line.tax_id)

                    reward_dict[line.tax_id] = {
                        'name': _("Discount: %s", program.name),
                        'product_id': program.discount_line_product_id.id,
                        'price_unit': - discount_line_amount if discount_line_amount > 0 else 0,
                        'product_uom_qty': 1.0,
                        'product_uom': program.discount_line_product_id.uom_id.id,
                        'is_reward_line': True,
                        'tax_id': [(4, tax.id, False) for tax in taxes],
                    }
        elif program.discount_apply_on in ['specific_products', 'on_order']:
            if program.discount_apply_on == 'specific_products':
                # We should not exclude reward line that offer this product since we need to offer only the discount on the real paid product (regular product - free product)
                free_product_lines = self.env['coupon.program'].search([('reward_type', '=', 'product'), ('reward_product_id', 'in', program.discount_specific_product_ids.ids)]).mapped('discount_line_product_id')
                lines = lines.filtered(lambda x: x.product_id in (program.discount_specific_product_ids | free_product_lines))

            # when processing lines we should not discount more than the order remaining total
            currently_discounted_amount = 0
            for line in lines:
                discount_line_amount = min(self._get_reward_values_discount_percentage_per_line(program, line), amount_total - currently_discounted_amount)

                if discount_line_amount:

                    if line.tax_id in reward_dict:
                        reward_dict[line.tax_id]['price_unit'] -= discount_line_amount
                    else:
                        taxes = self.fiscal_position_id.map_tax(line.tax_id)

                        reward_dict[line.tax_id] = {
                            'name': _(
                                "Discount: %(program)s - On product with following taxes: %(taxes)s",
                                program=program.name,
                                taxes=", ".join(taxes.mapped('name')),
                            ),
                            'product_id': program.discount_line_product_id.id,
                            'price_unit': - discount_line_amount if discount_line_amount > 0 else 0,
                            'product_uom_qty': 1.0,
                            'product_uom': program.discount_line_product_id.uom_id.id,
                            'is_reward_line': True,
                            'tax_id': [(4, tax.id, False) for tax in taxes],
                        }
                        currently_discounted_amount += discount_line_amount

        # If there is a max amount for discount, we might have to limit some discount lines or completely remove some lines
        max_amount = program._compute_program_amount('discount_max_amount', self.currency_id)
        if max_amount > 0:
            amount_already_given = 0
            for val in list(reward_dict):
                amount_to_discount = amount_already_given + reward_dict[val]["price_unit"]
                if abs(amount_to_discount) > max_amount:
                    reward_dict[val]["price_unit"] = - (max_amount - abs(amount_already_given))
                    add_name = formatLang(self.env, max_amount, currency_obj=self.currency_id)
                    reward_dict[val]["name"] += "( " + _("limited to ") + add_name + ")"
                amount_already_given += reward_dict[val]["price_unit"]
                if reward_dict[val]["price_unit"] == 0:
                    del reward_dict[val]
        return reward_dict.values()

    def _get_reward_line_values(self, program):
        self.ensure_one()
        self = self.with_context(lang=self.partner_id.lang)
        program = program.with_context(lang=self.partner_id.lang)
        if program.reward_type == 'discount':
            return self._get_reward_values_discount(program)
        elif program.reward_type == 'product':
            return [self._get_reward_values_product(program)]

    def _create_reward_line(self, program):
        self.write({'order_line': [(0, False, value) for value in self._get_reward_line_values(program)]})

    def _create_reward_coupon(self, program):
        # if there is already a coupon that was set as expired, reactivate that one instead of creating a new one
        coupon = self.env['coupon.coupon'].search([
            ('program_id', '=', program.id),
            ('state', '=', 'expired'),
            ('partner_id', '=', self.partner_id.id),
            ('order_id', '=', self.id),
            ('discount_line_product_id', '=', program.discount_line_product_id.id),
        ], limit=1)
        if coupon:
            coupon.write({'state': 'reserved'})
        else:
            coupon = self.env['coupon.coupon'].sudo().create({
                'program_id': program.id,
                'state': 'reserved',
                'partner_id': self.partner_id.id,
                'order_id': self.id,
                'discount_line_product_id': program.discount_line_product_id.id
            })
        self.generated_coupon_ids |= coupon
        return coupon

    def _send_reward_coupon_mail(self):
        template = self.env.ref('sale_coupon.mail_template_sale_coupon', raise_if_not_found=False)
        if template:
            for order in self:
                for coupon in order.generated_coupon_ids:
                    order.message_post_with_template(
                        template.id, composition_mode='comment',
                        model='coupon.coupon', res_id=coupon.id,
                        email_layout_xmlid='mail.mail_notification_light',
                    )

    def _get_applicable_programs(self):
        """
        This method is used to return the valid applicable programs on given order.
        """
        self.ensure_one()
        programs = self.env['coupon.program'].with_context(
            no_outdated_coupons=True,
        ).search([
            ('company_id', 'in', [self.company_id.id, False]),
            '|', ('rule_date_from', '=', False), ('rule_date_from', '<=', fields.Datetime.now()),
            '|', ('rule_date_to', '=', False), ('rule_date_to', '>=', fields.Datetime.now()),
        ], order="id")._filter_programs_from_common_rules(self)
        # no impact code...
        # should be programs = programs.filtered if we really want to filter...
        # if self.promo_code:
        #     programs._filter_promo_programs_with_code(self)
        return programs

    def _get_applicable_no_code_promo_program(self):
        self.ensure_one()
        programs = self.env['coupon.program'].with_context(
            no_outdated_coupons=True,
            applicable_coupon=True,
        ).search([
            ('promo_code_usage', '=', 'no_code_needed'),
            '|', ('rule_date_from', '=', False), ('rule_date_from', '<=', fields.Datetime.now()),
            '|', ('rule_date_to', '=', False), ('rule_date_to', '>=', fields.Datetime.now()),
            '|', ('company_id', '=', self.company_id.id), ('company_id', '=', False),
        ])._filter_programs_from_common_rules(self)
        return programs

    def _get_valid_applied_coupon_program(self):
        self.ensure_one()
        # applied_coupon_ids's coupons might be coming from:
        #   * a coupon generated from a previous order that benefited from a promotion_program that rewarded the next sale order.
        #     In that case requirements to benefit from the program (Quantity and price) should not be checked anymore
        #   * a coupon_program, in that case the promo_applicability is always for the current order and everything should be checked (filtered)
        programs = self.applied_coupon_ids.mapped('program_id').filtered(lambda p: p.promo_applicability == 'on_next_order')._filter_programs_from_common_rules(self, True)
        programs += self.applied_coupon_ids.mapped('program_id').filtered(lambda p: p.promo_applicability == 'on_current_order')._filter_programs_from_common_rules(self)
        return programs

    def _create_new_no_code_promo_reward_lines(self):
        '''Apply new programs that are applicable'''
        self.ensure_one()
        order = self
        programs = order._get_applicable_no_code_promo_program()
        programs = programs._keep_only_most_interesting_auto_applied_global_discount_program()
        for program in programs:
            # VFE REF in master _get_applicable_no_code_programs already filters programs
            # why do we need to reapply this bunch of checks in _check_promo_code ????
            # We should only apply a little part of the checks in _check_promo_code...
            error_status = program._check_promo_code(order, False)
            if not error_status.get('error'):
                if program.promo_applicability == 'on_next_order':
                    order.state != 'cancel' and order._create_reward_coupon(program)
                elif program.discount_line_product_id.id not in self.order_line.mapped('product_id').ids:
                    self.write({'order_line': [(0, False, value) for value in self._get_reward_line_values(program)]})
                order.no_code_promo_program_ids |= program

    def _update_existing_reward_lines(self):
        '''Update values for already applied rewards'''
        def update_line(order, lines, values):
            '''Update the lines and return them if they should be deleted'''
            lines_to_remove = self.env['sale.order.line']
            # Check commit 6bb42904a03 for next if/else
            # Remove reward line if price or qty equal to 0
            if values['product_uom_qty'] and values['price_unit']:
                lines.write(values)
            else:
                if program.reward_type != 'free_shipping':
                    # Can't remove the lines directly as we might be in a recordset loop
                    lines_to_remove += lines
                else:
                    values.update(price_unit=0.0)
                    lines.write(values)
            return lines_to_remove

        self.ensure_one()
        order = self
        applied_programs = order._get_applied_programs_with_rewards_on_current_order()
        for program in applied_programs.sorted(lambda ap: (ap.discount_type == 'fixed_amount', ap.discount_apply_on == 'on_order')):
            values = order._get_reward_line_values(program)
            lines = order.order_line.filtered(lambda line: line.product_id == program.discount_line_product_id)
            if program.reward_type == 'discount':
                lines_to_remove = lines
                lines_to_add = []
                lines_to_keep = []
                # Values is what discount lines should really be, lines is what we got in the SO at the moment
                # 1. If values & lines match, we should update the line (or delete it if no qty or price?)
                #    As removing a lines remove all the other lines linked to the same program, we need to save them
                #    using lines_to_keep
                # 2. If the value is not in the lines, we should add it
                # 3. if the lines contains a tax not in value, we should remove it
                for value in values:
                    value_found = False
                    for line in lines:
                        # Case 1.
                        if not len(set(line.tax_id.mapped('id')).symmetric_difference(set([v[1] for v in value['tax_id']]))):
                            value_found = True
                            # Working on Case 3.
                            # update_line update the line to the correct value and returns them if they should be unlinked
                            update_to_remove = update_line(order, line, value)
                            if not update_to_remove:
                                lines_to_keep += [(0, False, value)]
                                lines_to_remove -= line
                    # Working on Case 2.
                    if not value_found:
                        lines_to_add += [(0, False, value)]
                # Case 3.
                line_update = []
                if lines_to_remove:
                    line_update += [(3, line_id, 0) for line_id in lines_to_remove.ids]
                    line_update += lines_to_keep
                line_update += lines_to_add
                order.write({'order_line': line_update})
            else:
                update_line(order, lines, values[0]).unlink()

    def _remove_invalid_reward_lines(self):
        """ Find programs & coupons that are not applicable anymore.
            It will then unlink the related reward order lines.
            It will also unset the order's fields that are storing
            the applied coupons & programs.
            Note: It will also remove a reward line coming from an archive program.
        """
        self.ensure_one()
        order = self

        applied_programs = order._get_applied_programs()
        applicable_programs = self.env['coupon.program']
        if applied_programs:
            applicable_programs = order._get_applicable_programs() + order._get_valid_applied_coupon_program()
            applicable_programs = applicable_programs._keep_only_most_interesting_auto_applied_global_discount_program()
        programs_to_remove = applied_programs - applicable_programs

        reward_product_ids = applied_programs.discount_line_product_id.ids
        # delete reward line coming from an archived coupon (it will never be updated/removed when recomputing the order)
        invalid_lines = order.order_line.filtered(lambda line: line.is_reward_line and line.product_id.id not in reward_product_ids)

        if programs_to_remove:
            product_ids_to_remove = programs_to_remove.discount_line_product_id.ids

            if product_ids_to_remove:
                # Invalid generated coupon for which we are not eligible anymore ('expired' since it is specific to this SO and we may again met the requirements)
                self.generated_coupon_ids.filtered(lambda coupon: coupon.program_id.discount_line_product_id.id in product_ids_to_remove).write({'state': 'expired'})

            # Reset applied coupons for which we are not eligible anymore ('valid' so it can be use on another )
            coupons_to_remove = order.applied_coupon_ids.filtered(lambda coupon: coupon.program_id in programs_to_remove)
            coupons_to_remove.write({'state': 'new'})

            # Unbind promotion and coupon programs which requirements are not met anymore
            order.no_code_promo_program_ids -= programs_to_remove
            order.code_promo_program_id -= programs_to_remove

            if coupons_to_remove:
                order.applied_coupon_ids -= coupons_to_remove

            # Remove their reward lines
            if product_ids_to_remove:
                invalid_lines |= order.order_line.filtered(lambda line: line.product_id.id in product_ids_to_remove)

        invalid_lines.unlink()

    def _get_applied_programs_with_rewards_on_current_order(self):
        # Need to add filter on current order. Indeed, it has always been calculating reward line even if on next order (which is useless and do calculation for nothing)
        # This problem could not be noticed since it would only update or delete existing lines related to that program, it would not find the line to update since not in the order
        # But now if we dont find the reward line in the order, we add it (since we can now have multiple line per  program in case of discount on different vat), thus the bug
        # mentionned ahead will be seen now
        return self.no_code_promo_program_ids.filtered(lambda p: p.promo_applicability == 'on_current_order') + \
               self.applied_coupon_ids.mapped('program_id') + \
               self.code_promo_program_id.filtered(lambda p: p.promo_applicability == 'on_current_order')

    def _get_applied_programs_with_rewards_on_next_order(self):
        return self.no_code_promo_program_ids.filtered(lambda p: p.promo_applicability == 'on_next_order') + \
            self.code_promo_program_id.filtered(lambda p: p.promo_applicability == 'on_next_order')

    def _get_applied_programs(self):
        """Returns all applied programs on current order:

        Expected to return same result than:

            self._get_applied_programs_with_rewards_on_current_order()
            +
            self._get_applied_programs_with_rewards_on_next_order()
        """
        return self.code_promo_program_id + self.no_code_promo_program_ids + self.applied_coupon_ids.mapped('program_id')

    def _get_invoice_status(self):
        # Handling of a specific situation: an order contains
        # a product invoiced on delivery and a promo line invoiced
        # on order. We would avoid having the invoice status 'to_invoice'
        # if the created invoice will only contain the promotion line
        super()._get_invoice_status()
        for order in self.filtered(lambda order: order.invoice_status == 'to invoice'):
            paid_lines = order._get_paid_order_lines()
            if not any(line.invoice_status == 'to invoice' for line in paid_lines):
                order.invoice_status = 'no'

    def _get_invoiceable_lines(self, final=False):
        """ Ensures we cannot invoice only reward lines.

        Since promotion lines are specified with service products,
        those lines are directly invoiceable when the order is confirmed
        which can result in invoices containing only promotion lines.

        To avoid those cases, we allow the invoicing of promotion lines
        iff at least another 'basic' lines is also invoiceable.
        """
        invoiceable_lines = super()._get_invoiceable_lines(final)
        reward_lines = self._get_reward_lines()
        if invoiceable_lines <= reward_lines:
            return self.env['sale.order.line'].browse()
        return invoiceable_lines

    def update_prices(self):
        """Recompute coupons/promotions after pricelist prices reset."""
        super().update_prices()
        if any(line.is_reward_line for line in self.order_line):
            self.recompute_coupon_lines()


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    is_reward_line = fields.Boolean('Is a program reward line')

    def _is_not_sellable_line(self):
        return self.is_reward_line or super()._is_not_sellable_line()

    def unlink(self):
        related_program_lines = self.env['sale.order.line']
        # Reactivate coupons related to unlinked reward line
        for line in self.filtered(lambda line: line.is_reward_line):
            coupons_to_reactivate = line.order_id.applied_coupon_ids.filtered(
                lambda coupon: coupon.program_id.discount_line_product_id == line.product_id
            )
            coupons_to_reactivate.write({'state': 'new'})
            line.order_id.applied_coupon_ids -= coupons_to_reactivate
            # Remove the program from the order if the deleted line is the reward line of the program
            # And delete the other lines from this program (It's the case when discount is split per different taxes)
            related_program = self.env['coupon.program'].search([('discount_line_product_id', '=', line.product_id.id)])
            if related_program:
                line.order_id.no_code_promo_program_ids -= related_program
                line.order_id.code_promo_program_id -= related_program
                related_program_lines |= line.order_id.order_line.filtered(lambda l: l.product_id.id == related_program.discount_line_product_id.id) - line
        return super(SaleOrderLine, self | related_program_lines).unlink()

    def _compute_tax_id(self):
        reward_lines = self.filtered('is_reward_line')
        super(SaleOrderLine, self - reward_lines)._compute_tax_id()
        # Discount reward line is split per tax, the discount is set on the line but not on the product
        # as the product is the generic discount line.
        # In case of a free product, retrieving the tax on the line instead of the product won't affect the behavior.
        for line in reward_lines:
            line = line.with_company(line.company_id)
            fpos = line.order_id.fiscal_position_id or line.order_id.fiscal_position_id.get_fiscal_position(line.order_partner_id.id)
            # If company_id is set, always filter taxes by the company
            taxes = line.tax_id.filtered(lambda r: not line.company_id or r.company_id == line.company_id)
            line.tax_id = fpos.map_tax(taxes)

    def _get_display_price(self, product):
        # A product created from a promotion does not have a list_price.
        # The price_unit of a reward order line is computed by the promotion, so it can be used directly
        if self.is_reward_line:
            return self.price_unit
        return super()._get_display_price(product)

    # Invalidation of `coupon.program.order_count`
    # `test_program_rules_validity_dates_and_uses`,
    # Overriding modified is quite hardcore as you need to know how works the cache and the invalidation system,
    # but at least the below works and should be efficient.
    # Another possibility is to add on product.product a one2many to sale.order.line 'order_line_ids',
    # and then add the depends @api.depends('discount_line_product_id.order_line_ids'),
    # but I am not sure this will as efficient as the below.
    def modified(self, fnames, *args, **kwargs):
        super(SaleOrderLine, self).modified(fnames, *args, **kwargs)
        if 'product_id' in fnames:
            Program = self.env['coupon.program'].sudo()
            field_order_count = Program._fields['order_count']
            field_total_order_count = Program._fields['total_order_count']
            programs = self.env.cache.get_records(Program, field_order_count)
            programs |= self.env.cache.get_records(Program, field_total_order_count)
            if programs:
                products = self.filtered('is_reward_line').mapped('product_id')
                for program in programs:
                    if program.discount_line_product_id in products:
                        self.env.cache.invalidate([(field_order_count, program.ids), (field_total_order_count, program.ids)])

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict, OrderedDict
from odoo import api, models, _
from odoo.tools import float_compare
import base64

class PosOrder(models.Model):
    _inherit = 'pos.order'

    # This whole file is temporary and will be fixed in the future.

    def _process_saved_order(self, draft, order_data=None):
        self.ensure_one()
        res = super()._process_saved_order(draft, order_data)

        loyalty_coupons_data = order_data.get('loyalty_coupons_data') if order_data else None
        is_loyalty_coupons_data_provided = loyalty_coupons_data is not None

        if self.state in ('paid', 'done', 'invoiced'):
            if is_loyalty_coupons_data_provided:
                self._delete_coupons_data()
                if loyalty_coupons_data:
                    res.update(self._confirm_coupon_programs(loyalty_coupons_data))
            else:
                res.update(self._apply_saved_coupons_data())
        elif is_loyalty_coupons_data_provided:
            self._save_coupons_data(loyalty_coupons_data)

        return res

    def _save_coupons_data(self, coupons_data):
        self.ensure_one()
        self._delete_coupons_data()

        # Keys are stringified when using rpc
        coupons_data = {int(coupon_temp_id): coupon_data for coupon_temp_id, coupon_data in coupons_data.items()}
        self._check_existing_loyalty_cards(coupons_data)

        # Check that the provided positive loyalty.card ids are valid, otherwise ignore them
        existing_coupons_to_add_points_id = [coupon_id for coupon_id, coupon_data in coupons_data.items() if coupon_id > 0 and not coupon_data.get('giftCardId')]
        existing_coupons_read_result = self.env['loyalty.card'].search_read(domain=[('id', 'in', existing_coupons_to_add_points_id)], fields=['id']) if existing_coupons_to_add_points_id else []
        coupons_to_add_points_temp_id_by_real_id = {coupon_read['id']: coupon_read['id'] for coupon_read in existing_coupons_read_result}

        # Create the coupons that were awarded with the order.
        coupons_to_create = OrderedDict({coupon_temp_id: coupon_data for coupon_temp_id, coupon_data in coupons_data.items() if coupon_temp_id < 0 and not coupon_data.get('giftCardId')})

        created_coupons = self.env['loyalty.card'].with_context(action_no_send_mail=True).sudo().create([{
            'program_id': coupon_data['program_id'],
            'partner_id': self._get_partner_id(coupon_data.get('partner_id', False)),
            'code': coupon_data.get('barcode') or self.env['loyalty.card']._generate_code(),
            'points': 0,
            'source_pos_order_id': self.id,
        } for coupon_data in coupons_to_create.values()])

        # We update the gift card that we sold when the gift_card_settings = 'scan_use'.
        gift_cards_to_update = [coupon_data for coupon_data in coupons_data.values() if coupon_data.get('giftCardId')]

        self.env['pos.loyalty.points.change'].sudo().create([{
            'order_id': self.id,
            'coupon_id': coupon_data['giftCardId'],
            'points': coupon_data['points'],
            'add_points': False,
            'is_coupon_created': False,
            'coupon_new_partner_id': self._get_partner_id(coupon_data.get('partner_id', False)),
            'temporary_id': 0, # Unused
        } for coupon_data in gift_cards_to_update])

        # Map the newly created coupons
        # By sorting created_coupons, coupons_to_create and created_coupons should be in the same order.
        for created_coupon_temp_id, created_coupon in zip(coupons_to_create.keys(), created_coupons.sorted(key=lambda r: r.id)):
            coupons_to_add_points_temp_id_by_real_id[created_coupon.id] = created_coupon_temp_id

        self.env['pos.loyalty.points.change'].sudo().create([{
            'order_id': self.id,
            'coupon_id': coupon_id,
            'points': coupons_data[coupon_temp_id]['points'],
            'add_points': True,
            'is_coupon_created': coupon_id in created_coupons.ids,
            'temporary_id': coupon_temp_id,
        } for coupon_id, coupon_temp_id in coupons_to_add_points_temp_id_by_real_id.items()])

        lines_per_reward_code = defaultdict(lambda: self.env['pos.order.line'])
        for line in self.lines:
            if not line.reward_identifier_code:
                continue
            lines_per_reward_code[line.reward_identifier_code] |= line

        for coupon_id, coupon_temp_id in coupons_to_add_points_temp_id_by_real_id.items():
            for reward_code in coupons_data[coupon_temp_id].get('line_codes', []):
                lines_per_reward_code[reward_code].coupon_id = coupon_id

    def _delete_coupons_data(self):
        points_changes_sudo = self.env['pos.loyalty.points.change'].sudo().search([('order_id', 'in', self.ids)])

        self.lines.filtered('coupon_id').coupon_id = False

        if points_changes_sudo:
            created_coupons = points_changes_sudo.filtered('is_coupon_created').coupon_id
            points_changes_sudo.unlink()
            created_coupons.unlink()

    def _apply_saved_coupons_data(self):
        self.ensure_one()
        points_changes_sudo = self.env['pos.loyalty.points.change'].sudo().search([('order_id', '=', self.id)]).with_context(bypass_pos_loyalty_card_modifiable_check=True)

        updated_gift_cards = self.env['loyalty.card']
        if points_changes_sudo:
            for points_change in points_changes_sudo:
                if points_change.add_points:
                    points_change.coupon_id.points += points_change.points
                else:
                    if points_change.coupon_id.program_type == 'gift_card':
                        points_change.coupon_id.write({
                            'points': points_change.points,
                            'source_pos_order_id': self.id,
                            'partner_id': points_change.coupon_new_partner_id.id,
                        })
                        updated_gift_cards |= points_change.coupon_id
                    else: # Currently unused
                        points_change.coupon_id.points = points_change.points

        created_coupons = points_changes_sudo.filtered('is_coupon_created').coupon_id
        # Send creation email
        created_coupons.with_context(action_no_send_mail=False)._send_creation_communication()

        # Reports per program
        report_per_program = {}
        coupon_per_report = defaultdict(list)
        # Important to include the updated gift cards so that it can be printed. Check coupon_report.
        for coupon in created_coupons | updated_gift_cards:
            if coupon.program_id not in report_per_program:
                report_per_program[coupon.program_id] = coupon.program_id.communication_plan_ids.\
                    filtered(lambda c: c.trigger == 'create').pos_report_print_id
            for report in report_per_program[coupon.program_id]:
                coupon_per_report[report.id].append(coupon.id)

        added_points_coupons_by_temp_id = {points_change.temporary_id: points_change.coupon_id for points_change in points_changes_sudo.filtered('add_points')}
        points_changes_sudo.unlink()
        return {
            'coupon_updates': [{
                'old_id': coupon_temp_id,
                'id': coupon.id,
                'points': coupon.points,
                'code': coupon.code,
                'program_id': coupon.program_id.id,
                'partner_id': coupon.partner_id.id,
            } for coupon_temp_id, coupon in added_points_coupons_by_temp_id.items() if coupon.program_id.is_nominative],
            'program_updates': [{
                'program_id': coupon.program_id.id,
                'usages': coupon.program_id.total_order_count,
            } for coupon in added_points_coupons_by_temp_id.values()],
            'new_coupon_info': [{
                'program_name': coupon.program_id.name,
                'expiration_date': coupon.expiration_date,
                'code': coupon.code,
            } for coupon in created_coupons if (
                coupon.program_id.applies_on == 'future'
                # Don't send the coupon code for the gift card and ewallet programs.
                # It should not be printed in the ticket.
                and coupon.program_id.program_type not in ['gift_card', 'ewallet']
            )],
            'coupon_report': coupon_per_report,
        }

    def validate_coupon_programs(self, point_changes, new_codes):
        """
        This is called upon validating the order in the pos.

        This will check the balance for any pre-existing coupon to make sure that the rewards are in fact all claimable.
        This will also check that any set code for coupons do not exist in the database.
        """
        point_changes = {int(k): v for k, v in point_changes.items()}
        coupon_ids_from_pos = set(point_changes.keys())
        coupons = self.env['loyalty.card'].browse(coupon_ids_from_pos).exists().filtered('program_id.active')
        coupon_difference = set(coupons.ids) ^ coupon_ids_from_pos
        if coupon_difference:
            return {
                'successful': False,
                'payload': {
                    'message': _('Some coupons are invalid. The applied coupons have been updated. Please check the order.'),
                    'removed_coupons': list(coupon_difference),
                }
            }
        for coupon in coupons:
            if float_compare(coupon.points, -point_changes[coupon.id], 2) == -1:
                return {
                    'successful': False,
                    'payload': {
                        'message': _('There are not enough points for the coupon: %s.', coupon.code),
                        'updated_points': {c.id: c.points for c in coupons}
                    }
                }
        # Check existing coupons
        coupons = self.env['loyalty.card'].search([('code', 'in', new_codes)])
        if coupons:
            return {
                'successful': False,
                'payload': {
                    'message': _('The following codes already exist in the database, perhaps they were already sold?\n%s',
                        ', '.join(coupons.mapped('code'))),
                }
            }
        return {
            'successful': True,
            'payload': {},
        }

    @api.model
    def _get_partner_id(self, partner_id):
        return partner_id and self.env['res.partner'].browse(partner_id).exists() and partner_id or False

    def _confirm_coupon_programs(self, coupon_data):
        """
        This is called after the order is created.

        This will create all necessary coupons and link them to their line orders etc..

        It will also return the points of all concerned coupons to be updated in the cache.
        """
        get_partner_id = lambda partner_id: partner_id and self.env['res.partner'].browse(partner_id).exists() and partner_id or False
        # Keys are stringified when using rpc
        coupon_data = {int(k): v for k, v in coupon_data.items()}

        self._check_existing_loyalty_cards(coupon_data)
        # Map negative id to newly created ids.
        coupon_new_id_map = {k: k for k in coupon_data.keys() if k > 0}

        # Create the coupons that were awarded by the order.
        coupons_to_create = {k: v for k, v in coupon_data.items() if k < 0 and not v.get('giftCardId')}
        coupon_create_vals = [{
            'program_id': p['program_id'],
            'partner_id': get_partner_id(p.get('partner_id', False)),
            'code': p.get('barcode') or self.env['loyalty.card']._generate_code(),
            'points': 0,
            'source_pos_order_id': self.id,
        } for p in coupons_to_create.values()]

        # Pos users don't have the create permission
        new_coupons = self.env['loyalty.card'].with_context(action_no_send_mail=True).sudo().create(coupon_create_vals)

        # We update the gift card that we sold when the gift_card_settings = 'scan_use'.
        gift_cards_to_update = [v for v in coupon_data.values() if v.get('giftCardId')]
        updated_gift_cards = self.env['loyalty.card']
        for coupon_vals in gift_cards_to_update:
            gift_card = self.env['loyalty.card'].browse(coupon_vals.get('giftCardId'))
            gift_card.write({
                'points': coupon_vals['points'],
                'source_pos_order_id': self.id,
                'partner_id': get_partner_id(coupon_vals.get('partner_id', False)),
            })
            updated_gift_cards |= gift_card

        # Map the newly created coupons
        for old_id, new_id in zip(coupons_to_create.keys(), new_coupons):
            coupon_new_id_map[new_id.id] = old_id

        all_coupons = self.env['loyalty.card'].browse(coupon_new_id_map.keys()).exists()
        lines_per_reward_code = defaultdict(lambda: self.env['pos.order.line'])
        for line in self.lines:
            if not line.reward_identifier_code:
                continue
            lines_per_reward_code[line.reward_identifier_code] |= line
        for coupon in all_coupons:
            if coupon.id in coupon_new_id_map:
                # Coupon existed previously, update amount of points.
                coupon.points += coupon_data[coupon_new_id_map[coupon.id]]['points']
            for reward_code in coupon_data[coupon_new_id_map[coupon.id]].get('line_codes', []):
                lines_per_reward_code[reward_code].coupon_id = coupon
        # Send creation email
        new_coupons.with_context(action_no_send_mail=False)._send_creation_communication()
        # Reports per program
        report_per_program = {}
        coupon_per_report = defaultdict(list)
        # Important to include the updated gift cards so that it can be printed. Check coupon_report.
        for coupon in new_coupons | updated_gift_cards:
            if coupon.program_id not in report_per_program:
                report_per_program[coupon.program_id] = coupon.program_id.communication_plan_ids.\
                    filtered(lambda c: c.trigger == 'create').pos_report_print_id
            for report in report_per_program[coupon.program_id]:
                coupon_per_report[report.id].append(coupon.id)
        return {
            'coupon_updates': [{
                'old_id': coupon_new_id_map[coupon.id],
                'id': coupon.id,
                'points': coupon.points,
                'code': coupon.code,
                'program_id': coupon.program_id.id,
                'partner_id': coupon.partner_id.id,
            } for coupon in all_coupons if coupon.program_id.is_nominative],
            'program_updates': [{
                'program_id': program.id,
                'usages': program.total_order_count,
            } for program in all_coupons.program_id],
            'new_coupon_info': [{
                'program_name': coupon.program_id.name,
                'expiration_date': coupon.expiration_date,
                'code': coupon.code,
            } for coupon in new_coupons if (
                coupon.program_id.applies_on == 'future'
                # Don't send the coupon code for the gift card and ewallet programs.
                # It should not be printed in the ticket.
                and coupon.program_id.program_type not in ['gift_card', 'ewallet']
            )],
            'coupon_report': coupon_per_report,
        }

    def _check_existing_loyalty_cards(self, coupon_data):
        coupon_key_to_modify = []
        for coupon_id, coupon_vals in coupon_data.items():
            partner_id = coupon_vals.get('partner_id', False)
            if partner_id:
                partner_coupons = self.env['loyalty.card'].search(
                    [('partner_id', '=', partner_id), ('program_type', '=', 'loyalty')])
                existing_coupon_for_program = partner_coupons.filtered(lambda c: c.program_id.id == coupon_vals['program_id'])
                if existing_coupon_for_program:
                    coupon_vals['coupon_id'] = existing_coupon_for_program[0].id
                    coupon_key_to_modify.append([coupon_id, existing_coupon_for_program[0].id])
        for old_key, new_key in coupon_key_to_modify:
            coupon_data[new_key] = coupon_data.pop(old_key)

    def _get_fields_for_order_line(self):
        fields = super(PosOrder, self)._get_fields_for_order_line()
        fields.extend(['is_reward_line', 'reward_id', 'coupon_id', 'reward_identifier_code', 'points_cost'])
        return fields

    def _add_mail_attachment(self, name, ticket):
        attachment = super()._add_mail_attachment(name, ticket)
        gift_card_programs = self.config_id._get_program_ids().filtered(lambda p: p.program_type == 'gift_card' and
                                                                                  p.pos_report_print_id)
        if gift_card_programs:
            gift_cards = self.env['loyalty.card'].search([('source_pos_order_id', '=', self.id),
                                                          ('program_id', 'in', gift_card_programs.mapped('id'))])
            if gift_cards:
                for program in gift_card_programs:
                    filtered_gift_cards = gift_cards.filtered(lambda gc: gc.program_id == program)
                    if filtered_gift_cards:
                        action_report = program.pos_report_print_id
                        report = action_report._render_qweb_pdf(action_report.report_name, filtered_gift_cards.mapped('id'))
                        filename = name + '.pdf'
                        gift_card_pdf = self.env['ir.attachment'].create({
                            'name': filename,
                            'type': 'binary',
                            'datas': base64.b64encode(report[0]),
                            'store_fname': filename,
                            'res_model': 'pos.order',
                            'res_id': self.ids[0],
                            'mimetype': 'application/x-pdf'
                        })
                        attachment += [(4, gift_card_pdf.id)]

        return attachment

    def unlink(self):
        self._delete_coupons_data()
        return super().unlink()

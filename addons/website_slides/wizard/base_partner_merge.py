# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import api, models
from odoo.tools.misc import groupby as tools_groupby, partition


class MergePartnerAutomatic(models.TransientModel):
    _inherit = 'base.partner.merge.automatic.wizard'

    def _merge_internal(self, src_partners, dst_partner):
        super()._merge_internal(src_partners, dst_partner)

        self.env['slide.slide.partner'].sudo().search(
            [('partner_id', '=', dst_partner.id)])._recompute_completion(update_karma=False)
        self.env['slide.channel.partner'].sudo().search(
            [('partner_id', '=', dst_partner.id)])._recompute_completion(update_karma=False)

    @api.model
    def _merge_partners_for_unique_m2m(self, src_partners, dst_partner,
                                       res_model, uniq_field_per_partner, order=None, prefer_dst_partner=False):
        """ Merge records of res_model for the given partners following the given preferences.

        ! It is the caller responsibility to check the ACL, this method is executed in sudo.
        Use this method when the model ("join" model that links uniquely partner to another
        model) contains a unique key per partner (foreign key to the other model), to select
        the records to assign to the dst_partner from the record of src_partners and dst_partner.
        Indeed, when there is a unique constraint on partner_id and another field we cannot
        simply assign all record of src_partners to dst_partner without potentially create
        conflicts (unique constraint violation).
        When multiple records with the same unique key per partner among the record of the
        given partners (src_partners and dst_partner) are encountered, this method choose
        the one with the highest preference and assign it to dst_partner. Of course, if there
        is only one, it is just assigned to the dst_partner.

        :param recordset src_partners: source partners
        :param recordset dst_partner: destination partner
        :param str res_model: many-to-many relationship model linking res_partner and another
            model through the other_record_field
        :param str uniq_field_per_partner: field name of the unique "other" record per partner
        :param str order: order by clause to express the preference (ex.: completed DESC, vote DESC)
        :param bool prefer_dst_partner: when a conflict occurs whether to always prefer the record
        with dst_partner if present instead of following the preferences
        """
        Model_sudo = self.env[res_model].sudo()
        records_to_delete = []
        records_per_other_record_field = tools_groupby(
            Model_sudo.search_read(
                [('partner_id', 'in', (src_partners + dst_partner).ids)],
                [uniq_field_per_partner, 'partner_id'],
                order=uniq_field_per_partner + (f', {order}' if order else '')),
            key=lambda r: r[uniq_field_per_partner][0])
        if prefer_dst_partner:
            for __, records in records_per_other_record_field:
                dst_partner_records, others = partition(
                    lambda r: r['partner_id'][0] == dst_partner.id, records)
                if dst_partner_records:
                    records_to_delete += others
                    records_to_delete += dst_partner_records[1:]
                else:
                    records_to_delete += others[1:]
        else:
            for __, records in records_per_other_record_field:
                records_to_delete += records[1:]
        Model_sudo.browse([r['id'] for r in records_to_delete]).unlink()
        Model_sudo.search([('partner_id', 'in', src_partners.ids)]).partner_id = dst_partner

    @api.model
    def _update_foreign_keys(self, src_partners, dst_partner):
        """ Overridden to avoid cascade deletions during the base method's merging procedure. """
        self._merge_partners_for_unique_m2m(
            src_partners, dst_partner,
            'slide.slide.partner', 'slide_id', order='completed DESC, vote DESC, quiz_attempts_count ASC')
        self._merge_partners_for_unique_m2m(
            src_partners, dst_partner, 'slide.channel.partner', 'channel_id', prefer_dst_partner=True)
        super()._update_foreign_keys(src_partners, dst_partner)

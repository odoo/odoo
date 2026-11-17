from odoo import fields, models


class MailingMailing(models.Model):
    _inherit = 'mailing.mailing'

    disable_open_tracking = fields.Boolean("Disable Open Tracking")
    disable_click_tracking = fields.Boolean("Disable Click Tracking")

    blacklisted_country_ids = fields.Many2many('res.country', string="For recipients in")

    def _get_tracking_blocked_res_ids(self, model, res_ids):
        """ Return the subset of res_ids whose recipient is located in one of
        the blacklisted countries (every res_id if no country is set). Use the
        record 'country_id' if any, else the country of its partners. """
        self.ensure_one()
        if not self.blacklisted_country_ids:
            return set(res_ids)
        countries = self.blacklisted_country_ids
        records = self.env[model].sudo().browse(res_ids)
        if 'country_id' in records._fields:
            return set(records.filtered(lambda r: r.country_id in countries).ids)
        partners_by_record = records._mail_get_partners(introspect_fields=True)
        return {
            res_id for res_id, partners in partners_by_record.items()
            if partners.country_id & countries
        }

    def _get_open_tracking_blocked_res_ids(self, model, res_ids):
        if not self.disable_open_tracking:
            return set()
        return self._get_tracking_blocked_res_ids(model, res_ids)

    def _get_click_tracking_blocked_res_ids(self, model, res_ids):
        blocked_res_ids = super()._get_click_tracking_blocked_res_ids(model, res_ids)
        if self.disable_click_tracking:
            blocked_res_ids |= self._get_tracking_blocked_res_ids(model, res_ids)
        return blocked_res_ids

# -*- coding:utf-8 -*-
from odoo import api, fields, models, _


class L10nFrArchiveWizard(models.TransientModel):
    _name = 'l10n_fr.archive'

    def _get_default_date(self):
        return fields.Date.today()

    date = fields.Date(string='Date', help='Date until which the archive will be generated.',
                       default=_get_default_date)

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(L10nFrArchiveWizard, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type == 'form':
            # Inject the right url to redirect the user to the threat of the company's partner.
            partner_id = self.env.user.company_id.partner_id
            url = 'web#id=%d&amp;view_type=form&amp;model=res.partner' % partner_id.id
            res['arch'] = res['arch'].replace('inject_partner_url', url)
        return res

    @api.multi
    def archive(self):
        self.ensure_one()
        company = self.env.user.company_id
        company._l10n_fr_create_archive_attachment(self.date)

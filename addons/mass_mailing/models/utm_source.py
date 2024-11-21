# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models

from odoo.exceptions import UserError


class UtmSource(models.Model):
    _inherit = 'utm.source'

    @api.ondelete(at_uninstall=False)
    def _unlink_except_linked_mailings(self):
        """ Already handled by ondelete='restrict', but let's show a nice error message """
        linked_mailings = self.env['mailing.mailing'].sudo().search([
            ('source_id', 'in', self.ids)
        ])

        if linked_mailings:
            raise UserError(_(
                "You cannot delete these UTM Sources as they are linked to the following mailings in "
                "Mass Mailing:\n%(mailing_names)s",
                mailing_names=', '.join(['"%s"' % subject for subject in linked_mailings.mapped('subject')])))

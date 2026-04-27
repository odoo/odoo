# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields, _

class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_es_reports_iae_group = fields.Char("IAE Group or Heading", size=7, default='A010000', help="""\
        This field corresponds to the activity to which the entry refers in 7 alphanumeric characters.\n
        For example, in the operations of a hardware store, 'A036533' will be entered, which indicates an operation\
        carried out by a business activity of a commercial nature subject to the IAE for 'retail trade in household\
        items, hardware, ornaments.'""")

    def _get_mod_boe_sequence(self, mod_version):
        """ Get or create mod BOE sequence for the current company

        :param str mod_version: any of "347" or "349"
        :return: the sequence record
        """
        self.ensure_one()
        assert mod_version in ("347", "349")
        mod_sequence_code = 'l10n_es.boe.mod_%s' % mod_version
        mod_sequence = self.env['ir.sequence'].search([
            ('company_id', '=', self.id), ('code', '=', mod_sequence_code),
        ])
        if not mod_sequence:
            mod_sequence = self.env["ir.sequence"].create({
                'name': "Mod %s BOE sequence for company %s" % (mod_version, self.name),
                'code': mod_sequence_code,
                'padding': 10,
                'company_id': self.id,
            })
        return mod_sequence[0]

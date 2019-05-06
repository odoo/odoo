# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.tools import pycompat
from odoo.exceptions import ValidationError


class ResPartnerBank(models.Model):

    _inherit = 'res.partner.bank'

    @api.constrains('acc_number')
    def check_cbu(self):
        for rec in self.filtered(lambda x: x.acc_type == 'cbu'):
            if rec.acc_number and not rec.is_valid_cbu():
                raise ValidationError(
                    _('The CBU "%s" is not valid') % rec.acc_number)

    @api.model
    def _get_supported_account_types(self):
        """ Add new account type named cbu used in Argentina
        """
        res = super(ResPartnerBank, self)._get_supported_account_types()
        res.append(('cbu', _('CBU')))
        return res

    @api.multi
    def is_valid_cbu(self):
        """ Ensure that the given CBU number is a valid number
        """
        # TODO change pycompat.izip() to zip() when we get to version 13.0
        # taking into account what was commented here
        # https://github.com/odoo/odoo/pull/16811
        self.ensure_one()
        cbu = self.acc_number
        if type(cbu) == int:
            cbu = "%022d" % cbu
        cbu = cbu.strip()
        if len(cbu) != 22:
            return False
        s1 = sum(int(a) * b for a, b in pycompat.izip(
            cbu[0:7], (7, 1, 3, 9, 7, 1, 3)))
        d1 = (10 - s1) % 10
        if d1 != int(cbu[7]):
            return False
        s2 = sum(int(a) * b
                 for a, b in pycompat.izip(cbu[8:-1],
                                 (3, 9, 7, 1, 3, 9, 7, 1, 3, 9, 7, 1, 3)))
        d2 = (10 - s2) % 10
        if d2 != int(cbu[-1]):
            return False
        return True

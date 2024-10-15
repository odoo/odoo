# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.addons import account, uom


class UomUom(uom.UomUom, account.UomUom):

    l10n_cl_sii_code = fields.Char('SII Code')

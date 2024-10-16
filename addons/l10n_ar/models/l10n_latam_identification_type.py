# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields
from odoo.addons import l10n_latam_base


class L10n_LatamIdentificationType(l10n_latam_base.L10n_LatamIdentificationType):


    l10n_ar_afip_code = fields.Char("AFIP Code")

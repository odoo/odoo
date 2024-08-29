# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import l10n_latam_base
from odoo import models, fields


class L10nLatamIdentificationType(models.Model, l10n_latam_base.L10nLatamIdentificationType):
    _name = "l10n_latam.identification.type"


    l10n_co_document_code = fields.Char("Document Code")

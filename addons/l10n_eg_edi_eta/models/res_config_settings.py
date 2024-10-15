from odoo import models, fields
from odoo.addons import account


class ResConfigSettings(account.ResConfigSettings):

    l10n_eg_client_identifier = fields.Char(related='company_id.l10n_eg_client_identifier', readonly=False)
    l10n_eg_client_secret = fields.Char(related='company_id.l10n_eg_client_secret', readonly=False)
    l10n_eg_production_env = fields.Boolean(related='company_id.l10n_eg_production_env', readonly=False)
    l10n_eg_invoicing_threshold = fields.Float(related='company_id.l10n_eg_invoicing_threshold', readonly=False)

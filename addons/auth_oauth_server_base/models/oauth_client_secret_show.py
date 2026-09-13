from odoo import api, fields, models
from odoo.tools import SQL


class OauthClientSecretShow(models.Model):
    _name = 'oauth.client.secret.show'
    _description = 'OAuth Client Secret, shown once right after being generated'
    _auto = False
    _table_sql = SQL('(0)')

    client_secret = fields.Char(readonly=True)

    @api.model
    def _show(self, client_secret: str):
        return {
            'type': 'ir.actions.act_window',
            'name': "OAuth Client Secret",
            'res_model': self._name,
            'views': [(False, 'form')],
            'target': 'new',
            'context': {'default_client_secret': client_secret},
        }

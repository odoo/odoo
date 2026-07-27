from odoo import api, fields, models


class OauthTokenShow(models.AbstractModel):
    _name = 'oauth.token.show'
    _description = 'OAuth client credentials, shown once right after being generated'

    client_id = fields.Char(readonly=True)
    client_secret = fields.Char(readonly=True)

    @api.model
    def _show(self, client_id: str, client_secret: str):
        return {
            'type': 'ir.actions.act_window',
            'name': "OAuth Client Credentials",
            'res_model': self._name,
            'views': [(False, 'form')],
            'target': 'new',
            'context': {'default_client_id': client_id, 'default_client_secret': client_secret},
        }

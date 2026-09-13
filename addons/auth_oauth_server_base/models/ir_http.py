from werkzeug.datastructures import WWWAuthenticate
from werkzeug.exceptions import Unauthorized

from odoo import models
from odoo.addons.auth_oauth_server_base.utils.oauth_utils import protected_resource_metadata_url
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _auth_method_bearer(cls, routing):
        """Routes requiring an access token obtained through oauth are declared with `oauth_resource='<resource name>'`,
        so that a caller without a valid credential is pointed to the OAuth flow instead of just being rejected."""
        try:
            super()._auth_method_bearer(routing)
        except Unauthorized as error:
            resource_name = routing.get('oauth_resource')
            if not resource_name:
                raise

            params = {'resource_metadata': protected_resource_metadata_url(request.env, resource_name)}
            if request.httprequest.headers.get('Authorization', '').lower().startswith('bearer '):
                params['error'] = 'invalid_token'

            raise Unauthorized(www_authenticate=WWWAuthenticate('Bearer', params)) from error

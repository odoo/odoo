# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.fields import Domain
from odoo.http import Controller, request
from odoo.exceptions import ValidationError


class DomainController(Controller):

    @http.route('/web/domain/validate', type='jsonrpc', auth="user")
    def validate(self, model, domain):
        """ Parse `domain` and verify that it can be used to search on `model`
        :return: True when the domain is valid, otherwise False
        :raises ValidationError: if `model` is invalid
        """
        Model = request.env.get(model)
        if Model is None:
            raise ValidationError(_('Invalid model: %s', model))
        try:
            Domain(domain).validate(Model.sudo())
            return True
        except ValueError:  # noqa: BLE001
            return False

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.http import Controller, request
from odoo.exceptions import ValidationError
from odoo.tools.misc import mute_logger

class Domain(Controller):

    @http.route('/web/domain/validate', type='json', auth="user")
    def validate(self, model, domain):
        """ Parse `domain` and verify that it can be used to search on `model`
        :return: True when the domain is valid, otherwise False
        :raises ValidationError: if `model` is invalid
        """
        Model = request.env.get(model)
        if Model is None:
            raise ValidationError(_('Invalid model: %s', model))
        try:
            # go through the motions of preparing the final SQL for the domain,
            # so that anything invalid will raise an exception.
            query = Model.sudo()._search(domain)
            sql, params = query.select()

            # Execute the search in EXPLAIN mode, to have the query parser
            # verify it. EXPLAIN will make sure the query is never actually executed
            # An alternative to EXPLAIN would be a LIMIT 0 clause, but the semantics
            # of a falsy `limit` parameter when calling _search() do not permit it.
            with mute_logger('odoo.sql_db'):
                request.env.cr.execute(f"EXPLAIN {sql}", params)
            return True
        except Exception:  # pylint: disable=broad-except
            return False

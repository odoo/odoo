# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, _
from odoo.exceptions import UserError
from odoo.osv import expression

logger = logging.getLogger(__name__)


class AccountAvataxUniqueCode(models.AbstractModel):
    """Enables unique Avatax references. These are based on the database ID because
    they cannot change. They're made searchable so customers can easily cross-reference
    between Odoo and Avalara.
    """
    _name = 'account.avatax.unique.code'
    _description = 'Mixin to generate unique ids for Avatax'

    avatax_unique_code = fields.Char(
        "Avalara Code",
        compute="_compute_avatax_unique_code",
        search="_search_avatax_unique_code",
        store=False,
        help="Use this code to cross-reference in the Avalara portal."
    )

    def _get_avatax_description(self):
        """This is used to describe records in Avatax.

        E.g. 'Customer 10' with this function returning 'Customer'.

        :return (string): a name for this model
        """
        raise NotImplementedError()

    def _compute_avatax_unique_code(self):
        for record in self:
            record.avatax_unique_code = '%s %s' % (record._get_avatax_description(), record.id)

    def _search_avatax_unique_code(self, operator, value):
        unsupported_operators = ('in', 'not in', '<', '<=', '>', '>=')
        if operator in unsupported_operators or not isinstance(value, str):
            raise UserError(_("Search operation not supported"))

        value = value.lower()

        # allow searching with or without prefix
        prefix = self._get_avatax_description().lower() + " "
        if value.startswith(prefix):
            value = value[len(prefix):]

        # these require that the value is a digit, if it's not then match nothing
        if operator in ('=', '!=') and not value.isdigit():
            return expression.FALSE_DOMAIN

        # to avoid matching every record on like
        if not value:
            return expression.FALSE_DOMAIN

        return [('id', operator, value)]

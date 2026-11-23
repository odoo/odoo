# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class AliasMixin(models.AbstractModel):
    """ A mixin for models that inherits mail.alias to have a one-to-one relation
    between the model and its alias. """
    _name = 'mail.alias.mixin'
    _inherit = 'mail.alias.mixin.optional'
    _inherits = {'mail.alias': 'alias_id'}
    _description = 'Email Aliases Mixin'

    alias_id = fields.Many2one(required=True)
    alias_name = fields.Char(inherited=True)
    alias_defaults = fields.Text(inherited=True)

    # --------------------------------------------------
    # CRUD
    # --------------------------------------------------

    def _require_new_alias(self, record_vals):
        """ alias_id field is always required, due to inherits """
        return not record_vals.get('alias_id')

    def _init_column(self, name):
        """ Create aliases for existing rows. """
        super()._init_column(name)
        if name == 'alias_id':
            # as 'mail.alias' records refer to 'ir.model' records, create
            # aliases after the reflection of models
            self.pool.post_init(self._init_column_alias_id)

    def _init_column_alias_id(self):
        # both self and the alias model must be present in 'ir.model'
        child_ctx = {
            'active_test': False,       # retrieve all records
            'prefetch_fields': False,   # do not prefetch fields on records
        }
        child_model = self.sudo().with_context(child_ctx)

        for record in child_model.search([('alias_id', '=', False)]):
            # create the alias, and link it to the current record
            alias = self.env['mail.alias'].sudo().create(record._alias_get_creation_values())
            record.with_context(mail_notrack=True).alias_id = alias
            _logger.info('Mail alias created for %s %s (id %s)',
                         record._name, record.display_name, record.id)

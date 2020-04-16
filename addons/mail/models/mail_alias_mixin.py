# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class AliasMixin(models.AbstractModel):
    """ A mixin for models that inherits mail.alias. This mixin initializes the
        alias_id column in database, and manages the expected one-to-one
        relation between your model and mail aliases.
    """
    _name = 'mail.alias.mixin'
    _inherits = {'mail.alias': 'alias_id'}
    _description = 'Email Aliases Mixin'

    alias_id = fields.Many2one('mail.alias', string='Alias', ondelete="restrict", required=True)

    # --------------------------------------------------
    # CRUD
    # --------------------------------------------------

    @api.model
    def create(self, vals):
        """ Create a record with ``vals``, and create a corresponding alias. """
        new_alias = not 'alias_id' in vals
        if new_alias:
            alias_vals, record_vals = self._alias_filter_fields(vals)
            alias_vals.update(self._alias_get_creation_values())
            alias = self.env['mail.alias'].create(alias_vals)
            record_vals['alias_id'] = alias.id

        record = super(AliasMixin, self).create(record_vals)
        alias.sudo().write(record._alias_get_creation_values())

        return record

    def unlink(self):
        """ Delete the given records, and cascade-delete their corresponding alias. """
        aliases = self.mapped('alias_id')
        res = super(AliasMixin, self).unlink()
        aliases.unlink()
        return res

    def _init_column(self, name):
        """ Create aliases for existing rows. """
        super(AliasMixin, self)._init_column(name)
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

    # --------------------------------------------------
    # MIXIN TOOL OVERRIDE METHODS
    # --------------------------------------------------

    def _alias_get_creation_values(self):
        """ Return values to create an alias, or to write on the alias after its
            creation.
        """
        return {
            'alias_parent_thread_id': self.id if self.id else False,
            'alias_parent_model_id': self.env['ir.model']._get(self._name).id,
        }

    def _alias_filter_fields(self, values, filters=False):
        """ Split the vals dict into two dictionnary of vals, one for alias
        field and the other for other fields """
        if not filters:
            filters = self.env['mail.alias']._fields.keys()
        alias_values, record_values = {}, {}
        for fname in values.keys():
            if fname in filters:
                alias_values[fname] = values.get(fname)
            else:
                record_values[fname] = values.get(fname)
        return alias_values, record_values

    # --------------------------------------------------
    # GATEWAY
    # --------------------------------------------------

    def _alias_check_contact(self, message, message_dict, alias):
        """ Main mixin method that inheriting models may inherit in order
        to implement a specifc behavior. """
        return self._alias_check_contact_on_record(self, message, message_dict, alias)

    def _alias_check_contact_on_record(self, record, message, message_dict, alias):
        """ Generic method that takes a record not necessarily inheriting from
        mail.alias.mixin. """
        author = self.env['res.partner'].browse(message_dict.get('author_id', False))
        if alias.alias_contact == 'followers':
            if not record.ids:
                return _('incorrectly configured alias (unknown reference record)')
            if not hasattr(record, "message_partner_ids") or not hasattr(record, "message_channel_ids"):
                return _('incorrectly configured alias')
            accepted_partner_ids = record.message_partner_ids | record.message_channel_ids.mapped('channel_partner_ids')
            if not author or author not in accepted_partner_ids:
                return _('restricted to followers')
        elif alias.alias_contact == 'partners' and not author:
            return _('restricted to known authors')
        return True

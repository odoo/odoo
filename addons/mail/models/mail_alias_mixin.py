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
    ALIAS_WRITEABLE_FIELDS = ['alias_name', 'alias_contact', 'alias_defaults']

    alias_id = fields.Many2one('mail.alias', string='Alias', ondelete="restrict", required=True)

    # --------------------------------------------------
    # CRUD
    # --------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        """ Create a record with each ``vals`` or ``vals_list`` and create a corresponding alias. """
        valid_vals_list = []
        for vals in vals_list:
            new_alias = not vals.get('alias_id')
            if new_alias:
                alias_vals, record_vals = self._alias_filter_fields(vals)
                alias_vals.update(self._alias_get_creation_values())
                alias = self.env['mail.alias'].sudo().create(alias_vals)
                record_vals['alias_id'] = alias.id
                valid_vals_list.append(record_vals)
            else:
                valid_vals_list.append(vals)

        records = super(AliasMixin, self).create(valid_vals_list)

        for record in records:
            record.alias_id.sudo().write(record._alias_get_creation_values())

        return records

    def write(self, vals):
        """ Split writable fields of mail.alias and other fields alias fields will
        write with sudo and the other normally """
        alias_vals, record_vals = self._alias_filter_fields(vals, filters=self.ALIAS_WRITEABLE_FIELDS)
        if record_vals:
            super(AliasMixin, self).write(record_vals)
        if alias_vals and (record_vals or self.check_access_rights('write', raise_exception=False)):
            self.mapped('alias_id').sudo().write(alias_vals)

        return True

    def unlink(self):
        """ Delete the given records, and cascade-delete their corresponding alias. """
        aliases = self.mapped('alias_id')
        res = super(AliasMixin, self).unlink()
        aliases.sudo().unlink()
        return res

    @api.returns(None, lambda value: value[0])
    def copy_data(self, default=None):
        data = super(AliasMixin, self).copy_data(default)[0]
        for fields_not_writable in set(self.env['mail.alias']._fields.keys()) - set(self.ALIAS_WRITEABLE_FIELDS):
            if fields_not_writable in data:
                del data[fields_not_writable]
        return [data]

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

    def _alias_check_contact_on_record(self, record, message, message_dict, alias):
        """ Move to ``BaseModel._alias_get_error_message() """
        return record._alias_get_error_message(message, message_dict, alias)

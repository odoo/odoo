# -*- coding: utf-8 -*-
"""This model is used to detect, which all options want to hide from the
    specified group and model"""
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#

from collections import defaultdict
from operator import attrgetter
from odoo import api, _
from odoo.exceptions import UserError
from odoo.models import BaseModel, _unlink, LOG_ACCESS_COLUMNS, \
    INSERT_BATCH_SIZE, SQL_DEFAULT
from odoo.tools import OrderedSet, split_every, attrgetter, clean_context


@api.model
def _create(self, data_list):
    """ Create records from the stored field values in ``data_list``. """
    assert data_list
    cr = self.env.cr

    # insert rows in batches of maximum INSERT_BATCH_SIZE
    ids = []  # ids of created records
    other_fields = OrderedSet()  # non-column fields

    for data_sublist in split_every(INSERT_BATCH_SIZE, data_list):
        stored_list = [data['stored'] for data in data_sublist]
        fnames = sorted({name for stored in stored_list for name in stored})

        columns = []
        rows = [[] for _ in stored_list]
        for fname in fnames:
            field = self._fields[fname]
            if field.column_type:
                columns.append(fname)
                for stored, row in zip(stored_list, rows):
                    if fname in stored:
                        colval = field.convert_to_column(stored[fname], self,
                                                         stored)
                        if field.translate is True and colval:
                            if 'en_US' not in colval.adapted:
                                colval.adapted['en_US'] = next(
                                    iter(colval.adapted.values()))
                        row.append(colval)
                    else:
                        row.append(SQL_DEFAULT)
            else:
                other_fields.add(field)

            if field.type == 'properties':
                # force calling fields.create for properties field because
                # we might want to update the parent definition
                other_fields.add(field)

        if not columns:
            # manage the case where we create empty records
            columns = ['id']
            for row in rows:
                row.append(SQL_DEFAULT)

        header = ", ".join(f'"{column}"' for column in columns)
        template = ", ".join("%s" for _ in rows)
        cr.execute(
            f'INSERT INTO "{self._table}" ({header}) VALUES {template} RETURNING "id"',
            [tuple(row) for row in rows],
        )
        ids.extend(id_ for id_, in cr.fetchall())

    # put the new records in cache, and update inverse fields, for many2one
    #
    # cachetoclear is an optimization to avoid modified()'s cost until other_fields are processed
    cachetoclear = []
    records = self.browse(ids)
    inverses_update = defaultdict(list)  # {(field, value): ids}
    common_set_vals = set(
        LOG_ACCESS_COLUMNS + [self.CONCURRENCY_CHECK_FIELD, 'id',
                              'parent_path'])
    for data, record in zip(data_list, records):
        data['record'] = record
        # DLE P104: test_inherit.py, test_50_search_one2many
        vals = dict(
            {k: v for d in data['inherited'].values() for k, v in d.items()},
            **data['stored'])
        set_vals = common_set_vals.union(vals)
        for field in self._fields.values():
            if field.type in ('one2many', 'many2many'):
                self.env.cache.set(record, field, ())
            elif field.related and not field.column_type:
                self.env.cache.set(record, field,
                                   field.convert_to_cache(None, record))
            # DLE P123: `test_adv_activity`, `test_message_assignation_inbox`, `test_message_log`, `test_create_mail_simple`, ...
            # Set `mail.message.parent_id` to False in cache so it doesn't do the useless SELECT when computing the modified of `child_ids`
            # in other words, if `parent_id` is not set, no other message `child_ids` are impacted.
            # + avoid the fetch of fields which are False. e.g. if a boolean field is not passed in vals and as no default set in the field attributes,
            # then we know it can be set to False in the cache in the case of a create.
            elif field.name not in set_vals and not field.compute:
                self.env.cache.set(record, field,
                                   field.convert_to_cache(None, record))
        for fname, value in vals.items():
            field = self._fields[fname]
            if field.type in ('one2many', 'many2many'):
                cachetoclear.append((record, field))
            else:
                cache_value = field.convert_to_cache(value, record)
                self.env.cache.set(record, field, cache_value)
                if field.type in ('many2one', 'many2one_reference') and \
                        self.pool.field_inverses[field]:
                    inverses_update[(field, cache_value)].append(record.id)

    for (field, value), record_ids in inverses_update.items():
        field._update_inverses(self.browse(record_ids), value)

    # update parent_path
    records._parent_store_create()

    # protect fields being written against recomputation
    protected = [(data['protected'], data['record']) for data in data_list]
    with self.env.protecting(protected):
        # mark computed fields as todo
        records.modified(self._fields, create=True)

        if other_fields:
            # discard default values from context for other fields
            others = records.with_context(clean_context(self._context))
            for field in sorted(other_fields, key=attrgetter('_sequence')):
                field.create([
                    (other, data['stored'][field.name])
                    for other, data in zip(others, data_list)
                    if field.name in data['stored']
                ])

            # mark fields to recompute
            records.modified([field.name for field in other_fields],
                             create=True)

        # if value in cache has not been updated by other_fields, remove it
        for record, field in cachetoclear:
            if self.env.cache.contains(record,
                                       field) and not self.env.cache.get(
                record, field):
                self.env.cache.remove(record, field)

    # check Python constraints for stored fields
    records._validate_fields(
        name for data in data_list for name in data['stored'])
    records.check_access_rule('create')
    # This is used to restrict the access right to create a record
    current_model_id = self.env['ir.model'].sudo().search(
        [('model', '=', self._name)]).id
    access_right_rec = self.env['access.right'].sudo().search_read(
        [('model_id', '=', current_model_id)],
        ['model_id', 'is_create_or_update',
         'groups_id'])
    if access_right_rec and not self.env.is_admin():
        for rec in access_right_rec:
            group_name = self.env['ir.model.data'].sudo().search([
                ('model', '=', 'res.groups'),
                ('res_id', '=', rec['groups_id'][0])
            ]).name
            module_name = self.env['ir.model.data'].sudo().search([
                ('model', '=', 'res.groups'),
                ('res_id', '=', rec['groups_id'][0])
            ]).module
            group = module_name + "." + group_name
            if self.env.user.has_group(group):
                if rec['is_create_or_update']:
                    raise UserError('You are restricted from performing this'
                                      ' operation. Please contact the'
                                      ' administrator.')
    return records


@api.model
def unlink(self):
    """ unlink()

    Deletes the records in ``self``.

    :raise AccessError: if the user is not allowed to delete all the given records
    :raise UserError: if the record is default property for other records
    """
    if not self:
        return True

    self.check_access_rights('unlink')
    self.check_access_rule('unlink')

    from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG
    for func in self._ondelete_methods:
        # func._ondelete is True if it should be called during uninstallation
        if func._ondelete or not self._context.get(MODULE_UNINSTALL_FLAG):
            func(self)

    # TOFIX: this avoids an infinite loop when trying to recompute a
    # field, which triggers the recomputation of another field using the
    # same compute function, which then triggers again the computation
    # of those two fields
    for field in self._fields.values():
        self.env.remove_to_compute(field, self)

    self.env.flush_all()

    cr = self._cr
    Data = self.env['ir.model.data'].sudo().with_context({})
    Defaults = self.env['ir.default'].sudo()
    Property = self.env['ir.property'].sudo()
    Attachment = self.env['ir.attachment'].sudo()
    ir_property_unlink = Property
    ir_model_data_unlink = Data
    ir_attachment_unlink = Attachment

    # mark fields that depend on 'self' to recompute them after 'self' has
    # been deleted (like updating a sum of lines after deleting one line)
    with self.env.protecting(self._fields.values(), self):
        self.modified(self._fields, before=True)
    for sub_ids in cr.split_for_in_conditions(self.ids):
        records = self.browse(sub_ids)

        # Check if the records are used as default properties.
        refs = [f'{self._name},{id_}' for id_ in sub_ids]
        if Property.search(
                [('res_id', '=', False), ('value_reference', 'in', refs)],
                limit=1):
            raise UserError(
                _('Unable to delete this document because it is used as a default property'))

        # Delete the records' properties.
        ir_property_unlink |= Property.search([('res_id', 'in', refs)])

        query = f'DELETE FROM "{self._table}" WHERE id IN %s'
        cr.execute(query, (sub_ids,))

        # Removing the ir_model_data reference if the record being deleted
        # is a record created by xml/csv file, as these are not connected
        # with real database foreign keys, and would be dangling references.
        #
        # Note: the following steps are performed as superuser to avoid
        # access rights restrictions, and with no context to avoid possible
        # side-effects during admin calls.
        data = Data.search(
            [('model', '=', self._name), ('res_id', 'in', sub_ids)])
        ir_model_data_unlink |= data

        # For the same reason, remove the defaults having some of the
        # records as value
        Defaults.discard_records(records)

        # For the same reason, remove the relevant records in ir_attachment
        # (the search is performed with sql as the search method of
        # ir_attachment is overridden to hide attachments of deleted
        # records)
        query = 'SELECT id FROM ir_attachment WHERE res_model=%s AND res_id IN %s'
        cr.execute(query, (self._name, sub_ids))
        ir_attachment_unlink |= Attachment.browse(
            row[0] for row in cr.fetchall())

    # invalidate the *whole* cache, since the orm does not handle all
    # changes made in the database, like cascading delete!
    self.env.invalidate_all(flush=False)
    if ir_property_unlink:
        ir_property_unlink.unlink()
    if ir_model_data_unlink:
        ir_model_data_unlink.unlink()
    if ir_attachment_unlink:
        ir_attachment_unlink.unlink()
    # DLE P93: flush after the unlink, for recompute fields depending on
    # the modified of the unlink
    self.env.flush_all()
    # auditing: deletions are infrequent and leave no trace in the database
    _unlink.info('User #%s deleted %s records with IDs: %r', self._uid,
                 self._name, self.ids)
    # This is used to restrict the access right to unlink a record
    current_model_id = self.env['ir.model'].sudo().search(
        [('model', '=', self._name)]).id
    access_right_rec = self.env['access.right'].sudo().search_read(
        [('model_id', '=', current_model_id)], ['model_id', 'is_delete',
                                                'groups_id'])
    if access_right_rec and not self.env.is_admin():
        for rec in access_right_rec:
            group_name = self.env['ir.model.data'].sudo().search([
                ('model', '=', 'res.groups'),
                ('res_id', '=', rec['groups_id'][0])
            ]).name
            module_name = self.env['ir.model.data'].sudo().search([
                ('model', '=', 'res.groups'),
                ('res_id', '=', rec['groups_id'][0])
            ]).module
            group = module_name + "." + group_name
            if self.env.user.has_group(group):
                if rec['is_delete']:
                    raise UserError(_('You are restricted from performing this'
                                      ' operation. Please contact the'
                                      ' administrator.'))
    return True


BaseModel._create = _create
BaseModel.unlink = unlink

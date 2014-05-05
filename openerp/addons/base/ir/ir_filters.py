# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import exceptions
from openerp.osv import osv, fields
from openerp.tools.translate import _

class ir_filters(osv.osv):
    _name = 'ir.filters'
    _description = 'Filters'

    def _list_all_models(self, cr, uid, context=None):
        cr.execute("SELECT model, name FROM ir_model ORDER BY name")
        return cr.fetchall()

    def copy(self, cr, uid, id, default=None, context=None):
        name = self.read(cr, uid, [id], ['name'])[0]['name']
        default.update({'name':_('%s (copy)') % name})
        return super(ir_filters, self).copy(cr, uid, id, default, context)

    def get_filters(self, cr, uid, model):
        """Obtain the list of filters available for the user on the given model.

        :return: list of :meth:`~osv.read`-like dicts containing the
            ``name``, ``is_default``, ``domain``, ``user_id`` (m2o tuple) and
            ``context`` of the matching ``ir.filters``.
        """
        # available filters: private filters (user_id=uid) and public filters (uid=NULL) 
        filter_ids = self.search(cr, uid,
            [('model_id','=',model),('user_id','in',[uid, False])])
        my_filters = self.read(cr, uid, filter_ids,
            ['name', 'is_default', 'domain', 'context', 'user_id'])
        return my_filters

    def _check_global_default(self, cr, uid, vals, matching_filters, context=None):
        """ _check_global_default(cursor, UID, dict, list(dict), dict) -> None

        Checks if there is a global default for the model_id requested.

        If there is, and the default is different than the record being written
        (-> we're not updating the current global default), raise an error
        to avoid users unknowingly overwriting existing global defaults (they
        have to explicitly remove the current default before setting a new one)

        This method should only be called if ``vals`` is trying to set
        ``is_default``

        :raises openerp.exceptions.Warning: if there is an existing default and
                                            we're not updating it
        """
        existing_default = self.search(cr, uid, [
            ('model_id', '=', vals['model_id']),
            ('user_id', '=', False),
            ('is_default', '=', True)], context=context)

        if not existing_default: return
        if matching_filters and \
           (matching_filters[0]['id'] == existing_default[0]):
            return

        raise exceptions.Warning(
            _("There is already a shared filter set as default for %(model)s, delete or change it before setting a new default") % {
                'model': vals['model_id']
            })

    def create_or_replace(self, cr, uid, vals, context=None):
        lower_name = vals['name'].lower()
        matching_filters = [f for f in self.get_filters(cr, uid, vals['model_id'])
                                if f['name'].lower() == lower_name
                                # next line looks for matching user_ids (specific or global), i.e.
                                # f.user_id is False and vals.user_id is False or missing,
                                # or f.user_id.id == vals.user_id
                                if (f['user_id'] and f['user_id'][0]) == vals.get('user_id', False)]

        if vals.get('is_default'):
            if vals.get('user_id'):
                act_ids = self.search(cr, uid, [
                        ('model_id', '=', vals['model_id']),
                        ('user_id', '=', vals['user_id']),
                        ('is_default', '=', True),
                    ], context=context)
                self.write(cr, uid, act_ids, {'is_default': False}, context=context)
            else:
                self._check_global_default(
                    cr, uid, vals, matching_filters, context=None)

        # When a filter exists for the same (name, model, user) triple, we simply
        # replace its definition.
        if matching_filters:
            self.write(cr, uid, matching_filters[0]['id'], vals, context)
            return matching_filters[0]['id']

        return self.create(cr, uid, vals, context)

    _sql_constraints = [
        # Partial constraint, complemented by unique index (see below)
        # Still useful to keep because it provides a proper error message when a violation
        # occurs, as it shares the same prefix as the unique index. 
        ('name_model_uid_unique', 'unique (name, model_id, user_id)', 'Filter names must be unique'),
    ]

    def _auto_init(self, cr, context=None):
        super(ir_filters, self)._auto_init(cr, context)
        # Use unique index to implement unique constraint on the lowercase name (not possible using a constraint)
        cr.execute("SELECT indexname FROM pg_indexes WHERE indexname = 'ir_filters_name_model_uid_unique_index'")
        if not cr.fetchone():
            cr.execute("""CREATE UNIQUE INDEX "ir_filters_name_model_uid_unique_index" ON ir_filters
                            (lower(name), model_id, COALESCE(user_id,-1))""")

    _columns = {
        'name': fields.char('Filter Name', size=64, translate=True, required=True),
        'user_id': fields.many2one('res.users', 'User', ondelete='cascade',
                                   help="The user this filter is private to. When left empty the filter is public "
                                        "and available to all users."),
        'domain': fields.text('Domain', required=True),
        'context': fields.text('Context', required=True),
        'model_id': fields.selection(_list_all_models, 'Model', required=True),
        'is_default': fields.boolean('Default filter')
    }
    _defaults = {
        'domain': '[]',
        'context':'{}',
        'user_id': lambda self,cr,uid,context=None: uid,
        'is_default': False
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

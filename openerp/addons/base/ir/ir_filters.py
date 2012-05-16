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

from osv import osv, fields
from tools.translate import _

class ir_filters(osv.osv):
    '''
    Filters
    '''
    _name = 'ir.filters'
    _description = 'Filters'

    def _list_all_models(self, cr, uid, context=None):
        cr.execute("SELECT model, name from ir_model")
        return cr.fetchall()

    def copy(self, cr, uid, id, default=None, context=None):
        name = self.read(cr, uid, [id], ['name'])[0]['name']
        default.update({'name':_('%s (copy)') % name})
        return super(ir_filters, self).copy(cr, uid, id, default, context)

    def get_filters(self, cr, uid, model):
        """Obtain the list of filters available for the user on the given model.

        :return: list of :meth:`~osv.read`-like dicts containing the ``name``,
            ``domain``, ``user_id`` (m2o tuple) and ``context`` of the matching ``ir.filters``.
        """
        # available filters: private filters (user_id=uid) and public filters (uid=NULL) 
        act_ids = self.search(cr, uid, [('model_id','=',model),('user_id','in',[uid, False])])
        my_acts = self.read(cr, uid, act_ids, ['name', 'domain', 'context', 'user_id'])
        return my_acts

    def create_or_replace(self, cr, uid, vals, context=None):
        lower_name = vals['name'].lower()
        matching_filters = [f for f in self.get_filters(cr, uid, vals['model_id'])
                                if f['name'].lower() == lower_name
                                # next line looks for matching user_ids (specific or global), i.e.
                                # f.user_id is False and vals.user_id is False or missing,
                                # or f.user_id.id == vals.user_id
                                if (f['user_id'] and f['user_id'][0]) == vals.get('user_id', False)]
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
    }
    _defaults = {
        'domain': '[]',
        'context':'{}',
        'user_id': lambda self,cr,uid,context=None: uid,
    }

ir_filters()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

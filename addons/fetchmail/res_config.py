# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (C) 2004-2012 OpenERP S.A. (<http://openerp.com>).
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

from osv import fields, osv

class fetchmail_config_settings(osv.osv_memory):
    """ This wizard can be inherited in conjunction with 'res.config.settings', in order to
        define fields that configure a fetchmail server.

        It relies on the following convention on a set of fields::

            class my_config_wizard(osv.osv_memory):
                _name = 'my.settings'
                _inherits = ['res.config.settings', 'fetchmail.config.settings']

                _columns = {
                    'fetchmail_X': fields.boolean(..., fetchmail_model='my.model', fetchmail_name='Blah'),
                    'X_server': fields.char('Server Name', size=256),
                    'X_port': fields.integer('Port'),
                    'X_type': fields.selection(
                        [('pop', 'POP Server'), ('imap', 'IMAP Server'), ('local', 'Local Server')],
                        'Server Type'),
                    'X_is_ssl': fields.boolean('SSL/TLS'),
                    'X_user': fields.char('Username', size=256),
                    'X_password': fields.char('Password', size=1024),
                }

        The method ``get_default_fetchmail_servers`` retrieves the current fetchmail configuration
        for all fields that start with 'fetchmail_'.  It looks up configurations that match the
        given model name (``fetchmail_model``).  The method ``set_fetchmail_servers`` updates the
        fetchmail configurations by following the same conventions.  Both methods are called
        automatically by the methods of the model 'res.config.settings'.

        The onchange method ``onchange_fetchmail`` can be used to react on changes on the fields
        'X_type' and 'X_is_ssl'.  Its first parameter is the fields' prefix (here 'X').
    """
    _name = 'fetchmail.config.settings'

    def get_default_fetchmail_servers(self, cr, uid, fields, context=None):
        ir_model = self.pool.get('ir.model')
        fetchmail_server = self.pool.get('fetchmail.server')
        fetchmail_fields = [f for f in self._columns if f.startswith('fetchmail_')]
        res = {}
        for field in fetchmail_fields:
            model_name = self._columns[field].fetchmail_model
            model_id = ir_model.search(cr, uid, [('model', '=', model_name)])[0]
            server_ids = fetchmail_server.search(cr, uid, [('object_id', '=', model_id), ('state', '=', 'done')])
            if server_ids:
                server = fetchmail_server.browse(cr, uid, server_ids[0], context)
                prefix = field[10:]
                res.update({
                    field: True,
                    prefix + '_server': server.server,
                    prefix + '_port': server.port,
                    prefix + '_type': server.type,
                    prefix + '_is_ssl': server.is_ssl,
                    prefix + '_user': server.user,
                    prefix + '_password': server.password,
                })
        return res

    def set_fetchmail_servers(self, cr, uid, ids, context):
        ir_model = self.pool.get('ir.model')
        fetchmail_server = self.pool.get('fetchmail.server')
        fetchmail_fields = [f for f in self._columns if f.startswith('fetchmail_')]
        config = self.browse(cr, uid, ids[0], context)
        for field in fetchmail_fields:
            model_name = self._columns[field].fetchmail_model
            model_id = ir_model.search(cr, uid, [('model', '=', model_name)])[0]
            server_ids = fetchmail_server.search(cr, uid, [('object_id', '=', model_id), ('state', '=', 'done')])
            if config[field]:
                prefix = field[10:]
                values = {
                    'server': config[prefix + '_server'],
                    'port': config[prefix + '_port'],
                    'type': config[prefix + '_type'],
                    'is_ssl': config[prefix + '_is_ssl'],
                    'user': config[prefix + '_user'],
                    'password': config[prefix + '_password'],
                }
                if not server_ids:
                    values.update({
                        'name': getattr(self._columns[field], 'fetchmail_name', model_name),
                        'object_id': model_id,
                    })
                    server_ids = [fetchmail_server.create(cr, uid, values, context=context)]
                else:
                    server_ids = fetchmail_server.search(cr, uid, [('object_id', '=', model_id)], context=context)
                    fetchmail_server.write(cr, uid, server_ids, values, context=context)
                fetchmail_server.button_confirm_login(cr, uid, server_ids, context)
            else:
                fetchmail_server.set_draft(cr, uid, server_ids, context)

    def onchange_fetchmail(self, cr, uid, ids, prefix, server_type, ssl, context=None):
        values = {}
        if server_type == 'pop':
            values[prefix + '_port'] = ssl and 995 or 110
        elif server_type == 'imap':
            values[prefix + '_port'] = ssl and 993 or 143
        else:
            values[prefix + '_server'] = False
            values[prefix + '_port'] = 0
        return {'value': values}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

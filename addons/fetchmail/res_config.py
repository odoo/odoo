# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv

class fetchmail_config_settings(osv.osv_memory):
    """ This wizard can be inherited in conjunction with 'res.config.settings', in order to
        define fields that configure a fetchmail server.

        It relies on the following convention on the object::

            class my_config_settings(osv.osv_memory):
                _name = 'my.settings'
                _inherit = ['res.config.settings', 'fetchmail.config.settings']

                _columns = {
                    'fetchmail_stuff': fields.boolean(...,
                        fetchmail_model='my.stuff', fetchmail_name='Incoming Stuff'),
                }

                def configure_fetchmail_stuff(self, cr, uid, ids, context=None):
                    return self.configure_fetchmail(cr, uid, 'fetchmail_stuff', context)

        and in the form view::

            <field name="fetchmail_stuff"/>
            <button type="object" name="configure_fetchmail_stuff"/>

        The method ``get_default_fetchmail`` determines the value of all fields that start
        with 'fetchmail_'.  It looks up fetchmail server configurations that match the given
        model name (``fetchmail_model``) and are active.

        The button action ``configure_fetchmail_stuff`` is caught by the object, and calls
        automatically the method ``configure_fetchmail``; it opens the fetchmail server
        configuration form for the corresponding field.
    """
    _name = 'fetchmail.config.settings'

    def get_default_fetchmail(self, cr, uid, fields, context=None):
        """ determine the value of all fields like 'fetchmail_XXX' """
        ir_model = self.pool.get('ir.model')
        fetchmail_server = self.pool.get('fetchmail.server')
        fetchmail_fields = [f for f in fields if f.startswith('fetchmail_')]
        res = {}
        for f in fetchmail_fields:
            model_name = self._columns[f].fetchmail_model
            model_id = ir_model.search(cr, uid, [('model', '=', model_name)])[0]
            server_ids = fetchmail_server.search(cr, uid, [('object_id', '=', model_id), ('state', '=', 'done')])
            res[f] = bool(server_ids)
        return res

    def set_fetchmail(self, cr, uid, ids, context=None):
        """ deactivate fetchmail servers for all fields like 'fetchmail_XXX' that are False """
        config = self.browse(cr, uid, ids[0], context)
        fetchmail_fields = [f for f in self._columns if f.startswith('fetchmail_')]
        # determine which models should not have active fetchmail servers, and
        # deactivate all active servers for those models
        models = [self._columns[f].fetchmail_model for f in fetchmail_fields if not config[f]]
        if models:
            fetchmail_server = self.pool.get('fetchmail.server')
            server_ids = fetchmail_server.search(cr, uid, [('object_id.model', 'in', models), ('state', '=', 'done')])
            fetchmail_server.set_draft(cr, uid, server_ids, context)

    def configure_fetchmail(self, cr, uid, field, context=None):
        """ open the form view of the fetchmail.server to configure """
        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'fetchmail.server',
            'view_mode': 'form',
            'target': 'current',
        }
        model_name = self._columns[field].fetchmail_model
        model_id = self.pool.get('ir.model').search(cr, uid, [('model', '=', model_name)])[0]
        server_ids = self.pool.get('fetchmail.server').search(cr, uid, [('object_id', '=', model_id)])
        if server_ids:
            action['res_id'] = server_ids[0]
        else:
            action['context'] = {
                'default_name': self._columns[field].fetchmail_name,
                'default_object_id': model_id,
            }
        return action

    def __getattr__(self, name):
        """ catch calls to 'configure_fetchmail_XXX' """
        if name.startswith('configure_fetchmail_'):
            return (lambda cr, uid, ids, context=None:
                    self.configure_fetchmail(cr, uid, name[10:], context))
        return super(fetchmail_config_settings, self).__getattr__(name)

#!/usr/bin/env python

from osv import osv, fields
from tools.translate import _

class pos_session_opening(osv.osv_memory):
    _name = 'pos.session.opening'

    _columns = {
        'pos_config_id' : fields.many2one('pos.config', 'PoS Config', required=True),
        'pos_session_id' : fields.many2one('pos.session', 'PoS Session'),
    }

    def open_session_cb(self, cr, uid, ids, context=None):
        assert len(ids) == 1
        proxy = self.pool.get('pos.session')
        wizard = self.browse(cr, uid, ids[0], context=context)

        if not wizard.pos_session_id:
            values = {
                'user_id' : uid,
                'config_id' : wizard.pos_config_id.id,
            }
            session_id = proxy.create(cr, uid, values, context=context)

            if all(journal.opening_control == False
                   for journal in wizard.pos_config_id.journal_ids):

                wkf_service = netsvc.LocalService('workflow')
                wkf_service.trg_validate(uid, 'pos.session', session_id, 'open', cr)

            return self._open_session(session_id)

    def open_existing_session_cb(self, cr, uid, ids, context=None):
        assert len(ids) == 1
        wizard = self.browse(cr, uid, ids[0], context=context)
        return self._open_session(wizard.pos_session_id.id)

    def _open_session(self, session_id):
        return {
            'name': _('Session'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'pos.session',
            'res_id': session_id,
            'view_id': False,
            'type': 'ir.actions.act_window',
        }

    def on_change_config(self, cr, uid, ids, config_id, context=None):
        if not config_id:
            return {}

        domain = [
            ('state', 'in', ('opening_control', 'opened')),
            ('config_id', '=', config_id),
        ]

        proxy = self.pool.get('pos.session')
        session_ids = proxy.search(cr, uid, domain, context=context)

        result = {
            'value' : {
                'pos_session_id' : session_ids and session_ids[0] or False,
            }
        }

        return result

    def default_get(self, cr, uid, fieldnames, context=None):
        current_user = self.pool.get('res.users').browse(cr, uid, uid, context=context)

        result = {
            'pos_config_id' : current_user.pos_config and current_user.pos_config.id or False,
        }

        return result

pos_session_opening()
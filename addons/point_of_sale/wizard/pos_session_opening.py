# -*- coding: utf-8 -*-
from openerp import api, fields, models, _

from openerp.addons.point_of_sale.models.point_of_sale_session import PosSession


class PosSessionOpening(models.TransientModel):
    _name = 'pos.session.opening'

    pos_config_id = fields.Many2one('pos.config', string='Point of Sale', required=True)
    pos_session_id = fields.Many2one('pos.session', string='PoS Session')
    pos_state = fields.Selection(related='pos_session_id.state',
                                 selection=PosSession.POS_SESSION_STATE,
                                 string='Session Status', readonly=True)
    pos_state_str = fields.Char(string='Status', readonly=True)
    show_config = fields.Boolean(string='Show Config', readonly=True)
    pos_session_name = fields.Char(related='pos_session_id.name', string="Session Name", size=64, readonly=True)
    pos_session_username = fields.Char(related='pos_session_id.user_id.name', size=64, readonly=True)

    @api.multi
    def open_ui(self):
        self.ensure_one()
        self.env.context = dict(self.env.context or {})
        self.env.context['active_id'] = self.pos_session_id.id
        return {
            'type': 'ir.actions.act_url',
            'url': '/pos/web/',
            'target': 'self',
        }

    @api.multi
    def open_existing_session_cb_close(self):
        self.ensure_one()
        self.pos_session_id.signal_workflow('cashbox_control')
        return self.open_session_cb()

    @api.multi
    def open_session_cb(self):
        self.ensure_one()
        assert len(self.ids) == 1, "you can open only one session at a time"
        if not self.pos_session_id:
            values = {
                'user_id': self.env.uid,
                'config_id': self.pos_config_id.id,
            }
            session_id = self.env['pos.session'].create(values)
            if session_id.state == 'opened':
                return self.open_ui()
            return session_id._open_session()
        return self._open_session(self.pos_session_id.id)

    @api.multi
    def open_existing_session_cb(self):
        assert len(self.ids) == 1
        return self._open_session(self.pos_session_id.id)

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

    @api.onchange('pos_config_id')
    def on_change_config(self):
        result = {
            'pos_session_id': False,
            'pos_state': False,
            'pos_state_str': '',
            'pos_session_username': False,
            'pos_session_name': False,
        }
        if not self.pos_config_id:
            return {'value': result}
        session = self.env['pos.session'].search([
            ('state', '!=', 'closed'),
            ('config_id', '=', self.pos_config_id.id),
            ('user_id', '=', self.env.uid),
        ], limit=1)
        if session:
            self.pos_state = str(session.state)
            self.pos_state_str = dict(PosSession.POS_SESSION_STATE).get(session.state, '')
            self.pos_session_id = session.id
            self.pos_session_name = session.name
            self.pos_session_username = session.user_id.name

        return {'value': result}

    @api.model
    def default_get(self, fieldnames):
        session = self.env['pos.session'].search([('state', '<>', 'closed'), ('user_id', '=', self.env.uid)], limit=1)
        if session:
            result = session.config_id.id
        else:
            result = self.env.user.pos_config and self.env.user.pos_config.id or False
        if not result:
            pos_confid = self.env['pos.config'].search([], limit=1)
            result = pos_confid.id or False

        count = self.env['pos.config'].search_count([('state', '=', 'active')])
        return {
            'pos_config_id': result,
            'show_config': bool(count > 1),
        }

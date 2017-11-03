from datetime import datetime

from openerp import models, api, fields
from openerp.tools.translate import _
from openerp.exceptions import UserError
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT

NOT_SAME_DAY_ERROR = _("According to the French law, you shouldn't resume a point of sale for another day. Please close and validate session %s.")


class pos_config(models.Model):
    _inherit = 'pos.config'

    @api.multi
    def open_ui(self):
        date_today = datetime.utcnow()
        for config in self.filtered(lambda c: c.company_id._is_accounting_unalterable()):
            if config.current_session_id:
                session_start = datetime.strptime(config.current_session_id.start_at, DEFAULT_SERVER_DATETIME_FORMAT)
                if session_start.date() != date_today.date():
                    raise UserError(NOT_SAME_DAY_ERROR % config.current_session_id.name)
        return super(pos_config, self).open_ui()


class pos_session(models.Model):
    _inherit = 'pos.session'

    @api.multi
    def open_frontend_cb(self):
        date_today = datetime.utcnow()
        for session in self.filtered(lambda s: s.config_id.company_id._is_accounting_unalterable()):
            session_start = datetime.strptime(session.start_at, DEFAULT_SERVER_DATETIME_FORMAT)
            if session_start.date() != date_today.date():
                raise UserError(NOT_SAME_DAY_ERROR % session.name)
        return super(pos_session, self).open_frontend_cb()


class pos_order(models.Model):
    _inherit = 'pos.order'

    l10n_fr_pos_cert_hash = fields.Char()
    l10n_fr_pos_cert_sequence_number = fields.Char()

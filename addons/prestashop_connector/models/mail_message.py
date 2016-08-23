from openerp.osv.orm import Model
from openerp.osv import fields


class MailMessage(Model):
    _inherit = 'mail.message'

    _columns = {
        'prestashop_bind_ids': fields.one2many(
            'prestashop.mail.message',
            'openerp_id',
            string="Prestashop Bindings"
        ),
    }


class PrestashopMailMessage(Model):
    _name = "prestashop.mail.message"
    _inherit = "prestashop.binding"
    _inherits = {'mail.message': 'openerp_id'}

    _columns = {
        'openerp_id': fields.many2one(
            'mail.message',
            string="Message",
            required=True,
            ondelete='cascade'
        ),
    }

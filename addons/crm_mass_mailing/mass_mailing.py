from openerp.osv import osv


class MassMailing(osv.Model):
    _name = 'mail.mass_mailing'
    _inherit = ['mail.mass_mailing', 'crm.tracking.mixin']

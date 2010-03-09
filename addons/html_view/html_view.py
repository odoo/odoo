

from osv import osv, fields

class html_view(osv.osv):
    _name = 'html.view'
    _columns = {
        'name': fields.char('Name', size=128, required=True, select=True),
        'comp_id': fields.many2one('res.company', 'Company', select=1),
        'bank_ids': fields.one2many('res.partner.bank', 'partner_id', 'Banks'),
    }
    
html_view()
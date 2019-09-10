from openerp.osv import orm


class Barcode(orm.AbstractModel):
    _name = 'website.qweb.field.barcode'
    _inherit = ['website.qweb.field', 'ir.qweb.field.barcode']

    def from_html(self, cr, uid, model, field, element, context=None):
        return None

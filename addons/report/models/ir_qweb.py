from reportlab.graphics.barcode import createBarcodeDrawing

from openerp.osv import osv
from openerp.addons.base.ir.ir_qweb import HTMLSafe


class BarcodeConverter(osv.AbstractModel):
    """ ``barcode`` widget rendering, inserts a data:uri-using image tag in the
    document. May be overridden by e.g. the website module to generate links
    instead.
    """
    _name = 'ir.qweb.field.barcode'
    _inherit = 'ir.qweb.field'

    def value_to_html(self, cr, uid, value, field, options=None, context=None):
        barcode_type = options.get('type', 'Code128')
        barcode = self.pool['report'].barcode(
            barcode_type,
            value,
            **dict((key, value) for key, value in options.items() if key in ['width', 'height', 'humanreadable']))
        return HTMLSafe('<img src="data:%s;base64,%s">' % ('png', barcode.encode('base64')))

    def from_html(self, cr, uid, model, field, element, context=None):
        return None

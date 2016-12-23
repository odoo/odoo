from openerp.osv import fields, osv


class ir_attachment(osv.osv):
    _inherit = "ir.attachment"

    def invalidate_bundle(self, cr, uid, type='%', xmlid=None, context=None):
        assert type in ('%', 'css', 'js'), "Unhandled bundle type"
        xmlid = '%' if xmlid is None else xmlid + '%'
        domain = [('url', '=like', '/web/%s/%s/%%' % (type, xmlid))]
        ids = self.search(cr, uid, domain, context=context)
        if ids:
            self.unlink(cr, uid, ids, context=context)

# -*- coding: utf-8 -*-

from openerp.osv import osv

import simplejson
import werkzeug.wrappers


class res_partner(osv.Model):
    _inherit = 'res.partner'

    def google_map_json(self, cr, uid, ids, context=None):
        data = {
            "counter": len(ids),
            "partners": []
        }
        for partner in self.pool.get('res.partner').browse(cr, uid, ids, context={'show_address': True}):
            data["partners"].append({
                'id': partner.id,
                'name': partner.name,
                'address': '\n'.join(partner.name_get()[0][1].split('\n')[1:]),
                'latitude': partner.partner_latitude,
                'longitude': partner.partner_longitude,
            })

        mime = 'application/json'
        body = "var data = " + "}, \n{".join(simplejson.dumps(data).split("}, {"))
        return werkzeug.wrappers.Response(body, headers=[('Content-Type', mime), ('Content-Length', len(body))])

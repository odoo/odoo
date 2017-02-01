# -*- encoding: utf-8 -*-
from openerp import models
import re


class res_partner(models.Model):

    _inherit = 'res.partner'

    def name_search(self, cr, user, name, args=None, operator='ilike',
                    context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        ids = []
        if name:
            ptrn_name = re.compile('(\[(.*?)\])')
            res_name = ptrn_name.search(name)
            if res_name:
                name = name.replace('[' + res_name.group(2) + '] ', '')
            partner_search = super(res_partner, self).name_search(cr, user,
                                                                  name, args, operator, context, limit)
            ids = [partner[0] for partner in partner_search]
            if not ids:
                ids = self.search(cr, user, [('x_identificacion', operator, name)] + args,
                                  limit=limit, context=context)
            if not ids:
                ptrn = re.compile('(\[(.*?)\])')
                res = ptrn.search(name)
                if res:
                    ids = self.search(cr, user,
                                      [('x_identificacion', operator, res.group(2))] + args, limit=limit,
                                      context=context)
        else:
            return super(res_partner, self).name_search(cr, user,
                                                        name, args, operator, context, limit)

        return self.name_get(cr, user, ids, context=context)

    def name_get(self, cr, uid, ids, context=None):
        if isinstance(ids, (list, tuple)) and not len(ids):
            return []
        if isinstance(ids, (long, int)):
            ids = [ids]
        res_name = super(res_partner, self).name_get(cr, uid, ids, context)
        res = []
        for record in res_name:
            partner = self.browse(cr, uid, record[0], context=context)
            name = record[1]
            if partner.x_identificacion:
                name = name + ' [' + partner.x_identificacion + '] '
            res.append((record[0], name))
        return res

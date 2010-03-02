from osv import fields, osv
from service import web_services
import time
import wizard
import pooler

class wiki_make_index(osv.osv_memory):
    _name = "wiki.make.index"
    _description = "Create Index"
    _columns = {
    }

    def wiki_do_index(self, cr, uid, ids, context):
        """ Makes Index according to page hierarchy"""
        for index_obj in self.browse(cr, uid, ids):
            wiki_pool = self.pool.get('wiki.wiki')
            cr.execute("Select id, section from wiki_wiki where id = ANY(%s) order by section " , (context['active_ids'],))
            lst0 = cr.fetchall()
            lst = []
            s_ids = {}
            for l in lst0:
                s_ids[l[1]] = l[0]
                lst.append(l[1])

            lst.sort()
            val = None
            def toint(x):
                try:
                    return int(x)
                except:
                    return 1

            lst = map(lambda x: map(toint, x.split('.')), lst)

            result = []
            current = ['0']
            current2 = []

            for l in lst:
                for pos in range(len(l)):
                    if pos >= len(current):
                        current.append('1')
                        continue
                    if (pos == len(l) - 1) or (pos >= len(current2)) or (toint(l[pos]) > toint(current2[pos])):
                        current[pos] = str(toint(current[pos]) + 1)
                        current = current[:pos + 1]
                        if pos == len(l) - 1:
                            break

                key = ('.'.join([str(x) for x in l]))
                id = s_ids[key]
                val = ('.'.join([str(x) for x in current[:]]), id)

            if val:
                result.append(val)
            current2 = l

            for rs in result:
                wiki_pool.write(cr, uid, [rs[1]], {'section': rs[0]})
        return {}


wiki_make_index()


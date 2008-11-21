# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2006 TINY SPRL. (http://axelor.com) All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from osv import fields, osv
import time
#from core.Wiki2Html import Wiki2Html
from StringIO import StringIO

class Tag(osv.osv):
    _name="wiki.wiki.tag"
    _description="Wiki"

    _columns={
       'name':fields.char('Title',size=128),
    }
Tag()

class Wiki(osv.osv):
    _name="wiki.wiki"
    _description="Wiki"
    _order = 'model_id'
    _columns={
       'name':fields.char('Title', size=128, select=True, required=True),
       'write_uid':fields.many2one('res.users',"Last Modify By"),
       'text_area':fields.text("Content", select=True),
       'create_uid':fields.many2one('res.users','Authour', select=True),
       'create_date':fields.datetime("Created on", select=True),
       'write_date':fields.datetime("Last modified", select=True),
       'tags':fields.char('Tags', size=1024), # many2many("wiki.wiki.tag","wiki_tag_many_id","wiki_id","tag_id","Tags", select=True),
       'history_id':fields.one2many('wiki.wiki.history','history_wiki_id','History Lines'),
       'path':fields.char('Page Path',size=128),
       'model_id': fields.many2one('ir.model', 'Model id', select=True, ondelete='cascade'),
       'res_id': fields.integer("Record Id"),
       'minor_edit':fields.boolean('Thisd is a minor edit', select=True),
       'summary':fields.char('Summary',size=256, select=True),
    }

    def __init__(self, cr, pool):
        super(Wiki, self).__init__(cr, pool)
        self.oldmodel = None

    def read(self, cr, uid, cids, fields=None, context=None, load='_classic_read'):
        ids = []
        for id in cids:
            if type(id) == type(1):
                ids.append(id)
            elif type(id) == type(u''):
                ids.append(10)
                
        result = super(Wiki, self).read(cr, uid, ids, fields, None, load='_classic_read')
        return result

    def create(self, cr, uid, vals, context=None):
        if not vals.has_key('minor_edit'):
            return super(Wiki,self).create(cr, uid, vals, context)
        vals['history_id']=[[0,0,{'minor_edit':vals['minor_edit'],'text_area':vals['text_area'],'summary':vals['summary']}]]
        return super(Wiki,self).create(cr, uid, vals, context)

    def write(self, cr, uid, ids, vals, context=None):
#        wiki_data=self.read(cr,uid,ids,['minor_edit','summary'])[0]
        if vals.get('text_area'):
#            vals['html'] = self.Wiki2Html(vals['text_area'])
            if vals.has_key('minor_edit') and vals.has_key('summary'):
                vals['history_id']=[[0,0,{'minor_edit':vals['minor_edit'],'text_area':vals['text_area'],'modify_by':uid,'summary':vals['summary']}]]
            elif vals.has_key('minor_edit'):
                vals['history_id']=[[0,0,{'minor_edit':vals['minor_edit'],'text_area':vals['text_area'],'modify_by':uid,'summary':wiki_data['summary']}]]
            elif vals.has_key('summary'):
                vals['history_id']=[[0,0,{'minor_edit':wiki_data['summary'],'text_area':vals['text_area'],'modify_by':uid,'summary':vals['summary']}]]
            else:
                vals['history_id']=[[0,0,{'minor_edit':wiki_data['minor_edit'],'text_area':vals['text_area'],'modify_by':uid,'summary':wiki_data['summary']}]]
        return super(Wiki,self).write(cr, uid, ids, vals, context)
Wiki()

class History(osv.osv):
    _name="wiki.wiki.history"
    _description="Wiki History"
    _rec_name="date_time"
    _order = 'id DESC'
    _columns={
      'date_time':fields.datetime("Date",select=True),
      'text_area':fields.text("Text area",select=True),
      'minor_edit':fields.boolean('This is a major edit ?',select=True),
      'summary':fields.char('Summary',size=256, select=True),
      'modify_by':fields.many2one('res.users',"Modify By", select=True),
      'hist_write_date':fields.datetime("Last modified", select=True),
      'history_wiki_id':fields.many2one('wiki.wiki','Wiki Id', select=True)
    }
    _defaults = {
        'hist_write_date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'modify_by': lambda obj,cr,uid,context: uid,
    }
    
    def getDiff(self, cr, uid, v1, v2, context={}):
        import difflib
        
        history_pool = self.pool.get('wiki.wiki.history')
        
        text1 = history_pool.read(cr, uid, [v1], ['text_area'])[0]['text_area']
        text2 = history_pool.read(cr, uid, [v2], ['text_area'])[0]['text_area']
        
        line1 = text1.splitlines(1)
        line2 = text2.splitlines(1)
        
        diff = difflib.HtmlDiff()
        
        return diff.make_file(line1, line2, "Revision-%s" % (v1), "Revision-%s" % (v2), context=False)
    
History()

from StringIO import StringIO
from HTMLParser import HTMLParser

class IndexLine(osv.osv):
    _name="wiki.index.line"
    _description="Index Lines"
    _columns={
      'name':fields.text('Content', select=True),
      'active':fields.boolean('Active', select=True),
      'model':fields.char('Resource',size=256, select=True),
      'res_id':fields.integer('Resource Id', select=True),
    }
    _defaults = {
        'active': lambda *a: True,
    }
    
    def __init__(self, cr , pool):
        super(IndexLine, self).__init__(cr, pool)
     
    def reIndex(self, cr, uid, ids, context={}):
        password = self.pool.get('res.users').browse(cr, uid, uid).password
        self.server.init(cr.dbname, uid, password, True)
        self.server.open()
        
        self.Index(cr, uid, context)
        
        self.server.close()
        return True
    
    def Index(self, cr, uid, ids, context={}):
        
        entry_pool = self.pool.get('wiki.index.line')
        eids = entry_pool.search(cr, uid, [])
        
        model_pool = self.pool.get('ir.model')
        field_pool = self.pool.get('ir.model.fields')
        
        ids = model_pool.search(cr, uid, [('model','!=','wiki.index.line')])
        models = model_pool.read(cr, uid, ids, ['id', 'model'])
        
        for mod in models:
            res_ids = None
            
            if str(mod['model']).startswith('workflow'):
                continue
            
            if str(mod['model']).startswith('ir'):
                continue
            
            if str(mod['model']).startswith('wiki.index.line'):
                continue
            
            if str(mod['model']).startswith('res.currency'):
                continue
            
            if str(mod['model']).startswith('wiki.wiki'):
                continue
            
            if str(mod['model']).startswith('report'):
                continue
            
            if str(mod['model']).startswith('account_analytic_analysis.summary.user'):
                continue
            
            if str(mod['model']).startswith('hr_timesheet_invoice.factor'):
                continue
            
            try:
                fids = field_pool.search(cr, 1, [('model_id','=',mod['id'])])
                fdata = field_pool.read(cr, uid, fids, ['name','relation', 'ttype'])
            except Exception, e:
                continue
        
            res_pool = None
            res_ids = None

            res_pool = self.pool.get(mod['model'])
            
            res_datas = None
            
            try:
                res_ids = res_pool.search(cr, 1, [])
                res_datas = res_pool.read(cr, 1, res_ids)
            except Exception, e:
                print e
                continue
            
            print 'Indexing : ', mod['model'], ' Auto Status : '
            
            if res_datas:
                for res_data in res_datas:
                    
                    exist_ids = entry_pool.search(cr, uid, [('res_id','=',res_data['id']),('model','=',mod['model'])])
                    if exist_ids.__len__() > 0:
                        continue

                    final_res = ''
                    final_res += ' '.join(map(str,res_data.values()))
                    
                    entry_pool.create(cr, uid, {
                        'model':mod['model'],
                        'res_id':res_data['id'],
                        'name': final_res
                    })
                    cr.commit()

        return True
    
    def createIndex(self, cr, uid, ids, context={}):
        return self.Index(cr, uid, ids, context)
    
    def getResult(self, cr, uid, key, reSearch=True, context = {}):
        
        if context and context.get('read_all') and key:
            try:
                ids = self.search(cr, uid, [('name','ilike',key)])
                res = self.read(cr, uid, ids, ['model', 'res_id'])
            except Exception, e:
                raise osv.except_osv('Search Error !!', e.faultString)
            
            trs = {}
            for rs in res:
                model = rs.get('model')
                id = rs.get('res_id')
                if trs.has_key(model):
                    olds = trs[model]
                    olds.append(id)
                else:
                    trs[model] = [id]
                    
            res = trs
            if res:
                buffer = ''
                for mod in res.keys():
                    sbuff = ''
                    obj_pool = self.pool.get(mod)
                    header = False
                    
                    for id in res[mod]:
                        name = None
                        try:
                            name = obj_pool.name_get(cr, 1, [id])[0][1]
                            obj_pool.read(cr, uid, [id])
                            header = True
                        except Exception, e:
                            header = False
                            continue

                        rec_url = '/form/view?model=' + mod + "&id=" + str(id)
                        edit_url = '/form/edit?model=' + mod + "&id=" + str(id)
                        sbuff+= '#Row\n'
                        name = name.replace('/',' ')
                        name = name.replace('*',' ')
                        name = name.replace('_',' ')
                        sbuff+= '| # | ' + name + ' | [' +  mod + '/' + str(id) + ' -  Wiki]' + ' | [' +  rec_url + ' - Browse ] | [' +  edit_url + ' - Edit ]\n'
                    
                    if header == True:
                        mid = self.pool.get('ir.model').search(cr, uid, [('model','=',mod)])[0]
                        mod_data = self.pool.get('ir.model').browse(cr, uid, mid).name
                        sbuff = '\n==' + mod_data + '==\n' + sbuff
                        
                    buffer += sbuff
                html = self.pool.get('wiki.wiki').Wiki2Html(buffer)
                html = html.replace('$s', '<strike>')
                html = html.replace('$es', '</strike>')
                return [{'html':html}]

        return None

IndexLine()
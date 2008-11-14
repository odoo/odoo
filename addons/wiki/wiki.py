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
from Wiki2Html import Wiki2Html
import xmlrpclib
import base64
import os
from StringIO import StringIO
import popen2

class Tag(osv.osv):
    _name="base.wiki.tag"
    _description="Wiki"
    _rec_name="title"
    _columns={
       'title':fields.char('Title',size=128),
    }
Tag()

class Wiki(osv.osv):
    _name="base.wiki"
    _description="Wiki"
    _rec_name="title"
    _order = 'model_id'
    _columns={
       'title':fields.char('Title', size=128, select=True),
       'last_modify_by':fields.many2one('res.users',"Last Modify By"),
       'text_area':fields.text("Content", select=True),
       'wiki_create_uid':fields.many2one('res.users','Authour', select=True),
       'wiki_create_date':fields.datetime("Created on", select=True),
       'wiki_write_date':fields.datetime("Last modified", select=True),
       'tags':fields.many2many("base.wiki.tag","wiki_tag_many_id","wiki_id","tag_id","Tags", select=True),
       #'forum_id':fields.one2many('base.wiki.forum','wiki_id','Forum Lines'),
       'history_id':fields.one2many('base.wiki.history','history_wiki_id','History Lines'),
       'html':fields.text("Html Data", select=True),
       'path':fields.char('Page Path',size=128),
       'model_id': fields.many2one('ir.model', 'Model id', select=True, ondelete='cascade'),
       'res_id': fields.integer("Record Id"),
       'minor_edit':fields.boolean('Thisd is a minor edit', select=True),
       'summary':fields.char('Summary',size=256, select=True),
    }
    _defaults = {
        'wiki_create_date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'wiki_create_uid': lambda obj,cr,uid,context: uid,
    }

    def __init__(self, cr, pool):
        super(Wiki, self).__init__(cr, pool)
        self.oldmodel = None

    def read(self, cr, uid, cids, fields=None, context=None, load='_classic_read'):
        result = super(Wiki, self).read(cr, uid, cids, {}, load='_classic_read')

        if context and context.get('index'):
            ids = self.search(cr, uid, [('model_id','!=',False), ('id','in',cids)])
            res = self.read(cr, uid, ids)

            buffer = ''
            for rs in res:
                if self.oldmodel != rs['model_id'][1] or self.oldmodel == None:
                    self.oldmodel = rs['model_id'][1]
                    buffer+= '\n==' + self.pool.get('ir.model').browse(cr, uid, rs['model_id'][0]).name + '==\n'

                rec_url = '/form/view?model=' + rs['model_id'][1] + "&id=" + str(rs['res_id'])
                edit_url = '/form/edit?model=' + rs['model_id'][1] + "&id=" + str(rs['res_id'])
                buffer+= '#Row\n'
                buffer+= '| # | ' + rs['title'] + ' | [' +  rs['path'] + ' -  wiki]' + ' | [' +  rec_url + ' - Browse ] | [' +  edit_url + ' - Edit ]\n'

            ids = self.search(cr, uid, [('model_id','=',False), ('id','in',cids)])
            res = self.read(cr, uid, ids)

            if res:
                buffer+= '\n==Other Pages==\n'
                for rs in res:

                    buffer+= '* [' +  rs['path'] + ' - ' + rs['title'] + ']\n'

            return [{'html':self.Wiki2Html(buffer)}]
        else:
            return result

    def Wiki2Html(self, wiki):
        fileName = 'data.txt'
        file = open(fileName, 'w')
        file.write(wiki+'\n\n')
        file.close()

        parser = Wiki2Html()
        parser.read(fileName)
        return parser.html

    def create(self, cr, uid, vals, context=None):
        if vals.get('text_area'):
            vals['html'] = self.Wiki2Html(vals['text_area'])
        else:
            vals['text_area'] = 'Your text goes here'
            vals['html'] = 'You have not create the page.'
        if not vals.has_key('minor_edit'):
            return super(Wiki,self).create(cr, uid, vals, context)
        vals['history_id']=[[0,0,{'minor_edit':vals['minor_edit'],'text_area':vals['text_area'],'modify_by':uid,'summary':vals['summary']}]]
        return super(Wiki,self).create(cr, uid, vals, context)

    def write(self, cr, uid, ids, vals, context=None):
        vals['wiki_write_date']=time.strftime('%Y-%m-%d %H:%M:%S')
        vals['last_modify_by']=uid
        wiki_data=self.read(cr,uid,ids,['minor_edit','summary'])[0]
        if vals.get('text_area'):
            vals['html'] = self.Wiki2Html(vals['text_area'])
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

#class Forum(osv.osv):
#    _name="base.wiki.forum"
#    _description="Wiki Forum"
#    _rec_name="title"
#    _columns={
#        'title':fields.char('Title',size=128),
#        'replies':fields.integer('Replies'),
#        'wiki_authour':fields.many2one('res.users','Created By'),
#        'last_post':fields.datetime("Last Post",readonly=True),
#        'by':fields.many2one('res.users','By',readonly=True),
#        'discussion_lines':fields.one2many('base.wiki.discussion','forum_id','Discussion Lines'),
#        'wiki_id':fields.many2one('base.wiki','Wiki Id')
#    }
#Forum()
#
#class Discussion(osv.osv):
#    _name="base.wiki.discussion"
#    _description="Wiki Discussion"
#    _rec_name="wiki_authour"
#    _columns={
#        'wiki_authour':fields.many2one('res.users','Authour',readonly=True),
#        'posted_date':fields.datetime("Posted Date",readonly=True),
#        'message':fields.text('Message'),
#        'forum_id':fields.many2one('base.wiki.forum','Forum Id')
#    }
#Discussion()

class History(osv.osv):
    _name="base.wiki.history"
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
      'history_wiki_id':fields.many2one('base.wiki','Wiki Id', select=True)
    }
    _defaults = {
        'hist_write_date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'modify_by': lambda obj,cr,uid,context: uid,
    }
    
    def getDiff(self, cr, uid, v1, v2, context={}):
        import difflib
        
        history_pool = self.pool.get('base.wiki.history')
        
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
    _name="base.index.line"
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
        
        entry_pool = self.pool.get('base.index.line')
        eids = entry_pool.search(cr, uid, [])
#        entry_pool.unlink(cr, uid, eids)
#        cr.commit()
        
        model_pool = self.pool.get('ir.model')
        field_pool = self.pool.get('ir.model.fields')
        
        ids = model_pool.search(cr, uid, [('model','!=','base.index.line')])
        models = model_pool.read(cr, uid, ids, ['id', 'model'])
        
        for mod in models:
            res_ids = None
            
            if str(mod['model']).startswith('workflow'):
                continue
            
            if str(mod['model']).startswith('ir'):
                continue
            
            if str(mod['model']).startswith('base.index.line'):
                continue
            
            if str(mod['model']).startswith('res.currency'):
                continue
            
            if str(mod['model']).startswith('base.wiki'):
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
#            
#            fkeys = {}
#            tkeys = {}
#            for fd in fdata:
#                fkeys[fd['name']] = fd['relation']
#                tkeys[fd['name']] = fd['ttype']
        
            res_pool = None
            res_ids = None

            res_pool = self.pool.get(mod['model'])
            
            res_datas = None
            
            try:
                res_ids = res_pool.search(cr, 1, [])
                res_datas = res_pool.read(cr, 1, res_ids)
                #cr.execute("select * from %s" % ( mod['model'].replace('.','_')))
                #res_datas = cr.dictfetchall()
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
#                    
#                    for col in res_data:
#                        if fkeys.has_key(col) and fkeys[col] != 'NULL':
#                            if tkeys.has_key(col) and tkeys[col] == 'one2many':
#                                rel_pool = self.pool.get(fkeys.get(col))
#                                try:
#                                    foreign_key = res_pool._columns[col]._fields_id
#                                except Exception, e:
#                                    print e
#                                    continue
#                                fkids = rel_pool.search(cr, 1, [(foreign_key, '=', res_data['id'])])
#                                if fkids.__len__() > 0:
#                                    fkdata = rel_pool.read(cr, 1, fkids)
#                                    for fkd in fkdata:
#                                        final_res += ' '.join(map(str,fkd.values()))

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
        
#        password = self.pool.get('res.users').browse(cr, uid, uid).password
#        self.server.init(cr.dbname, uid, password, True)
        
        if context and context.get('read_all') and key:
            try:
                #res = self.server.search(key)
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
                html = self.pool.get('base.wiki').Wiki2Html(buffer)
                html = html.replace('$s', '<strike>')
                html = html.replace('$es', '</strike>')
                return [{'html':html}]
#            else:
#                #TODO: need to create an index on the new records
#                if reSearch:
#                    self.Index(cr, uid, context)
#                    self.getResult(cr, uid, key, False, context)

        return None

IndexLine()

class Project(osv.osv):
    _inherit = 'project.project'
    _name = 'project.project'
    _columns = {
        'wiki':fields.many2one('base.wiki', 'Wiki'),
        'dwiki':fields.many2one('base.wiki', 'Developer Wiki'),
    }    
Project()

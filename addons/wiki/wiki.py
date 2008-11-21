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
from StringIO import StringIO
from HTMLParser import HTMLParser

class WikiGroup(osv.osv):
    _name = "wiki.groups"
    _description="Wiki Groups"
    _order = 'name'
    _columns={
       'name':fields.char('Name', size=256, select=True, required=True),
       'notes':fields.text("Description", select=True),
       'create_date':fields.datetime("Created on", select=True),
    }
WikiGroup()

class Wiki(osv.osv):
    _name="wiki.wiki"
    _description="Wiki"
    _order = 'name'
    _columns={
        'group_id':fields.many2one('wiki.groups', 'Group'),
        'name':fields.char('Title', size=256, select=True, required=True),
        'write_uid':fields.many2one('res.users',"Last Modify By"),
        'text_area':fields.text("Content", select=True),
        'create_uid':fields.many2one('res.users','Authour', select=True),
        'create_date':fields.datetime("Created on", select=True),
        'write_date':fields.datetime("Last modified", select=True),
        'tags':fields.char('Tags', size=1024),
        'history_id':fields.one2many('wiki.wiki.history','history_wiki_id','History Lines'),
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
        if vals.get('text_area'):
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
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

class Wiki(osv.osv):
    _name="wiki.wiki"
Wiki()

class WikiGroup(osv.osv):
    _name = "wiki.groups"
    _description="Wiki Groups"
    _order = 'name'
    _columns={
       'name':fields.char('Wiki Group', size=256, select=True, required=True),
       'parent_id':fields.many2one('wiki.groups', 'Parent Group', ondelete='set null'),
       'child_ids':fields.one2many('wiki.groups', 'parent_id', 'Child Groups'),
       'page_ids':fields.one2many('wiki.wiki', 'group_id', 'Pages'),
       'notes':fields.text("Description", select=True),
       'create_date':fields.datetime("Created Date", select=True),
       'template': fields.text('Wiki Template'),
       'section': fields.boolean("Make Section ?"),
       'home':fields.many2one('wiki.wiki', 'Pages')
    }
WikiGroup()

class GroupLink(osv.osv):
    _name = "wiki.groups.link"
    _description="Wiki Groups Links"
    _rec_name = 'action_id'
    _columns={
       'group_id':fields.many2one('wiki.groups', 'Parent Group', ondelete='set null'),
       'action_id': fields.many2one('ir.ui.menu', 'Menu')
    }
GroupLink()

class Wiki(osv.osv):
    _inherit="wiki.wiki"
    _description="Wiki Page"
    _order = 'section,create_date desc'
    _columns={
        'name':fields.char('Title', size=256, select=True, required=True),
        'write_uid':fields.many2one('res.users',"Last Author"),
        'text_area':fields.text("Content"),
        'create_uid':fields.many2one('res.users','Author', select=True),
        'create_date':fields.datetime("Created on", select=True),
        'write_date':fields.datetime("Modification Date", select=True),
        'tags':fields.char('Tags', size=1024),
        'history_id':fields.one2many('wiki.wiki.history','wiki_id','History Lines'),
        'minor_edit':fields.boolean('Minor edit', select=True),
        'summary':fields.char('Summary',size=256, select=True),
        'section': fields.char('Section', size=32, help="Use page section code like 1.2.1"),
        'group_id':fields.many2one('wiki.groups', 'Wiki Group', select=1, ondelete='set null'),
        'toc':fields.boolean('Table of Contents'),
        'review': fields.boolean('Need Review')
    }
    def onchange_group_id(self, cr, uid, ids, group_id, content, context={}):
        if (not group_id) or content:
            return {}
        grp = self.pool.get('wiki.groups').browse(cr, uid, group_id)
        section = '0'
        for page in grp.page_ids:
            if page.section: section = page.section
        s = section.split('.')
        template = grp.template
        try:
            s[-1] = str(int(s[-1])+1)
        except:
            pass
        section = '.'.join(s)
        return {
            'value':{
                'text_area': template,
                'section': section
            }
        }
    def copy_data(self, cr, uid, id, default=None, context=None):
        return super(Wiki, self).copy_data(cr, uid, id, {'wiki_id':False}, context)

    def create(self, cr, uid, vals, context=None):
	id = super(Wiki,self).create(cr, uid, vals, context)
        history = self.pool.get('wiki.wiki.history')
	if vals.get('text_area'):
	    res = {
                'minor_edit':vals.get('minor_edit', True),
                'text_area':vals.get('text_area',''),
                'write_uid':uid,
                'wiki_id' : id,
                'summary':vals.get('summary','')
            }
            history.create(cr, uid, res)
	return id

    def write(self, cr, uid, ids, vals, context=None):
        result = super(Wiki,self).write(cr, uid, ids, vals, context)
        history = self.pool.get('wiki.wiki.history')
        if vals.get('text_area'):
            for id in ids:
                res = {
                    'minor_edit':vals.get('minor_edit', True),
                    'text_area':vals.get('text_area',''),
                    'write_uid':uid,
                    'wiki_id' : id,
                    'summary':vals.get('summary','')
                }
                history.create(cr, uid, res)
        return result

Wiki()

class History(osv.osv):
    _name = "wiki.wiki.history"
    _description = "Wiki History"
    _rec_name = "summary"
    _order = 'id DESC'
    _columns = {
      'create_date':fields.datetime("Date",select=True),
      'text_area':fields.text("Text area"),
      'minor_edit':fields.boolean('This is a major edit ?',select=True),
      'summary':fields.char('Summary',size=256, select=True),
      'write_uid':fields.many2one('res.users',"Modify By", select=True),
      'wiki_id':fields.many2one('wiki.wiki','Wiki Id', select=True)
    }
    _defaults = {
        'write_uid': lambda obj,cr,uid,context: uid,
    }
    def getDiff(self, cr, uid, v1, v2, context={}):
        import difflib
        history_pool = self.pool.get('wiki.wiki.history')
        text1 = history_pool.read(cr, uid, [v1], ['text_area'])[0]['text_area']
        text2 = history_pool.read(cr, uid, [v2], ['text_area'])[0]['text_area']
        line1 = line2 = ''
        if text1:
            line1 = text1.splitlines(1)
        if text2:
            line2 = text2.splitlines(1)
        if (not line1 and not line2) or (line1 == line2):
            raise osv.except_osv(_('Warning !'), _('There are no chnages in revisions'))
        diff = difflib.HtmlDiff()
        return diff.make_file(line1, line2, "Revision-%s" % (v1), "Revision-%s" % (v2), context=False)
History()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

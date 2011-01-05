# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 OpenERP s.a. (<http://openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

""" Helper functions for translation testing.
"""

import pooler
import logging

def install_dummy_language(cr, uid):
    """ Install a dummy language xx_XX and synchronize it (create all terms).
    """

    pool = pooler.get_pool(cr.dbname)
    res_lang = pool.get('res.lang')
    base_update_translations = pool.get('base.update.translations')

    # create xx_XX if it doesn't exist yet.
    ids = res_lang.search(cr, uid, [('code', '=', 'xx_XX')])
    if not ids:
        res_lang.create(cr, uid, {'code': 'xx_XX', 'iso_code': 'xx', 'name': 'Dummy Language', 'translatable': True})

    # create base.update.translations if it doesn't exist yet.
    ids = base_update_translations.search(cr, uid, [('lang', '=', 'xx_XX')])
    id = 0
    if not ids:
        id = base_update_translations.create(cr, uid, {'lang': 'xx_XX'})
    else:
        id = ids[0]

    # synchronize xx_XX
    print base_update_translations.act_update(cr, uid, [id])

    # add marks on all xx_XX terms
    cr.execute(u"update ir_translation set value='⟨⟨'||value||'⟩⟩' where lang='xx_XX'")

def has_marks(s):
  return s[:2] == u"⟨⟨" and s[-2:] == u"⟩⟩"

def check_all_views(cr, uid):
    pool = pooler.get_pool(cr.dbname)
    ir_ui_view = pool.get('ir.ui.view')

    ids = ir_ui_view.search(cr, uid, [])
    for view in ir_ui_view.browse(cr, uid, ids):
        check_view(cr, uid, view.id, view.model)

def check_view(cr, uid, view_id, view_model):
    pool = pooler.get_pool(cr.dbname)
    model = pool.get(view_model)
    if not model:
        return

    log = logging.getLogger('tools.test_translate')

    o = model.fields_view_get(cr, uid, view_id, 'tree', {'lang': 'xx_XX'})

    arch = o['arch']
    # TODO check translation in arch (see trans_parse_view in bin/tools/translate.py,
    # search views, ...
    # TODO it happens that o['view_id'] != view_id...
    fields = o['fields']
    checked_fields = 0
    for k, v in fields.items():
        checked_fields = checked_fields + 1
        if v.has_key('string') and not has_marks(v['string']):
            print "string not translated in %s / %s / %s (view_id: %s)" % (o['model'], o['name'], o['type'], o['view_id'])
        if v.has_key('help') and not has_marks(v['help']):
            print "help not translated in %s / %s / %s (view_id: %s)" % (o['model'], o['name'], o['type'], o['view_id'])
        if v.has_key('selection'):
            for selk, selv in v['selection']:
                if not has_marks(selv):
                    print "selection not translated in %s / %s / %s (view_id: %s)" % (o['model'], o['name'], o['type'], o['view_id'])
                    break
    #print "%s fields checked for %s %s %s %s %s" % (checked_fields, o['model'], o['name'], o['type'], o['view_id'], view_id)


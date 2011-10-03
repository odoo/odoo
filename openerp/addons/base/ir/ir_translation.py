# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

from osv import fields, osv
import tools

TRANSLATION_TYPE = [
    ('field', 'Field'),
    ('model', 'Object'),
    ('rml', 'RML  (deprecated - use Report)'), # Pending deprecation - to be replaced by report!
    ('report', 'Report/Template'),
    ('selection', 'Selection'),
    ('view', 'View'),
    ('wizard_button', 'Wizard Button'),
    ('wizard_field', 'Wizard Field'),
    ('wizard_view', 'Wizard View'),
    ('xsl', 'XSL'),
    ('help', 'Help'),
    ('code', 'Code'),
    ('constraint', 'Constraint'),
    ('sql_constraint', 'SQL Constraint')
]

class ir_translation(osv.osv):
    _name = "ir.translation"
    _log_access = False

    def _get_language(self, cr, uid, context):
        lang_model = self.pool.get('res.lang')
        lang_ids = lang_model.search(cr, uid, [('translatable', '=', True)], context=context)
        lang_data = lang_model.read(cr, uid, lang_ids, ['code', 'name'], context=context)
        return [(d['code'], d['name']) for d in lang_data]

    _columns = {
        'name': fields.char('Field Name', size=128, required=True),
        'res_id': fields.integer('Resource ID', select=True),
        'lang': fields.selection(_get_language, string='Language', size=16),
        'type': fields.selection(TRANSLATION_TYPE, string='Type', size=16, select=True),
        'src': fields.text('Source'),
        'value': fields.text('Translation Value'),
        # These two columns map to ir_model_data.module and ir_model_data.name.
        # They are used to resolve the res_id above after loading is done.
        'module': fields.char('Module', size=64, help='Maps to the ir_model_data for which this translation is provided.'),
        'xml_id': fields.char('External ID', size=128, help='Maps to the ir_model_data for which this translation is provided.'),
    }

    def _auto_init(self, cr, context={}):
        super(ir_translation, self)._auto_init(cr, context)

        # FIXME: there is a size limit on btree indexed values so we can't index src column with normal btree. 
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('ir_translation_ltns',))
        if cr.fetchone():
            #temporarily removed: cr.execute('CREATE INDEX ir_translation_ltns ON ir_translation (name, lang, type, src)')
            cr.execute('DROP INDEX ir_translation_ltns')
            cr.commit()
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('ir_translation_lts',))
        if cr.fetchone():
            #temporarily removed: cr.execute('CREATE INDEX ir_translation_lts ON ir_translation (lang, type, src)')
            cr.execute('DROP INDEX ir_translation_lts')
            cr.commit()

        # add separate hash index on src (no size limit on values), as postgres 8.1+ is able to combine separate indexes
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('ir_translation_src_hash_idx',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX ir_translation_src_hash_idx ON ir_translation using hash (src)')

        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('ir_translation_ltn',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX ir_translation_ltn ON ir_translation (name, lang, type)')
            cr.commit()

    @tools.ormcache_multi(skiparg=3, multi=6)
    def _get_ids(self, cr, uid, name, tt, lang, ids):
        translations = dict.fromkeys(ids, False)
        if ids:
            cr.execute('select res_id,value ' \
                    'from ir_translation ' \
                    'where lang=%s ' \
                        'and type=%s ' \
                        'and name=%s ' \
                        'and res_id IN %s',
                    (lang,tt,name,tuple(ids)))
            for res_id, value in cr.fetchall():
                translations[res_id] = value
        return translations

    def _set_ids(self, cr, uid, name, tt, lang, ids, value, src=None):
        # clear the caches
        tr = self._get_ids(cr, uid, name, tt, lang, ids)
        for res_id in tr:
            if tr[res_id]:
                self._get_source.clear_cache(self, uid, name, tt, lang, tr[res_id])
            self._get_ids.clear_cache(self, uid, name, tt, lang, res_id)
        self._get_source.clear_cache(self, uid, name, tt, lang)

        cr.execute('delete from ir_translation ' \
                'where lang=%s ' \
                    'and type=%s ' \
                    'and name=%s ' \
                    'and res_id IN %s',
                (lang,tt,name,tuple(ids),))
        for id in ids:
            self.create(cr, uid, {
                'lang':lang,
                'type':tt,
                'name':name,
                'res_id':id,
                'value':value,
                'src':src,
                })
        return len(ids)

    @tools.ormcache(skiparg=3)
    def _get_source(self, cr, uid, name, types, lang, source=None):
        """
        Returns the translation for the given combination of name, type, language
        and source. All values passed to this method should be unicode (not byte strings),
        especially ``source``.

        :param name: identification of the term to translate, such as field name (optional if source is passed)
        :param types: single string defining type of term to translate (see ``type`` field on ir.translation), or sequence of allowed types (strings)
        :param lang: language code of the desired translation
        :param source: optional source term to translate (should be unicode)
        :rtype: unicode
        :return: the request translation, or an empty unicode string if no translation was
                 found and `source` was not passed
        """
        # FIXME: should assert that `source` is unicode and fix all callers to always pass unicode
        # so we can remove the string encoding/decoding.
        if not lang:
            return u''
        if isinstance(types, basestring):
            types = (types,)
        if source:
            query = """SELECT value 
                       FROM ir_translation 
                       WHERE lang=%s 
                        AND type in %s 
                        AND src=%s"""
            params = (lang or '', types, tools.ustr(source))
            if name:
                query += " AND name=%s"
                params += (tools.ustr(name),)
            cr.execute(query, params)
        else:
            cr.execute("""SELECT value
                          FROM ir_translation
                          WHERE lang=%s
                           AND type in %s
                           AND name=%s""",
                    (lang or '', types, tools.ustr(name)))
        res = cr.fetchone()
        trad = res and res[0] or u''
        if source and not trad:
            return tools.ustr(source)
        return trad

    def create(self, cr, uid, vals, context=None):
        if not context:
            context = {}
        ids = super(ir_translation, self).create(cr, uid, vals, context=context)
        self._get_source.clear_cache(self, uid, vals.get('name',0), vals.get('type',0),  vals.get('lang',0), vals.get('src',0))
        self._get_ids.clear_cache(self, uid, vals.get('name',0), vals.get('type',0), vals.get('lang',0), vals.get('res_id',0))
        return ids

    def write(self, cursor, user, ids, vals, context=None):
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        result = super(ir_translation, self).write(cursor, user, ids, vals, context=context)
        for trans_obj in self.read(cursor, user, ids, ['name','type','res_id','src','lang'], context=context):
            self._get_source.clear_cache(self, user, trans_obj['name'], trans_obj['type'], trans_obj['lang'], trans_obj['src'])
            self._get_ids.clear_cache(self, user, trans_obj['name'], trans_obj['type'], trans_obj['lang'], trans_obj['res_id'])
        return result

    def unlink(self, cursor, user, ids, context=None):
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        for trans_obj in self.read(cursor, user, ids, ['name','type','res_id','src','lang'], context=context):
            self._get_source.clear_cache(self, user, trans_obj['name'], trans_obj['type'], trans_obj['lang'], source=trans_obj['src'])
            self._get_ids.clear_cache(self, user, trans_obj['name'], trans_obj['type'], trans_obj['lang'], trans_obj['res_id'])
        result = super(ir_translation, self).unlink(cursor, user, ids, context=context)
        return result

ir_translation()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


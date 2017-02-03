# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from collections import defaultdict
from difflib import get_close_matches

from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.modules import get_module_path, get_module_resource

_logger = logging.getLogger(__name__)

TRANSLATION_TYPE = [
    ('field', 'Field'),                         # deprecated
    ('model', 'Object'),
    ('report', 'Report/Template'),
    ('selection', 'Selection'),
    ('view', 'View'),                           # deprecated
    ('help', 'Help'),                           # deprecated
    ('code', 'Code'),
    ('constraint', 'Constraint'),
    ('sql_constraint', 'SQL Constraint')
]


class IrTranslationImport(object):
    """ Temporary cursor for optimizing mass insert into model 'ir.translation'.

    Open it (attached to a sql cursor), feed it with translation data and
    finish() it in order to insert multiple translations in a batch.
    """
    _table = 'tmp_ir_translation_import'

    def __init__(self, model):
        """ Store some values, and also create a temporary SQL table to accept
        the data.

        :param model: the model to insert the data into (as a recordset)
        """
        self._cr = model._cr
        self._model_table = model._table
        self._overwrite = model._context.get('overwrite', False)
        self._debug = False

        # Note that Postgres will NOT inherit the constraints or indexes
        # of ir_translation, so this copy will be much faster.
        query = """ CREATE TEMP TABLE %s (
                        imd_model VARCHAR(64),
                        imd_name VARCHAR(128)
                    ) INHERITS (%s) """ % (self._table, self._model_table)
        self._cr.execute(query)

    def push(self, trans_dict):
        """ Feed a translation, as a dictionary, into the cursor """
        if not trans_dict['value']:
            return

        params = dict(trans_dict, state="translated")

        if params['type'] == 'view':
            # ugly hack for QWeb views - pending refactoring of translations in master
            if params['imd_model'] == 'website':
                params['imd_model'] = "ir.ui.view"
            # non-QWeb views do not need a matching res_id in case they do not
            # have an xml id -> force to 0 to avoid dropping them
            elif params['res_id'] is None and not params['imd_name']:
                # maybe we should insert this translation for all views of the
                # given model?
                params['res_id'] = 0

        # backward compatibility: convert 'field', 'help', 'view' into 'model'
        if params['type'] == 'field':
            model, field = params['name'].split(',')
            params['type'] = 'model'
            params['name'] = 'ir.model.fields,field_description'
            params['imd_model'] = 'ir.model.fields'
            params['imd_name'] = 'field_%s_%s' % (model.replace('.', '_'), field)

        elif params['type'] == 'help':
            model, field = params['name'].split(',')
            params['type'] = 'model'
            params['name'] = 'ir.model.fields,help'
            params['imd_model'] = 'ir.model.fields'
            params['imd_name'] = 'field_%s_%s' % (model.replace('.', '_'), field)

        elif params['type'] == 'view':
            params['type'] = 'model'
            params['name'] = 'ir.ui.view,arch_db'
            params['imd_model'] = "ir.ui.view"

        query = """ INSERT INTO %s (name, lang, res_id, src, type, imd_model, module, imd_name, value, state, comments)
                    VALUES (%%(name)s, %%(lang)s, %%(res_id)s, %%(src)s, %%(type)s, %%(imd_model)s, %%(module)s,
                            %%(imd_name)s, %%(value)s, %%(state)s, %%(comments)s) """ % self._table
        self._cr.execute(query, params)

    def finish(self):
        """ Transfer the data from the temp table to ir.translation """
        cr = self._cr
        if self._debug:
            cr.execute("SELECT count(*) FROM %s" % self._table)
            count = cr.fetchone()[0]
            _logger.debug("ir.translation.cursor: We have %d entries to process", count)

        # Step 1: resolve ir.model.data references to res_ids
        cr.execute(""" UPDATE %s AS ti
                       SET res_id = imd.res_id
                       FROM ir_model_data AS imd
                       WHERE ti.res_id IS NULL
                       AND ti.module IS NOT NULL AND ti.imd_name IS NOT NULL
                       AND ti.module = imd.module AND ti.imd_name = imd.name
                       AND ti.imd_model = imd.model; """ % self._table)

        if self._debug:
            cr.execute(""" SELECT module, imd_name, imd_model FROM %s
                           WHERE res_id IS NULL AND module IS NOT NULL """ % self._table)
            for row in cr.fetchall():
                _logger.info("ir.translation.cursor: missing res_id for %s.%s <%s> ", *row)

        # Records w/o res_id must _not_ be inserted into our db, because they are
        # referencing non-existent data.
        cr.execute("DELETE FROM %s WHERE res_id IS NULL AND module IS NOT NULL" % self._table)

        # detect the xml_translate fields, where the src must be the same
        env = api.Environment(cr, SUPERUSER_ID, {})
        src_relevant_fields = []
        for model in env:
            for field_name, field in env[model]._fields.items():
                if hasattr(field, 'translate') and callable(field.translate):
                    src_relevant_fields.append("%s,%s" % (model, field_name))

        find_expr = """
                irt.lang = ti.lang
            AND irt.type = ti.type
            AND irt.name = ti.name
            AND (
                    (ti.type = 'model' AND ti.res_id = irt.res_id AND ti.name IN %s AND irt.src = ti.src)
                 OR (ti.type = 'model' AND ti.res_id = irt.res_id AND ti.name NOT IN %s)
                 OR (ti.type = 'view' AND (irt.res_id IS NULL OR ti.res_id = irt.res_id) AND irt.src = ti.src)
                 OR (ti.type = 'field')
                 OR (ti.type = 'help')
                 OR (ti.type NOT IN ('model', 'view', 'field', 'help') AND irt.src = ti.src)
            )
        """

        # Step 2: update existing (matching) translations
        if self._overwrite:
            cr.execute(""" UPDATE ONLY %s AS irt
                           SET value = ti.value,
                               src = ti.src,
                               state = 'translated'
                           FROM %s AS ti
                           WHERE %s AND ti.value IS NOT NULL AND ti.value != ''
                       """ % (self._model_table, self._table, find_expr),
                       (tuple(src_relevant_fields), tuple(src_relevant_fields)))

        # Step 3: insert new translations
        cr.execute(""" INSERT INTO %s(name, lang, res_id, src, type, value, module, state, comments)
                       SELECT name, lang, res_id, src, type, value, module, state, comments
                       FROM %s AS ti
                       WHERE NOT EXISTS(SELECT 1 FROM ONLY %s AS irt WHERE %s);
                   """ % (self._model_table, self._table, self._model_table, find_expr),
                   (tuple(src_relevant_fields), tuple(src_relevant_fields)))

        if self._debug:
            cr.execute("SELECT COUNT(*) FROM ONLY %s" % self._model_table)
            total = cr.fetchone()[0]
            cr.execute("SELECT COUNT(*) FROM ONLY %s AS irt, %s AS ti WHERE %s" % \
                       (self._model_table, self._table, find_expr),
                       (tuple(src_relevant_fields), tuple(src_relevant_fields)))
            count = cr.fetchone()[0]
            _logger.debug("ir.translation.cursor: %d entries now in ir.translation, %d common entries with tmp", total, count)

        # Step 4: cleanup
        cr.execute("DROP TABLE %s" % self._table)
        return True


class IrTranslation(models.Model):
    _name = "ir.translation"
    _log_access = False

    name = fields.Char(string='Translated field', required=True)
    res_id = fields.Integer(string='Record ID', index=True)
    lang = fields.Selection(selection='_get_languages', string='Language')
    type = fields.Selection(TRANSLATION_TYPE, string='Type', index=True)
    src = fields.Text(string='Internal Source')  # stored in database, kept for backward compatibility
    source = fields.Text(string='Source term', compute='_compute_source',
                         inverse='_inverse_source', search='_search_source')
    value = fields.Text(string='Translation Value')
    module = fields.Char(index=True, help="Module this term belongs to")

    state = fields.Selection([('to_translate', 'To Translate'),
                              ('inprogress', 'Translation in Progress'),
                              ('translated', 'Translated')],
                             string="Status", default='to_translate',
                             help="Automatically set to let administators find new terms that might need to be translated")

    # aka gettext extracted-comments - we use them to flag openerp-web translation
    # cfr: http://www.gnu.org/savannah-checkouts/gnu/gettext/manual/html_node/PO-Files.html
    comments = fields.Text(string='Translation comments', index=True)

    _sql_constraints = [
        ('lang_fkey_res_lang', 'FOREIGN KEY(lang) REFERENCES res_lang(code)',
         'Language code of translation item must be among known languages'),
    ]

    @api.model
    def _get_languages(self):
        langs = self.env['res.lang'].search([('translatable', '=', True)])
        return [(lang.code, lang.name) for lang in langs]

    @api.depends('type', 'name', 'res_id')
    def _compute_source(self):
        ''' Get source name for the translation. If object type is model, return
        the value stored in db. Otherwise, return value store in src field.
        '''
        for record in self:
            record.source = record.src
            if record.type != 'model':
                continue
            model_name, field_name = record.name.split(',')
            if model_name not in self.env:
                continue
            model = self.env[model_name]
            field = model._fields.get(field_name)
            if field is None:
                continue
            if not callable(field.translate):
                # Pass context without lang, need to read real stored field, not translation
                result = model.browse(record.res_id).with_context(lang=None).read([field_name])
                record.source = result[0][field_name] if result else False

    def _inverse_source(self):
        ''' When changing source term of a translation, change its value in db
        for the associated object, and the src field.
        '''
        for record in self:
            if record.type == 'model':
                model_name, field_name = record.name.split(',')
                model = self.env[model_name]
                field = model._fields[field_name]
                if not callable(field.translate):
                    # Make a context without language information, because we want
                    # to write on the value stored in db and not on the one
                    # associated with the current language. Also not removing lang
                    # from context trigger an error when lang is different.
                    model.browse(record.res_id).with_context(lang=None).write({field_name: record.source})
        return self.write({'src': self.source})

    def _search_source(self, operator, value):
        ''' the source term is stored on 'src' field '''
        return [('src', operator, value)]

    @api.model_cr_context
    def _auto_init(self):
        res = super(IrTranslation, self)._auto_init()
        # Add separate md5 index on src (no size limit on values, and good performance).
        tools.create_index(self._cr, 'ir_translation_src_md5', self._table, ['md5(src)'])
        tools.create_index(self._cr, 'ir_translation_ltn', self._table, ['name', 'lang', 'type'])
        return res

    @api.model
    def _check_selection_field_value(self, field, value):
        if field == 'lang':
            return
        return super(IrTranslation, self)._check_selection_field_value(field, value)

    @api.model
    def _get_ids(self, name, tt, lang, ids):
        """ Return the translations of records.

        :param name: a string defined as "<model_name>,<field_name>"
        :param tt: the type of translation (should always be "model")
        :param lang: the language code
        :param ids: the ids of the given records
        """
        translations = dict.fromkeys(ids, False)
        if ids:
            self._cr.execute("""SELECT res_id, value FROM ir_translation
                                WHERE lang=%s AND type=%s AND name=%s AND res_id IN %s""",
                             (lang, tt, name, tuple(ids)))
            for res_id, value in self._cr.fetchall():
                translations[res_id] = value
        return translations

    CACHED_MODELS = {'ir.model.fields', 'ir.ui.view'}

    def _modified_model(self, model_name):
        """ Invalidate the ormcache if necessary, depending on ``model_name``.
        This should be called when modifying translations of type 'model'.
        """
        if model_name in self.CACHED_MODELS:
            self.clear_caches()

    @api.multi
    def _modified(self):
        """ Invalidate the ormcache if necessary, depending on the translations ``self``. """
        for trans in self:
            if trans.type != 'model' or trans.name.split(',')[0] in self.CACHED_MODELS:
                self.clear_caches()
                break

    @api.model
    def _set_ids(self, name, tt, lang, ids, value, src=None):
        """ Update the translations of records.

        :param name: a string defined as "<model_name>,<field_name>"
        :param tt: the type of translation (should always be "model")
        :param lang: the language code
        :param ids: the ids of the given records
        :param value: the value of the translation
        :param src: the source of the translation
        """
        self._modified_model(name.split(',')[0])

        # update existing translations
        self._cr.execute("""UPDATE ir_translation
                            SET value=%s, src=%s, state=%s
                            WHERE lang=%s AND type=%s AND name=%s AND res_id IN %s
                            RETURNING res_id""",
                         (value, src, 'translated', lang, tt, name, tuple(ids)))
        existing_ids = [row[0] for row in self._cr.fetchall()]

        # create missing translations
        for res_id in set(ids) - set(existing_ids):
            self.create({
                'lang': lang,
                'type': tt,
                'name': name,
                'res_id': res_id,
                'value': value,
                'src': src,
                'state': 'translated',
            })
        return len(ids)

    @api.model
    def _get_source_query(self, name, types, lang, source, res_id):
        if source:
            # Note: the extra test on md5(src) is a hint for postgres to use the
            # index ir_translation_src_md5
            query = """SELECT value FROM ir_translation
                       WHERE lang=%s AND type in %s AND src=%s AND md5(src)=md5(%s)"""
            source = tools.ustr(source)
            params = (lang or '', types, source, source)
            if res_id:
                query += " AND res_id in %s"
                params += (res_id,)
            if name:
                query += " AND name=%s"
                params += (tools.ustr(name),)
        else:
            query = """ SELECT value FROM ir_translation
                        WHERE lang=%s AND type in %s AND name=%s """
            params = (lang or '', types, tools.ustr(name))

        return (query, params)

    @tools.ormcache('name', 'types', 'lang', 'source', 'res_id')
    def __get_source(self, name, types, lang, source, res_id):
        # res_id is a tuple or None, otherwise ormcache cannot cache it!
        query, params = self._get_source_query(name, types, lang, source, res_id)
        self._cr.execute(query, params)
        res = self._cr.fetchone()
        trad = res and res[0] or u''
        if source and not trad:
            return tools.ustr(source)
        return trad

    @api.model
    def _get_source(self, name, types, lang, source=None, res_id=None):
        """ Return the translation for the given combination of ``name``,
        ``type``, ``language`` and ``source``. All values passed to this method
        should be unicode (not byte strings), especially ``source``.

        :param name: identification of the term to translate, such as field name (optional if source is passed)
        :param types: single string defining type of term to translate (see ``type`` field on ir.translation), or sequence of allowed types (strings)
        :param lang: language code of the desired translation
        :param source: optional source term to translate (should be unicode)
        :param res_id: optional resource id or a list of ids to translate (if used, ``source`` should be set)
        :rtype: unicode
        :return: the request translation, or an empty unicode string if no translation was
                 found and `source` was not passed
        """
        # FIXME: should assert that `source` is unicode and fix all callers to
        # always pass unicode so we can remove the string encoding/decoding.
        if not lang:
            return tools.ustr(source or '')
        if isinstance(types, basestring):
            types = (types,)
        if res_id:
            if isinstance(res_id, (int, long)):
                res_id = (res_id,)
            else:
                res_id = tuple(res_id)
        return self.__get_source(name, types, lang, source, res_id)

    @api.model
    def _get_terms_query(self, field, records):
        """ Utility function that makes the query for field terms. """
        query = """ SELECT * FROM ir_translation
                    WHERE lang=%s AND type=%s AND name=%s AND res_id IN %s """
        name = "%s,%s" % (field.model_name, field.name)
        params = (records.env.lang, 'model', name, tuple(records.ids))
        return query, params

    @api.model
    def _get_terms_mapping(self, field, records):
        """ Return a function mapping a ir_translation row (dict) to a value.
        This method is called before querying the database for translations.
        """
        return lambda data: data['value']

    @api.model
    def _get_terms_translations(self, field, records):
        """ Return the terms and translations of a given `field` on `records`.

        :return: {record_id: {source: value}}
        """
        result = {rid: {} for rid in records.ids}
        if records:
            map_trans = self._get_terms_mapping(field, records)
            query, params = self._get_terms_query(field, records)
            self._cr.execute(query, params)
            for data in self._cr.dictfetchall():
                result[data['res_id']][data['src']] = map_trans(data)
        return result

    @api.model
    def _sync_terms_translations(self, field, records):
        """ Synchronize the translations to the terms to translate, after the
        English value of a field is modified. The algorithm tries to match
        existing translations to the terms to translate, provided the distance
        between modified strings is not too large. It allows to not retranslate
        data where a typo has been fixed in the English value.
        """
        if not callable(field.translate):
            return

        trans = self.env['ir.translation']
        outdated = trans
        discarded = trans

        for record in records:
            # get field value and terms to translate
            value = record[field.name]
            terms = set(field.get_trans_terms(value))
            record_trans = trans.search([
                ('type', '=', 'model'),
                ('name', '=', "%s,%s" % (field.model_name, field.name)),
                ('res_id', '=', record.id),
            ])

            if not terms:
                # discard all translations for that field
                discarded += record_trans
                continue

            # remap existing translations on terms when possible
            for trans in record_trans:
                if trans.src == trans.value:
                    discarded += trans
                elif trans.src not in terms:
                    matches = get_close_matches(trans.src, terms, 1, 0.9)
                    if matches:
                        trans.write({'src': matches[0], 'state': trans.state})
                    else:
                        outdated += trans

        # process outdated and discarded translations
        outdated.write({'state': 'to_translate'})
        discarded.unlink()

    @api.model
    @tools.ormcache_context('model_name', keys=('lang',))
    def get_field_string(self, model_name):
        """ Return the translation of fields strings in the context's language.
        Note that the result contains the available translations only.

        :param model_name: the name of a model
        :return: the model's fields' strings as a dictionary `{field_name: field_string}`
        """
        fields = self.env['ir.model.fields'].sudo().search([('model', '=', model_name)])
        return {field.name: field.field_description for field in fields}

    @api.model
    @tools.ormcache_context('model_name', keys=('lang',))
    def get_field_help(self, model_name):
        """ Return the translation of fields help in the context's language.
        Note that the result contains the available translations only.

        :param model_name: the name of a model
        :return: the model's fields' help as a dictionary `{field_name: field_help}`
        """
        fields = self.env['ir.model.fields'].sudo().search([('model', '=', model_name)])
        return {field.name: field.help for field in fields}

    @api.multi
    def check(self, mode):
        """ Check access rights of operation ``mode`` on ``self`` for the
        current user. Raise an AccessError in case conditions are not met.
        """
        if self.env.user._is_admin():
            return

        # collect translated field records (model_ids) and other translations
        trans_ids = []
        model_ids = defaultdict(list)
        model_fields = defaultdict(list)
        for trans in self:
            if trans.type == 'model':
                mname, fname = trans.name.split(',')
                model_ids[mname].append(trans.res_id)
                model_fields[mname].append(fname)
            else:
                trans_ids.append(trans.id)

        # check for regular access rights on other translations
        if trans_ids:
            records = self.browse(trans_ids)
            records.check_access_rights(mode)
            records.check_access_rule(mode)

        # check for read/write access on translated field records
        fmode = 'read' if mode == 'read' else 'write'
        for mname, ids in model_ids.iteritems():
            records = self.env[mname].browse(ids)
            records.check_access_rights(fmode)
            records.check_field_access_rights(fmode, model_fields[mname])
            records.check_access_rule(fmode)

    @api.constrains('type', 'name', 'value')
    def _check_value(self):
        for trans in self.with_context(lang=None):
            if trans.type == 'model' and trans.value:
                mname, fname = trans.name.split(',')
                record = trans.env[mname].browse(trans.res_id)
                field = record._fields[fname]
                if callable(field.translate):
                    # check whether applying (trans.src -> trans.value) then
                    # (trans.value -> trans.src) gives the original value back
                    value0 = field.translate(lambda term: None, record[fname])
                    value1 = field.translate({trans.src: trans.value}.get, value0)
                    value2 = field.translate({trans.value: trans.src}.get, value1)
                    if value2 != value0:
                        raise ValidationError(_("Translation is not valid:\n%s") % trans.value)

    @api.model
    def create(self, vals):
        record = super(IrTranslation, self.sudo()).create(vals).with_env(self.env)
        record.check('create')
        record._modified()
        return record

    @api.multi
    def write(self, vals):
        if vals.get('value'):
            vals.setdefault('state', 'translated')
        elif vals.get('src') or not vals.get('value', True):
            vals.setdefault('state', 'to_translate')
        self.check('write')
        result = super(IrTranslation, self.sudo()).write(vals)
        self.check('write')
        self._modified()
        return result

    @api.multi
    def unlink(self):
        self.check('unlink')
        self._modified()
        return super(IrTranslation, self.sudo()).unlink()

    @api.model
    def insert_missing(self, field, records):
        """ Insert missing translations for `field` on `records`. """
        records = records.with_context(lang=None)
        external_ids = records.get_external_id()  # if no xml_id, empty string
        if callable(field.translate):
            # insert missing translations for each term in src
            query = """ INSERT INTO ir_translation (lang, type, name, res_id, src, value, module)
                        SELECT l.code, 'model', %(name)s, %(res_id)s, %(src)s, %(src)s, %(module)s
                        FROM res_lang l
                        WHERE l.active AND NOT EXISTS (
                            SELECT 1 FROM ir_translation
                            WHERE lang=l.code AND type='model' AND name=%(name)s AND res_id=%(res_id)s AND src=%(src)s
                        );
                    """
            for record in records:
                module = external_ids[record.id].split('.')[0]
                src = record[field.name] or None
                for term in set(field.get_trans_terms(src)):
                    self._cr.execute(query, {
                        'name': "%s,%s" % (field.model_name, field.name),
                        'res_id': record.id,
                        'src': term,
                        'module': module
                    })
        else:
            # insert missing translations for src
            query = """ INSERT INTO ir_translation (lang, type, name, res_id, src, value, module)
                        SELECT l.code, 'model', %(name)s, %(res_id)s, %(src)s, %(src)s, %(module)s
                        FROM res_lang l
                        WHERE l.active AND l.code != 'en_US' AND NOT EXISTS (
                            SELECT 1 FROM ir_translation
                            WHERE lang=l.code AND type='model' AND name=%(name)s AND res_id=%(res_id)s
                        );
                        UPDATE ir_translation SET src=%(src)s
                        WHERE type='model' AND name=%(name)s AND res_id=%(res_id)s;
                    """
            for record in records:
                module = external_ids[record.id].split('.')[0]
                self._cr.execute(query, {
                    'name': "%s,%s" % (field.model_name, field.name),
                    'res_id': record.id,
                    'src': record[field.name] or None,
                    'module': module
                })
        self._modified_model(field.model_name)

    @api.model
    def translate_fields(self, model, id, field=None):
        """ Open a view for translating the field(s) of the record (model, id). """
        main_lang = 'en_US'
        if not self.env['res.lang'].search_count([('code', '!=', main_lang)]):
            raise UserError(_("Translation features are unavailable until you install an extra translation."))

        # determine domain for selecting translations
        record = self.env[model].with_context(lang=main_lang).browse(id)
        domain = ['&', ('res_id', '=', id), ('name', '=like', model + ',%')]

        def make_domain(fld, rec):
            name = "%s,%s" % (fld.model_name, fld.name)
            return ['&', ('res_id', '=', rec.id), ('name', '=', name)]

        # insert missing translations, and extend domain for related fields
        for name, fld in record._fields.items():
            if not fld.translate:
                continue

            rec = record
            if fld.related:
                try:
                    # traverse related fields up to their data source
                    while fld.related:
                        rec, fld = fld.traverse_related(rec)
                    if rec:
                        domain = ['|'] + domain + make_domain(fld, rec)
                except AccessError:
                    continue

            assert fld.translate and rec._name == fld.model_name
            self.insert_missing(fld, rec)

        action = {
            'name': 'Translate',
            'res_model': 'ir.translation',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'view_id': self.env.ref('base.view_translation_dialog_tree').id,
            'target': 'current',
            'flags': {'search_view': True, 'action_buttons': True},
            'domain': domain,
        }
        if field:
            fld = record._fields[field]
            if not fld.related:
                action['context'] = {
                    'search_default_name': "%s,%s" % (fld.model_name, fld.name),
                }
        return action

    @api.model
    def _get_import_cursor(self):
        """ Return a cursor-like object for fast inserting translations """
        return IrTranslationImport(self)

    @api.model_cr_context
    def load_module_terms(self, modules, langs):
        """ Load PO files of the given modules for the given languages. """
        # make sure the given languages are active
        res_lang = self.env['res.lang'].sudo()
        for lang in langs:
            res_lang.load_lang(lang)
        # load i18n files
        for module_name in modules:
            modpath = get_module_path(module_name)
            if not modpath:
                continue
            for lang in langs:
                context = dict(self._context)
                lang_code = tools.get_iso_codes(lang)
                base_lang_code = None
                if '_' in lang_code:
                    base_lang_code = lang_code.split('_')[0]

                # Step 1: for sub-languages, load base language first (e.g. es_CL.po is loaded over es.po)
                if base_lang_code:
                    base_trans_file = get_module_resource(module_name, 'i18n', base_lang_code + '.po')
                    if base_trans_file:
                        _logger.info('module %s: loading base translation file %s for language %s', module_name, base_lang_code, lang)
                        tools.trans_load(self._cr, base_trans_file, lang, verbose=False, module_name=module_name, context=context)
                        context['overwrite'] = True  # make sure the requested translation will override the base terms later

                    # i18n_extra folder is for additional translations handle manually (eg: for l10n_be)
                    base_trans_extra_file = get_module_resource(module_name, 'i18n_extra', base_lang_code + '.po')
                    if base_trans_extra_file:
                        _logger.info('module %s: loading extra base translation file %s for language %s', module_name, base_lang_code, lang)
                        tools.trans_load(self._cr, base_trans_extra_file, lang, verbose=False, module_name=module_name, context=context)
                        context['overwrite'] = True  # make sure the requested translation will override the base terms later

                # Step 2: then load the main translation file, possibly overriding the terms coming from the base language
                trans_file = get_module_resource(module_name, 'i18n', lang_code + '.po')
                if trans_file:
                    _logger.info('module %s: loading translation file (%s) for language %s', module_name, lang_code, lang)
                    tools.trans_load(self._cr, trans_file, lang, verbose=False, module_name=module_name, context=context)
                elif lang_code != 'en_US':
                    _logger.info('module %s: no translation for language %s', module_name, lang_code)

                trans_extra_file = get_module_resource(module_name, 'i18n_extra', lang_code + '.po')
                if trans_extra_file:
                    _logger.info('module %s: loading extra translation file (%s) for language %s', module_name, lang_code, lang)
                    tools.trans_load(self._cr, trans_extra_file, lang, verbose=False, module_name=module_name, context=context)
        return True

    @api.model
    def get_technical_translations(self, model_name):
        """ Find the translations for the fields of `model_name`

        Find the technical translations for the fields of the model, including
        string, tooltip and available selections.

        :return: action definition to open the list of available translations
        """
        fields = self.env['ir.model.fields'].search([('model', '=', model_name)])
        view = self.env.ref("base.view_translation_tree", False) or self.env['ir.ui.view']
        return {
            'name': _("Technical Translations"),
            'view_mode': 'tree',
            'views': [(view.id, "list")],
            'res_model': 'ir.translation',
            'type': 'ir.actions.act_window',
            'domain': [
                '|',
                    '&', ('type', '=', 'model'),
                        '&', ('res_id', 'in', fields.ids),
                             ('name', 'like', 'ir.model.fields,'),
                    '&', ('type', '=', 'selection'),
                         ('name', 'like', model_name+','),
            ],
        }

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import hashlib
import itertools
import json
import logging
import operator
from collections import defaultdict
from difflib import get_close_matches

from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.modules import get_module_path, get_module_resource

_logger = logging.getLogger(__name__)

TRANSLATION_TYPE = [
    ('model', 'Model Field'),
    ('model_terms', 'Structured Model Field'),
    ('code', 'Code'),
]


class IrTranslationImport(object):
    """ Temporary cursor for optimizing mass insert into model 'ir.translation'.

    Open it (attached to a sql cursor), feed it with translation data and
    finish() it in order to insert multiple translations in a batch.
    """
    _table = 'tmp_ir_translation_import'

    def __init__(self, cr, overwrite=False):
        """ Store some values, and also create a temporary SQL table to accept
        the data.

        :param model: the model to insert the data into (as a recordset)
        """
        self._cr = cr
        self._model_table = "ir_translation"
        self._overwrite = overwrite
        self._debug = False
        self._rows = []

        # Note that Postgres will NOT inherit the constraints or indexes
        # of ir_translation, so this copy will be much faster.
        query = """ CREATE TEMP TABLE %s (
                        imd_model VARCHAR(64),
                        imd_name VARCHAR(128),
                        noupdate BOOLEAN
                    ) INHERITS (%s) """ % (self._table, self._model_table)
        self._cr.execute(query)

    def push(self, trans_dict):
        """ Feed a translation, as a dictionary, into the cursor """
        params = dict(trans_dict, state="translated")

        self._rows.append((params['name'], params['lang'], params['res_id'],
                           params['src'], params['type'], params['imd_model'],
                           params['module'], params['imd_name'], params['value'],
                           params['state'], params['comments']))

    def finish(self):
        """ Transfer the data from the temp table to ir.translation """
        cr = self._cr

        # Step 0: insert rows in batch
        query = """ INSERT INTO %s (name, lang, res_id, src, type, imd_model,
                                    module, imd_name, value, state, comments)
                    VALUES """ % self._table
        for rows in cr.split_for_in_conditions(self._rows):
            cr.execute(query + ", ".join(["%s"] * len(rows)), rows)

        _logger.debug("ir.translation.cursor: We have %d entries to process", len(self._rows))

        # Step 1: resolve ir.model.data references to res_ids
        cr.execute(""" UPDATE %s AS ti
                          SET res_id = imd.res_id,
                              noupdate = imd.noupdate
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

        count = 0
        # Step 2: insert new or upsert non-noupdate translations
        if self._overwrite:
            cr.execute(""" INSERT INTO %s(name, lang, res_id, src, type, value, module, state, comments)
                           SELECT name, lang, res_id, src, type, value, module, state, comments
                           FROM %s
                           WHERE type = 'code'
                           AND noupdate IS NOT TRUE
                           ON CONFLICT (type, lang, md5(src)) WHERE type = 'code'
                            DO UPDATE SET (name, lang, res_id, src, type, value, module, state, comments) = (EXCLUDED.name, EXCLUDED.lang, EXCLUDED.res_id, EXCLUDED.src, EXCLUDED.type, EXCLUDED.value, EXCLUDED.module, EXCLUDED.state,
                                                                                                             CASE WHEN %s.comments = 'openerp-web' THEN 'openerp-web' ELSE EXCLUDED.comments END
                                                                                                            )
                            WHERE EXCLUDED.value IS NOT NULL AND EXCLUDED.value != '';
                       """ % (self._model_table, self._table, self._model_table))
            count += cr.rowcount
            cr.execute(""" INSERT INTO %s(name, lang, res_id, src, type, value, module, state, comments)
                           SELECT name, lang, res_id, src, type, value, module, state, comments
                           FROM %s
                           WHERE type = 'model'
                           AND noupdate IS NOT TRUE
                           ON CONFLICT (type, lang, name, res_id) WHERE type = 'model'
                            DO UPDATE SET (name, lang, res_id, src, type, value, module, state, comments) = (EXCLUDED.name, EXCLUDED.lang, EXCLUDED.res_id, EXCLUDED.src, EXCLUDED.type, EXCLUDED.value, EXCLUDED.module, EXCLUDED.state, EXCLUDED.comments)
                            WHERE EXCLUDED.value IS NOT NULL AND EXCLUDED.value != '';
                       """ % (self._model_table, self._table))
            count += cr.rowcount

            cr.execute(""" INSERT INTO %s(name, lang, res_id, src, type, value, module, state, comments)
                           SELECT name, lang, res_id, src, type, value, module, state, comments
                           FROM %s
                           WHERE type = 'model_terms'
                           AND noupdate IS NOT TRUE
                           ON CONFLICT (type, name, lang, res_id, md5(src))
                            DO UPDATE SET (name, lang, res_id, src, type, value, module, state, comments) = (EXCLUDED.name, EXCLUDED.lang, EXCLUDED.res_id, EXCLUDED.src, EXCLUDED.type, EXCLUDED.value, EXCLUDED.module, EXCLUDED.state, EXCLUDED.comments)
                            WHERE EXCLUDED.value IS NOT NULL AND EXCLUDED.value != '';
                       """ % (self._model_table, self._table))
            count += cr.rowcount
        cr.execute(""" INSERT INTO %s(name, lang, res_id, src, type, value, module, state, comments)
                       SELECT name, lang, res_id, src, type, value, module, state, comments
                       FROM %s
                       WHERE %%s OR noupdate is true
                       ON CONFLICT DO NOTHING;
                   """ % (self._model_table, self._table), [not self._overwrite])
        count += cr.rowcount

        if self._debug:
            cr.execute("SELECT COUNT(*) FROM ONLY %s" % self._model_table)
            total = cr.fetchone()[0]
            _logger.debug("ir.translation.cursor: %d entries now in ir.translation, %d common entries with tmp", total, count)

        # Step 3: cleanup
        cr.execute("DROP TABLE %s" % self._table)
        self._rows.clear()
        return True


class IrTranslation(models.Model):
    _name = "ir.translation"
    _description = 'Translation'
    _log_access = False

    name = fields.Char(string='Translated field', required=True)
    res_id = fields.Integer(string='Record ID', index=True)
    lang = fields.Selection(selection='_get_languages', string='Language', validate=False)
    type = fields.Selection(TRANSLATION_TYPE, string='Type', index=True)
    src = fields.Text(string='Internal Source')  # stored in database, kept for backward compatibility
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
        return self.env['res.lang'].get_installed()

    def _auto_init(self):
        res = super(IrTranslation, self)._auto_init()
        # Add separate md5 index on src (no size limit on values, and good performance).
        tools.create_index(self._cr, 'ir_translation_src_md5', self._table, ['md5(src)'])
        # Cover 'model_terms' type
        tools.create_unique_index(self._cr, 'ir_translation_unique', self._table,
                                  ['type', 'name', 'lang', 'res_id', 'md5(src)'])
        if not tools.index_exists(self._cr, 'ir_translation_code_unique'):
            self._cr.execute("CREATE UNIQUE INDEX ir_translation_code_unique ON ir_translation (type, lang, md5(src)) WHERE type = 'code'")
        if not tools.index_exists(self._cr, 'ir_translation_model_unique'):
            self._cr.execute("CREATE UNIQUE INDEX ir_translation_model_unique ON ir_translation (type, lang, name, res_id) WHERE type = 'model'")

        return res

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

    def _modified(self):
        """ Invalidate the ormcache if necessary, depending on the translations ``self``. """
        # DLE P63: test_views.py
        for trans in self:
            if trans.type == 'model_terms' and trans.res_id:
                model, field = trans.name.split(',')
                if model in self.env:
                    model = self.env[model]
                    if field in model._fields:
                        field = model._fields[field]
                        record = model.browse(trans.res_id)
                        record.modified([field.name])
        for trans in self:
            if (trans.type != 'model' or
               (trans.name.split(',')[0] in self.CACHED_MODELS) or
               (trans.comments and 'openerp-web' in trans.comments)):  # clear get_web_trans_hash
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
        self.sudo().create([{
                'lang': lang,
                'type': tt,
                'name': name,
                'res_id': res_id,
                'value': value,
                'src': src,
                'state': 'translated',
            }
            for res_id in set(ids) - set(existing_ids)
        ])
        return len(ids)

    def _set_source(self, name, ids, src):
        """ Update the translation source of records.

        :param name: a string defined as "<model_name>,<field_name>"
        :param ids: the ids of the given records
        :param src: the source of the translation
        """
        self._cr.execute("""UPDATE ir_translation
                            SET src=%s
                            WHERE type=%s AND name=%s AND res_id IN %s
                            RETURNING id""",
                         (src, 'model', name, tuple(ids)))
        existing_ids = [row[0] for row in self._cr.fetchall()]
        # invalidate src for updated translations
        self.invalidate_cache(fnames=['src'], ids=existing_ids)

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
        if isinstance(types, str):
            types = (types,)
        if res_id:
            if isinstance(res_id, int):
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
        params = (records.env.lang, 'model_terms', name, tuple(records.ids))
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

        Translation = self.env['ir.translation']
        outdated = Translation
        discarded = Translation

        for record in records:
            # get field value and terms to translate
            value = record[field.name]
            terms = set(field.get_trans_terms(value))
            translations = Translation.search([
                ('type', '=', 'model_terms'),
                ('name', '=', "%s,%s" % (field.model_name, field.name)),
                ('res_id', '=', record.id),
            ])

            if not terms:
                # discard all translations for that field
                discarded += translations
                continue

            # remap existing translations on terms when possible; each term
            # should be translated at most once per language
            done = set()                # {(src, lang), ...}
            translations_to_match = []

            for translation in translations:
                if not translation.value:
                    discarded += translation
                    # consider it done to avoid being matched against another term
                    done.add((translation.src, translation.lang))
                elif translation.src in terms:
                    done.add((translation.src, translation.lang))
                else:
                    translations_to_match.append(translation)

            for translation in translations_to_match:
                matches = get_close_matches(translation.src, terms, 1, 0.9)
                src = matches[0] if matches else None
                if not src:
                    outdated += translation
                elif (src, translation.lang) in done:
                    discarded += translation
                else:
                    vals = {'src': src, 'state': translation.state}
                    if translation.lang == records.env.lang:
                        vals['value'] = src
                    translation.write(vals)
                    done.add((src, translation.lang))

        # process outdated and discarded translations
        outdated.write({'state': 'to_translate'})

        if discarded:
            # delete in SQL to avoid invalidating the whole cache
            discarded._modified()
            discarded.modified(self._fields)
            self.flush(self._fields, discarded)
            self.invalidate_cache(ids=discarded._ids)
            self.env.cr.execute("DELETE FROM ir_translation WHERE id IN %s", [discarded._ids])

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

    @api.model
    @tools.ormcache_context('model_name', 'field_name', keys=('lang',))
    def get_field_selection(self, model_name, field_name):
        """ Return the translation of a field's selection in the context's language.
        Note that the result contains the available translations only.

        :param model_name: the name of the field's model
        :param field_name: the name of the field
        :return: the fields' selection as a list
        """
        field = self.env['ir.model.fields']._get(model_name, field_name)
        return [(sel.value, sel.name) for sel in field.selection_ids]

    def check(self, mode):
        """ Check access rights of operation ``mode`` on ``self`` for the
        current user. Raise an AccessError in case conditions are not met.
        """
        if self.env.is_superuser():
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
        for mname, ids in model_ids.items():
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
                    src = trans.src
                    val = trans.value.strip()
                    # check whether applying (src -> val) then (val -> src)
                    # gives the original value back
                    value0 = field.translate(lambda term: None, record[fname])
                    value1 = field.translate({src: val}.get, value0)
                    # don't check the reverse if no translation happened
                    if value0 == value1:
                        continue
                    value2 = field.translate({val: src}.get, value1)
                    if value2 != value0:
                        raise ValidationError(_("Translation is not valid:\n%s", val))

    @api.model_create_multi
    def create(self, vals_list):
        records = super(IrTranslation, self.sudo()).create(vals_list).with_env(self.env)
        records.check('create')
        records._modified()
        # DLE P62: `test_translate.py`, `test_sync`
        self.flush()
        return records

    def write(self, vals):
        if vals.get('value'):
            vals.setdefault('state', 'translated')
        elif vals.get('src') or not vals.get('value', True):
            vals.setdefault('state', 'to_translate')
        self.check('write')
        result = super(IrTranslation, self.sudo()).write(vals)
        self.check('write')
        self._modified()
        # DLE P62: `test_translate.py`, `test_sync`
        # when calling `flush` with a field list, if there is no value for one of these fields,
        # the flush to database is not done.
        # this causes issues when changing the src/value of a translation, as when we read, we ask the flush,
        # but its not really the field which is in the towrite values, but its translation
        self.flush()
        return result

    def unlink(self):
        self.check('unlink')
        self._modified()
        return super(IrTranslation, self.sudo()).unlink()

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        # DLE P67, `test_new_fields.py`, `test_80_copy`
        # When assigning a translation to a field
        # e.g. email.with_context(lang='fr_FR').label = "bonjour"
        # and then search on translations for this translation, must flush as the translation has not yet been written in database
        if any(self.env[model]._fields[field].translate for model, ids in self.env.all.towrite.items() for record_id, fields in ids.items() for field in fields):
            self.flush()
        return super(IrTranslation, self)._search(args, offset=offset, limit=limit, order=order, count=count, access_rights_uid=access_rights_uid)

    @api.model
    def insert_missing(self, field, records):
        """ Insert missing translations for `field` on `records`. """
        records = records.with_context(lang=None)
        external_ids = records.get_external_id()  # if no xml_id, empty string
        if callable(field.translate):
            # insert missing translations for each term in src
            query = """ INSERT INTO ir_translation (lang, type, name, res_id, src, value, module, state)
                        SELECT l.code, 'model_terms', %(name)s, %(res_id)s, %(src)s, '', %(module)s, 'to_translate'
                        FROM res_lang l
                        WHERE l.active AND NOT EXISTS (
                            SELECT 1 FROM ir_translation
                            WHERE lang=l.code AND type='model' AND name=%(name)s AND res_id=%(res_id)s AND src=%(src)s
                        )
                        ON CONFLICT DO NOTHING;
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
            query = """ INSERT INTO ir_translation (lang, type, name, res_id, src, value, module, state)
                        SELECT l.code, 'model', %(name)s, %(res_id)s, %(src)s, '', %(module)s, 'to_translate'
                        FROM res_lang l
                        WHERE l.active AND NOT EXISTS (
                            SELECT 1 FROM ir_translation
                            WHERE lang=l.code AND type='model' AND name=%(name)s AND res_id=%(res_id)s
                        );

                        DELETE FROM ir_translation dup
                        WHERE type='model' AND name=%(name)s AND res_id=%(res_id)s
                            AND dup.id NOT IN (SELECT MAX(t.id)
                                       FROM ir_translation t
                                       WHERE t.lang=dup.lang AND type='model' AND name=%(name)s AND res_id=%(res_id)s
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
    def _upsert_translations(self, vals_list):
        """ Insert or update translations of type 'model' or 'model_terms'.

            This method is used for creations of translations where the given
            ``vals_list`` is trusted to be the right values and potential
            conflicts should be updated to the new given value.
            Mandatory values: name, lang, res_id, src, type
            The other keys are ignored during update if not present
        """
        rows_by_type = defaultdict(list)
        for vals in vals_list:
            rows_by_type[vals['type']].append((
                vals['name'], vals['lang'], vals['res_id'], vals['src'] or '', vals['type'],
                vals.get('module'), vals['value'] or '', vals.get('state'), vals.get('comments'),
            ))

        if rows_by_type['model']:
            query = """
                INSERT INTO ir_translation (name, lang, res_id, src, type,
                                            module, value, state, comments)
                VALUES {}
                ON CONFLICT (type, lang, name, res_id) WHERE type='model'
                DO UPDATE SET (name, lang, res_id, src, type, value, module, state, comments) =
                    (EXCLUDED.name, EXCLUDED.lang, EXCLUDED.res_id, EXCLUDED.src, EXCLUDED.type,
                     EXCLUDED.value,
                     COALESCE(EXCLUDED.module, ir_translation.module),
                     COALESCE(EXCLUDED.state, ir_translation.state),
                     COALESCE(EXCLUDED.comments, ir_translation.comments))
                WHERE EXCLUDED.value IS NOT NULL AND EXCLUDED.value != '';
            """.format(", ".join(["%s"] * len(rows_by_type['model'])))
            self.env.cr.execute(query, rows_by_type['model'])

        if rows_by_type['model_terms']:
            query = """
                INSERT INTO ir_translation (name, lang, res_id, src, type,
                                            module, value, state, comments)
                VALUES {}
                ON CONFLICT (type, name, lang, res_id, md5(src))
                DO UPDATE SET (name, lang, res_id, src, type, value, module, state, comments) =
                    (EXCLUDED.name, EXCLUDED.lang, EXCLUDED.res_id, EXCLUDED.src, EXCLUDED.type,
                     EXCLUDED.value, EXCLUDED.module, EXCLUDED.state, EXCLUDED.comments)
                WHERE EXCLUDED.value IS NOT NULL AND EXCLUDED.value != '';
            """.format(", ".join(["%s"] * len(rows_by_type['model_terms'])))
            self.env.cr.execute(query, rows_by_type['model_terms'])

    def _update_translations(self, vals_list):
        """ Update translations of type 'model' or 'model_terms'.

            This method is used for update of translations where the given
            ``vals_list`` is trusted to be the right values
            No new translation will be created
        """
        grouped_rows = {}
        for vals in vals_list:
            key = (vals['lang'], vals['type'], vals['name'])
            grouped_rows.setdefault(key, [vals['value'], vals['src'], vals['state'], []])
            grouped_rows[key][3].append(vals['res_id'])

        for where, values in grouped_rows.items():
            self._cr.execute(
                """ UPDATE ir_translation
                    SET value=%s,
                        src=%s,
                        state=%s
                    WHERE lang=%s AND type=%s AND name=%s AND res_id in %s
                """,
                (values[0], values[1], values[2], where[0], where[1], where[2], tuple(values[3]))
            )

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
            'name': _('Translate'),
            'res_model': 'ir.translation',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'view_id': self.env.ref('base.view_translation_dialog_tree').id,
            'target': 'current',
            'flags': {'search_view': True, 'action_buttons': True},
            'domain': domain,
            'context': {},
        }
        if field:
            fld = record._fields[field]
            if not fld.related:
                action['context'] = {
                    'search_default_name': "%s,%s" % (fld.model_name, fld.name),
                }
            else:
                rec = record
                try:
                    while fld.related:
                        rec, fld = fld.traverse_related(rec)
                    if rec:
                        action['context'] = {'search_default_name': "%s,%s" % (fld.model_name, fld.name),}
                except AccessError:
                    pass

            action['target'] = 'new'
            action['context']['translation_type'] = 'text' if fld.type in ['text', 'html'] else 'char'
            action['context']['translation_show_src'] = False
            if callable(fld.translate):
                action['view_id'] = self.env.ref('base.view_translation_lang_src_value_tree').id,
                action['context']['translation_show_src'] = True
            else:
                action['view_id'] = self.env.ref('base.view_translation_lang_value_tree').id,

        return action

    def _get_import_cursor(self, overwrite):
        """ Return a cursor-like object for fast inserting translations """
        return IrTranslationImport(self._cr, overwrite)

    def _load_module_terms(self, modules, langs, overwrite=False):
        """ Load PO files of the given modules for the given languages. """
        # load i18n files
        for module_name in modules:
            modpath = get_module_path(module_name)
            if not modpath:
                continue
            for lang in langs:
                lang_code = tools.get_iso_codes(lang)
                base_lang_code = None
                if '_' in lang_code:
                    base_lang_code = lang_code.split('_')[0]

                # Step 1: for sub-languages, load base language first (e.g. es_CL.po is loaded over es.po)
                if base_lang_code:
                    base_trans_file = get_module_resource(module_name, 'i18n', base_lang_code + '.po')
                    if base_trans_file:
                        _logger.info('module %s: loading base translation file %s for language %s', module_name, base_lang_code, lang)
                        tools.trans_load(self._cr, base_trans_file, lang, verbose=False, overwrite=overwrite)
                        overwrite = True  # make sure the requested translation will override the base terms later

                    # i18n_extra folder is for additional translations handle manually (eg: for l10n_be)
                    base_trans_extra_file = get_module_resource(module_name, 'i18n_extra', base_lang_code + '.po')
                    if base_trans_extra_file:
                        _logger.info('module %s: loading extra base translation file %s for language %s', module_name, base_lang_code, lang)
                        tools.trans_load(self._cr, base_trans_extra_file, lang, verbose=False, overwrite=overwrite)
                        overwrite = True  # make sure the requested translation will override the base terms later

                # Step 2: then load the main translation file, possibly overriding the terms coming from the base language
                trans_file = get_module_resource(module_name, 'i18n', lang_code + '.po')
                if trans_file:
                    _logger.info('module %s: loading translation file (%s) for language %s', module_name, lang_code, lang)
                    tools.trans_load(self._cr, trans_file, lang, verbose=False, overwrite=overwrite)
                elif lang_code != 'en_US':
                    _logger.info('module %s: no translation for language %s', module_name, lang_code)

                trans_extra_file = get_module_resource(module_name, 'i18n_extra', lang_code + '.po')
                if trans_extra_file:
                    _logger.info('module %s: loading extra translation file (%s) for language %s', module_name, lang_code, lang)
                    tools.trans_load(self._cr, trans_extra_file, lang, verbose=False, overwrite=overwrite)
        return True

    @api.model
    def get_technical_translations(self, model_name):
        """ Find the translations for the fields of `model_name`

        Find the technical translations for the fields of the model, including
        string, tooltip and available selections.

        :return: action definition to open the list of available translations
        """
        fields = self.env['ir.model.fields'].search([('model', '=', model_name)])
        selection_ids = tools.flatten([field.selection_ids.ids for field in fields if field.ttype == 'selection'])
        view = self.env.ref("base.view_translation_tree", False) or self.env['ir.ui.view']
        return {
            'name': _("Technical Translations"),
            'view_mode': 'tree',
            'views': [(view.id, "list")],
            'res_model': 'ir.translation',
            'type': 'ir.actions.act_window',
            'domain': [
                '&',
                    ('type', '=', 'model'),
                    '|',
                        '&', ('res_id', 'in', fields.ids),
                             ('name', 'like', 'ir.model.fields,'),
                        '&', ('res_id', 'in', selection_ids),
                             ('name', 'like', 'ir.model.fields.selection,')
            ],
        }

    @api.model
    def get_translations_for_webclient(self, mods, lang):
        if not mods:
            mods = [x['name'] for x in self.env['ir.module.module'].sudo().search_read(
                [('state', '=', 'installed')], ['name'])]
        if not lang:
            lang = self._context["lang"]
        langs = self.env['res.lang']._lang_get(lang)
        lang_params = None
        if langs:
            lang_params = {
                "name": langs.name,
                "direction": langs.direction,
                "date_format": langs.date_format,
                "time_format": langs.time_format,
                "grouping": langs.grouping,
                "decimal_point": langs.decimal_point,
                "thousands_sep": langs.thousands_sep,
                "week_start": langs.week_start,
            }
            lang_params['week_start'] = int(lang_params['week_start'])
            lang_params['code'] = lang

        # Regional languages (ll_CC) must inherit/override their parent lang (ll), but this is
        # done server-side when the language is loaded, so we only need to load the user's lang.
        translations_per_module = {}
        messages = self.env['ir.translation'].sudo().search_read([
            ('module', 'in', mods), ('lang', '=', lang),
            ('comments', 'like', 'openerp-web'), ('value', '!=', False),
            ('value', '!=', '')],
            ['module', 'src', 'value', 'lang'], order='module')
        for mod, msg_group in itertools.groupby(messages, key=operator.itemgetter('module')):
            translations_per_module.setdefault(mod, {'messages': []})
            translations_per_module[mod]['messages'].extend({
                'id': m['src'],
                'string': m['value']}
                for m in msg_group)

        return translations_per_module, lang_params

    @api.model
    @tools.ormcache('frozenset(mods)', 'lang')
    def get_web_translations_hash(self, mods, lang):
        translations, lang_params = self.get_translations_for_webclient(mods, lang)
        translation_cache = {
            'lang_parameters': lang_params,
            'modules': translations,
            'lang': lang,
            'multi_lang': len(self.env['res.lang'].sudo().get_installed()) > 1,
        }
        return hashlib.sha1(json.dumps(translation_cache, sort_keys=True).encode()).hexdigest()

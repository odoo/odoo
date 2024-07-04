# Part of Odoo. See LICENSE file for full copyright and licensing details.

from psycopg2.sql import SQL, Placeholder

from odoo import models, fields, api, tools
from odoo.osv.expression import AND, OR


# Avoid the need to find whether a record already exists before inserting.
INSERT_SQL = SQL("""
    INSERT INTO web_editor_edited (res_model, res_field, res_id)
    VALUES ({res_model}, {res_field}, {res_id})
    ON CONFLICT DO NOTHING
""").format(
    res_model=Placeholder('res_model'),
    res_field=Placeholder('res_field'),
    res_id=Placeholder('res_id'),
)

class EditedModel(models.Model):
    # This model is technical only - its records can only be accessed via sudo.

    _name = 'web_editor.edited'
    _description = "Website Edited Records"
    _log_access = False

    res_model = fields.Char('Model')
    res_field = fields.Char('Field')
    res_id = fields.Integer('Record Id')

    def init(self):
        # Ensure there is at most one active variant for each combination.
        query = """
            CREATE UNIQUE INDEX IF NOT EXISTS web_editor_edited_unique_index
            ON %s (res_model, res_field, res_id)
        """
        self.env.cr.execute(query % self._table)

    @api.model
    def _get_base_edited_html_fields(self):
        return [('ir.ui.view', 'arch_db', [('type', '=', 'qweb')])]

    @api.model
    def _get_edited_html_fields(self):
        """ Returns the list of fields that were tracked as edited.

            :return: list of (model name, field name, domain) tuples
        """
        all_edited = self.sudo().read_group(
            [], ['res_ids:array_agg(res_id)'],
            groupby=['res_model', 'res_field'], lazy=False,
        )
        result = self._get_base_edited_html_fields()
        result.extend([
            (edited['res_model'], edited['res_field'], [('id', 'in', edited['res_ids'])])
            for edited in all_edited
        ])
        return result

    @api.model
    def _track(self, res_model, res_field, res_id):
        # Only track HTML fields
        if self.env[res_model]._fields[res_field].type != 'html':
            return
        self.env.cr.execute(INSERT_SQL, {
            'res_model': res_model,
            'res_field': res_field,
            'res_id': res_id,
        })

    @api.model
    def _find_in_field(self, html_escaped_likes, model_name, field_name, base_domain):
        """ Returns models where the "likes" appear inside HTML fields or True
            if it appears inside non-accessible records.

            :param html_escaped_likes: array of string to include as values of
                domain 'like'. Values must be HTML escaped.
            :param model_name: name of the model
            :param field_name: name of the field
            :param base_domain: list of records to check (or all if unspecified)

            :return: matching records or True if matches are found in sudo or
                None if not found
        """
        if model_name not in self.env:
            # Do not fail if table was not cleaned after removing a module.
            return None
        matches = self.env[model_name]
        if field_name not in matches._fields:
            # Do not fail if table was not cleaned after removing a module.
            return None
        if matches._fields[field_name].type == 'binary':
            # Do not check binary fields with "like".
            return None
        likes = [[(field_name, 'like', like)] for like in html_escaped_likes]
        domain = AND([base_domain, OR(likes)])
        if matches.check_access_rights('read', raise_exception=False):
            matches = matches.with_context(active_test=False).search(domain)
            if matches:
                return matches
        sudo_matches = self.env[model_name].sudo().with_context(active_test=False).search(domain, limit=1)
        if sudo_matches:
            return True

    @api.model
    def _find(self, html_escaped_likes):
        """ Returns models where the "likes" appear inside HTML fields.

            :param html_escaped_likes: array of string to include as values of
                domain 'like'. Values must be HTML escaped.

            :return: None if no match or dict with
                - 'matches': matching records
                - 'sudo_models': list of non-accessible models containing
                matching records
        """
        all_matches = []
        sudo_models = []
        for model_name, field_name, domain in self._get_edited_html_fields():
            matches = self._find_in_field(html_escaped_likes, model_name, field_name, domain)
            if matches:
                if matches is True:
                    if model_name not in sudo_models:
                        sudo_models.append(model_name)
                else:
                    all_matches.append(matches)
        return {
            'matches': all_matches,
            'sudo_models': sudo_models,
        } if all_matches or sudo_models else None

    @api.model
    def _find_url(self, url, is_default_local_url=False):
        # in-document URLs are html-escaped, a straight search will not
        # find them
        url = tools.html_escape(url)
        likes = [
            f'"{url}"',
            f"'{url}'",
        ]
        if is_default_local_url:
            likes.extend([
                f'"{url}-',
                f"'{url}-",
                f'"{url}?',
                f"'{url}?",
            ])
        return self._find(likes)

    @api.model
    def _clean(self):
        # Called after field definitions have been uninstalled.
        # Build domain to find existing fields that are referenced in Edited.
        edited_fields_per_model = {}
        for res_model, res_field, _ in self._get_edited_html_fields():
            edited_fields_per_model.setdefault(res_model, set()).add(res_field)
        fields_domains = [[
            ('model', '=', model),
            ('name', 'in', list(edited_fields_per_model[model])),
        ] for model in edited_fields_per_model]
        fields_domain = OR(fields_domains)
        FieldsSudo = self.env['ir.model.fields'].sudo()
        fields = FieldsSudo.search(fields_domain)
        # Build domain to find Edited that have no associated field.
        for field in fields:
            model_fields = edited_fields_per_model[field.model]
            model_fields.remove(field.name)
            if not model_fields:
                edited_fields_per_model.pop(field.model)
        unlink_domains = [[
            ('res_model', '=', model),
            ('res_field', 'in', list(edited_fields_per_model[model])),
        ] for model in edited_fields_per_model]
        if unlink_domains:
            self.sudo().search(OR(unlink_domains)).unlink()

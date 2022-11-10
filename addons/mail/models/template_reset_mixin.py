# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from lxml import etree

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
from odoo.modules import get_module_resource
from odoo.modules.module import get_resource_from_path, get_resource_path
from odoo.tools.convert import xml_import
from odoo.tools.misc import file_open
from odoo.tools.translate import TranslationImporter


class TemplateResetMixin(models.AbstractModel):
    _name = "template.reset.mixin"
    _description = 'Template Reset Mixin'

    template_fs = fields.Char(
        string='Template Filename', copy=False,
        help="""File from where the template originates. Used to reset broken template.""")

    # -------------------------------------------------------------------------
    # OVERRIDE METHODS
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'template_fs' not in vals and 'install_filename' in self.env.context:
                # we store the relative path to the resource instead of the absolute path, if found
                # (it will be missing e.g. when importing data-only modules using base_import_module)
                path_info = get_resource_from_path(self.env.context['install_filename'])
                if path_info:
                    vals['template_fs'] = '/'.join(path_info[0:2])
        return super().create(vals_list)

    def _load_records_write(self, values):
        # OVERRIDE to make the fields blank that are not present in xml record
        if self.env.context.get('reset_template'):
            # We don't want to change anything for magic columns, values present in XML record, and 'template_fs'
            fields_in_xml_record = values.keys()
            fields_not_to_touch = set(models.MAGIC_COLUMNS) | fields_in_xml_record | {'template_fs'}
            fields_to_empty = self._fields.keys() - fields_not_to_touch
            # For the fields not defined in xml record, if they have default values, we should not
            # enforce empty values for them and the default values should be kept
            field_defaults = self.default_get(list(fields_to_empty))
            # Update the values to be written and include the default values, prevent fields with
            # default values from being empty
            values.update(field_defaults)
            fields_to_empty = fields_to_empty - set(field_defaults.keys())
            # Finally, update the values with fields that should be empty
            values.update(dict.fromkeys(fields_to_empty, False))
        return super()._load_records_write(values)

    # -------------------------------------------------------------------------
    # RESET TEMPLATE
    # -------------------------------------------------------------------------

    def _override_translation_term(self, module_name, xml_ids):
        translation_importer = TranslationImporter(self.env.cr)

        for code, _ in self.env['res.lang'].get_installed():
            lang_code = tools.get_iso_codes(code)
            # In case of sub languages (e.g fr_BE), load the base language first, (e.g fr.po) and
            # then load the main translation file (e.g fr_BE.po)

            # Step 1: reset translation terms with base language file
            if '_' in lang_code:
                base_lang_code = lang_code.split('_')[0]
                base_trans_file = get_module_resource(module_name, 'i18n', base_lang_code + '.po')
                if base_trans_file:
                    translation_importer.load_file(base_trans_file, code, xmlids=xml_ids)

            # Step 2: reset translation file with main language file (can possibly override the
            # terms coming from the base language)
            trans_file = get_module_resource(module_name, 'i18n', lang_code + '.po')
            if trans_file:
                translation_importer.load_file(trans_file, code, xmlids=xml_ids)

        translation_importer.save(overwrite=True, force_overwrite=True)

    def reset_template(self):
        """Resets the Template with values given in source file. We ignore the case of
        template being overridden in another modules because it is extremely less likely
        to happen. This method also tries to reset the translation terms for the current
        user lang (all langs are not supported due to costly file operation). """
        expr = "//*[local-name() = $tag and (@id = $xml_id or @id = $external_id)]"
        templates_with_missing_source = []
        for template in self.filtered('template_fs'):
            external_id = template.get_external_id().get(template.id)
            module, xml_id = external_id.split('.')
            fullpath = get_resource_path(*template.template_fs.split('/'))
            if fullpath:
                doc = etree.parse(fullpath)
                for rec in doc.xpath(expr, tag='record', xml_id=xml_id, external_id=external_id):
                    # We don't have a way to pass context while loading record from a file, so we use this hack
                    # to pass the context key that is needed to reset the fields not available in data file
                    rec.set('context', json.dumps({'reset_template': 'True'}))
                    obj = xml_import(template.env.cr, module, {}, mode='init', xml_filename=fullpath)
                    obj._tag_record(rec)
                    template._override_translation_term(module, [xml_id, external_id])
            else:
                templates_with_missing_source.append(template.display_name)
        if templates_with_missing_source:
            raise UserError(_("The following email templates could not be reset because their related source files could not be found:\n- %s", "\n- ".join(templates_with_missing_source)))

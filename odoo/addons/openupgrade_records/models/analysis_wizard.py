# coding: utf-8
# Copyright 2011-2015 Therp BV <https://therp.nl>
# Copyright 2016 Opener B.V. <https://opener.am>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import os
from odoo.modules import get_module_path

from odoo import api, fields, models
from odoo.addons.openupgrade_records.lib import compare


class AnalysisWizard(models.TransientModel):
    _name = 'openupgrade.analysis.wizard'
    _description = 'OpenUpgrade Analysis Wizard'
    server_config = fields.Many2one(
        'openupgrade.comparison.config',
        'Configuration', required=True)
    state = fields.Selection(
            [('init', 'Init'), ('ready', 'Ready')],
            readonly=True, default='init')
    log = fields.Text()
    write_files = fields.Boolean(
        help='Write analysis files to the module directories',
        default=True)

    @api.multi
    def get_communication(self):
        """
        Retrieve both sets of database representations,
        perform the comparison and register the resulting
        change set
        """

        def write_file(module, version, contents,
                       filename='openupgrade_analysis.txt'):
            module_path = get_module_path(module)
            if not module_path:
                return "ERROR: could not find module path:\n"
            full_path = os.path.join(
                module_path, 'migrations', version)
            if not os.path.exists(full_path):
                try:
                    os.makedirs(full_path)
                except os.error:
                    return "ERROR: could not create migrations directory:\n"
            logfile = os.path.join(full_path, filename)
            try:
                f = open(logfile, 'w')
            except Exception:
                return "ERROR: could not open file %s for writing:\n" % logfile
            f.write(contents)
            f.close()
            return None

        self.ensure_one()
        connection = self.server_config.get_connection()
        remote_record_obj = connection.get_model('openupgrade.record')
        local_record_obj = self.env['openupgrade.record']

        # Retrieve field representations and compare
        remote_records = remote_record_obj.field_dump()
        local_records = local_record_obj.field_dump()
        res = compare.compare_sets(remote_records, local_records)

        # Retrieve xml id representations and compare
        fields = ['module', 'model', 'name']
        local_xml_records = [
            dict([(field, record[field]) for field in fields])
            for record in local_record_obj.search([('type', '=', 'xmlid')])]
        remote_xml_record_ids = remote_record_obj.search(
            [('type', '=', 'xmlid')])
        remote_xml_records = [
            dict([(field, record[field]) for field in fields])
            for record in remote_record_obj.read(
                remote_xml_record_ids, fields)
        ]
        res_xml = compare.compare_xml_sets(
            remote_xml_records, local_xml_records)

        affected_modules = list(
            set(record['module'] for record in
                remote_records + local_records +
                remote_xml_records + local_xml_records
                ))

        # reorder and output the result
        keys = ['general'] + affected_modules
        modules = dict(
            (module['name'], module)
            for module in self.env['ir.module.module'].search(
                [('state', '=', 'installed')]))
        general = ''
        for key in keys:
            contents = "---Fields in module '%s'---\n" % key
            if key in res:
                contents += '\n'.join(
                    [unicode(line) for line in sorted(res[key])])
                if res[key]:
                    contents += '\n'
            contents += "---XML records in module '%s'---\n" % key
            if key in res_xml:
                contents += '\n'.join([unicode(line) for line in res_xml[key]])
                if res_xml[key]:
                    contents += '\n'
            if key not in res and key not in res_xml:
                contents += '-- nothing has changed in this module'
            if key == 'general':
                general += contents
                continue
            if key not in modules:
                general += (
                    "ERROR: module not in list of installed modules:\n" +
                    contents)
                continue
            if self.write_files:
                error = write_file(
                    key, modules[key].installed_version, contents)
                if error:
                    general += error
                    general += contents
            else:
                general += contents

        # Store the general log in as many places as possible ;-)
        if self.write_files and 'base' in modules:
            write_file(
                'base', modules['base'].installed_version, general,
                'openupgrade_general_log.txt')
        self.server_config.write({'last_log': general})
        self.write({'state': 'ready', 'log': general})

        return {
            'name': self._description,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': self._name,
            'type': 'ir.actions.act_window',
            'res_id': self.id,
        }

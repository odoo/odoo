# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2008-2012 NaN Projectes de Programari Lliure, S.L.
#                         http://www.NaN-tic.com
# Copyright (c) 2012 Omar Castiñeira Saavedra <omar@pexego.es>
#                         Pexego Sistemas Informáticos http://www.pexego.es
# Copyright (C) 2013 Tadeus Prastowo <tadeus.prastowo@infi-nity.com>
#                         Vikasa Infinity Anugrah <http://www.infi-nity.com>
# Copyright (C) 2019-Today Serpent Consulting Services Pvt. Ltd.
#                         (<http://www.serpentcs.com>)
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

import os
import csv
import base64
import tempfile
import codecs
import logging
from xml.dom.minidom import getDOMImplementation

from odoo.osv import orm

from .abstract_data_generator import AbstractDataGenerator


class BrowseDataGenerator(AbstractDataGenerator):
    def __init__(self, report, model, env, cr, uid, ids, context):
        self.report = report
        self.model = model
        self.env = env
        self.cr = cr
        self.uid = uid
        self.ids = ids
        self._context = context
        self._languages = []
        self.image_files = {}
        self.temporary_files = []
        self.logger = logging.getLogger(__name__)

    def warning(self, message):
        if self.logger:
            self.logger.warning("%s" % message)

    def languages(self):
        if self._languages:
            return self._languages
        languages = self.env['res.lang'].search([('translatable', '=', '1')])
        self._languages = languages.mapped('code')
        return self._languages

    def value_in_all_languages(self, model, id, field):
        context = self.env.context.copy()
        model = self.env[model]
        values = {}

        for language in self.languages():
            if language == 'en_US':
                context.update({'lang': False})
            else:
                context.update({'lang': language})
            values[language] = model.browse(id).mapped(field)
            if model._fields[field].type == 'selection' and \
                    model._fields[field].selection:
                field_data = model.with_context(context).\
                    fields_get(allfields=[field])
                values[language] = dict(field_data[field]['selection']).get(
                    values[language][0], values[language][0])
        result = []
        for key, value in values.items():
            result.append('%s~%s' % (key, value))
        return '|'.join(result)

    def generate_ids(self, record, relations, path, current_records):
        unrepeated = set([field.partition('/')[0] for field in relations])
        for relation in unrepeated:
            root = relation.partition('/')[0]
            if path:
                current_path = '%s/%s' % (path, root)
            else:
                current_path = root

            if root == 'Attachments':
                value = self.env['ir.attachment'].search([
                    ('res_model', '=', record._name),
                    ('res_id', '=', record.id)])

            elif root == 'User':
                value = self.env['res.users'].browse([self.uid])
            else:
                if root == 'id':
                    value = record.id
                elif hasattr(record, root):
                    value = getattr(record, root)
                else:
                    warning = "Field '%s' does not exist in model '%s'."
                    self.warning(warning % (root, record._name))
                    continue

                if isinstance(value, orm.browse_record):
                    relations2 = [
                        field.partition('/')[2] for field in relations
                        if field.partition('/')[0] == root and
                        field.partition('/')[2]]
                    return self.generate_ids(
                        value, relations2, current_path, current_records)

                if not isinstance(value, orm.browse_record_list):
                    wrng2 = "Field '%s' in model '%s' is not a relation field."
                    self.warning(wrng2 % (root, self.model))
                    return current_records

            # Only join if there are any records because it's a LEFT JOIN
            # If we wanted an INNER JOIN we wouldn't check for "value" and
            # return an empty current_records
            if value:
                # Only
                new_records = []
                for v in value:
                    current_new_records = []

                    for rec_id in current_records:
                        new = rec_id.copy()
                        new[current_path] = v
                        current_new_records.append(new)

                    relations2 = [
                        field.partition('/')[2] for field in relations
                        if field.partition('/')[0] == root and
                        field.partition('/')[2]]
                    new_records += self.generate_ids(
                        v, relations2, current_path, current_new_records)

                current_records = new_records
        return current_records


class XmlBrowseDataGenerator(BrowseDataGenerator):
    def __init__(self, report, model, env, cr, uid, ids, context):
        super(XmlBrowseDataGenerator, self).__init__(
            report, model, env, cr, uid, ids, context)
        self.all_records = []
        self.document = None

    # XML file generation works as follows:
    # By default (if no ODOO_RELATIONS property exists in the report)
    # a record will be created for each model id we've been asked to show.
    # If there are any elements in the ODOO_RELATIONS list,
    # they will imply a LEFT JOIN like behaviour on the rows to be shown.
    def generate(self, file_name):
        self.all_records = []
        relations = self.report.relations
        # The following loop generates one entry to all_records list
        # for each record that will be created. If there are any relations
        # it acts like a LEFT JOIN against the main model/table.
        for record in self.env[self.model].browse(self.ids):

            new_records = self.generate_ids(
                record, relations, '', [{'root': record}])
            copies = 1
            if self.report.copies_field and \
                    record.__hasattr__(self.report.copies_field):
                copies = int(record.__getattr__(self.report.copies_field))
            for new in new_records:
                for x in range(copies):
                    self.all_records.append(new)

        # Once all records have been calculated, create the
        # XML structure itself
        self.document = getDOMImplementation().createDocument(
            None, 'data', None)
        top_node = self.document.documentElement
        for records in self.all_records:
            record_node = self.document.createElement('record')
            top_node.appendChild(record_node)
            self.generate_xml_record(
                records['root'], records, record_node, '', self.report.fields)

        # Once created, the only missing step is to store the XML into a file
        with codecs.open(file_name, 'wb+', 'utf-8') as f:
            top_node.writexml(f)

    def generate_xml_record(self, record, records, record_node, path, fields):
        # One field (many2one, many2many or one2many) can appear several times.
        # Process each "root" field only once by using a set.
        unrepeated = set([field.partition('/')[0] for field in fields])

        for field in unrepeated:
            root = field.partition('/')[0]
            if path:
                current_path = '%s/%s' % (path, root)
            else:
                current_path = root
            field_node = self.document.createElement(root)
            record_node.appendChild(field_node)

            if root == 'Attachments':
                value = self.env['ir.attachment'].search(
                    [('res_model', '=', record._name),
                     ('res_id', '=', record.id)])

            elif root == 'User':
                value = self.env.user
            else:
                if root == 'id':
                    value = record.id
                elif hasattr(record, root):
                    value = getattr(record, root)
                else:
                    value = None
                    wrng4 = "Field '%s' does not exist in model '%s'."
                    self.warning(wrng4 % (root, record._name))

            # Check if it's a many2one
            if isinstance(value, orm.browse_record):
                fields2 = [f.partition('/')[2] for f in fields
                           if f.partition('/')[0] == root]
                self.generate_xml_record(
                    value, records, field_node, current_path, fields2)
                continue

            # Check if it's a one2many or many2many
            if isinstance(value, orm.browse_record_list):
                if not value:
                    continue

                fields2 = [f.partition('/')[2] for f in fields
                           if f.partition('/')[0] == root]
                if current_path in records:
                    self.generate_xml_record(
                        records[current_path], records,
                        field_node, current_path, fields2)
                else:
                    # If the field is not marked to be iterated use
                    # the first record only
                    self.generate_xml_record(
                        value[0], records, field_node, current_path, fields2)
                continue

            if field in record._fields:
                field_type = record._fields[field].type

            # The rest of field types must be converted into str
            if field == 'id':
                # Check for field 'id' because we can't find it's
                # type in _columns
                value = str(value)
            elif value is False:
                value = ''
            elif field_type == 'date':
                value = '%s 00:00:00' % str(value)
            elif field_type == 'binary':
                image_id = (record.id, field)
                if image_id in self.image_files:
                    file_name = self.image_files[image_id]
                else:
                    fd, file_name = tempfile.mkstemp()
                    try:
                        os.write(fd, base64.decodestring(value))
                    finally:
                        os.close(fd)
                    self.temporary_files.append(file_name)
                    self.image_files[image_id] = file_name
                value = file_name

            elif isinstance(value, str):
                value = str(value, 'utf-8')
            elif isinstance(value, float):
                value = '%.10f' % value
            elif not isinstance(value, str):
                value = str(value)

            value_node = self.document.createTextNode(value)
            field_node.appendChild(value_node)


class CsvBrowseDataGenerator(BrowseDataGenerator):
    # CSV file generation works as follows:
    # By default (if no ODOO_RELATIONS property exists in the report)
    # a record will be created for each model id we've been asked to show.
    # If there are any elements in the ODOO_RELATIONS list,
    # they will imply a LEFT JOIN like behaviour on the rows to be shown.
    def generate(self, file_name):
        self.all_records = []
        relations = self.report.relations

        # The following loop generates one entry to allRecords list
        # for each record that will be created. If there are any relations
        # it acts like a LEFT JOIN against the main model/table.
        reportCopies = self.report.copies or 1
        sequence = 0
        copiesField = self.report.copies_field
        for record in self.env[self.model].browse(self.ids):
            newRecords = self.generate_ids(
                record, relations, '', [{'root': record}])
            copies = reportCopies
            if copiesField and record.__hasattr__(copiesField):
                copies = copies * int(record.__getattr__(copiesField))
            sequence += 1
            subsequence = 0
            for new in newRecords:
                new['sequence'] = sequence
                new['subsequence'] = subsequence
                subsequence += 1
                for x in range(copies):
                    new['copy'] = x
                    self.all_records.append(new.copy())
        with open(file_name, 'w') as csvfile:
            fieldnames = self.report.field_names + ['']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            # writer.writeheader() #header should only printed from jrxml file.
            header = {}
            for field in self.report.field_names + ['']:
                header[field] = field
            writer.writerow(header)

            # Once all records have been calculated,
            # create the CSV structure itself
            for records in self.all_records:
                row = {}
                self.generateCsvRecord(
                    records['root'], records, row, '',
                    self.report.fields,
                    records['sequence'],
                    records['subsequence'],
                    records['copy'])

                writer.writerow(row)

    def generateCsvRecord(self, record, records, row, path, fields, sequence,
                          subsequence, copy):
        # One field (many2one, many2many or one2many) can appear several times
        # Process each "root" field only once by using a set.
        unrepeated = set([field.partition('/')[0] for field in fields])

        for field in unrepeated:
            root = field.partition('/')[0]
            current_path = root
            if path:
                current_path = '%s/%s' % (path, root)

            if root == 'Attachments':
                value = self.env['ir.attachment'].search(
                    [('res_model', '=', record._name),
                     ('res_id', '=', record.id)])

            elif root == 'User':
                value = self.env['res.users'].browse(self.uid)
            elif root == 'Special':
                fields2 = [f.partition('/')[2] for f in fields
                           if f.partition('/')[0] == root]

                for f in fields2:
                    p = '%s/%s' % (current_path, f)
                    if f == 'sequence':
                        row[self.report.fields[p]['name']] = sequence
                    elif f == 'subsequence':
                        row[self.report.fields[p]['name']] = subsequence
                    elif f == 'copy':
                        row[self.report.fields[p]['name']] = copy
                continue
            else:
                if root == 'id':
                    value = record.id
                elif hasattr(record, root):
                    value = getattr(record, root)
                else:
                    value = None
                    if root:
                        wrng6 = ("Field '%s' (path: %s) does"
                                 "not exist in model '%s'.")
                        self.warning(
                            wrng6 % (root, current_path, record._name))

            # Check if it's a many2one
            if isinstance(value, orm.browse_record):
                fields2 = [f.partition('/')[2] for f in fields
                           if f.partition('/')[0] == root]
                self.generateCsvRecord(
                    value, records, row, current_path,
                    fields2, sequence, subsequence, copy)
                continue

            # Check if it's a one2many or many2many
            if isinstance(value, orm.browse_record_list):
                if not value:
                    continue
                fields2 = [f.partition('/')[2] for f in fields
                           if f.partition('/')[0] == root]
                if current_path in records:
                    self.generateCsvRecord(
                        records[current_path], records, row,
                        current_path, fields2, sequence, subsequence, copy)
                else:
                    # If the field is not marked to be iterated
                    # use the first record only
                    self.generateCsvRecord(
                        value[0], records, row,
                        current_path, fields2, sequence, subsequence, copy)
                continue

            # The field might not appear in the self.report.fields
            # only when the field is a many2one but in this case it's null.
            # This will make the path to look like: "journal_id",
            # when the field actually in the report is "journal_id/name",
            # for example.In order not to change the way we detect many2one
            # fields, we simply check that the field is in self.report.
            # fields() and that's it.
            if current_path not in self.report.fields:
                continue

            # Show all translations for a field
            type = self.report.fields[current_path]['type']
            if type == 'java.lang.Object' and record.id:
                value = self.value_in_all_languages(
                    record._name, record.id, root)

            if field in record._fields:
                field_type = record._fields[field].type

            # The rest of field types must be converted into str
            if field == 'id':
                # Check for field 'id' because we can't find it's
                # type in _columns
                value = str(value)
            elif value in (False, None):
                value = ''
            elif field_type == 'date':
                value = '%s 00:00:00' % str(value)
            elif field_type == 'binary':

                image_id = (record.id, field)

                if image_id in self.image_files:
                    file_name = self.image_files[image_id]
                else:
                    fd, file_name = tempfile.mkstemp()
                    try:
                        os.write(fd, base64.decodestring(value))
                    finally:
                        os.close(fd)
                    self.temporary_files.append(file_name)
                    self.image_files[image_id] = file_name
                value = file_name
            elif isinstance(value, str):
                value = value
            elif isinstance(value, float):
                value = '%.10f' % value
            elif not isinstance(value, str):
                value = str(value)
            row[self.report.fields[current_path]['name']] = value

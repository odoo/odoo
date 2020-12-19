# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2008-2012 NaN Projectes de Programari Lliure, S.L.
#                         http://www.NaN-tic.com
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
from lxml import etree
import re

try:
    from tools.safe_eval import safe_eval
    import tools
except ImportError:
    from odoo.tools.safe_eval import safe_eval
    from odoo import tools

DATA_SOURCE_EXPRESSION_REG_EXP = re.compile(r"""\$P\{(\w+)\}""")


class JasperReport:
    def __init__(self, file_name='', path_prefix=''):
        self.report_path = file_name
        self.path_prefix = path_prefix.strip()

        if self.path_prefix and self.path_prefix[-1] != '/':
            self.path_prefix += '/'

        self.language = 'xpath'
        self.relations = []
        self.fields = {}
        self.field_names = []
        self.subreports = []
        self.datasets = []
        self.copies = 1
        self.copies_field = False
        self.is_header = False
        if file_name:
            self.extract_properties()

    def subreport_directory(self):
        return os.path.join(os.path.abspath(
            os.path.dirname(self.report_path)), '')

    def standard_directory(self):
        jasperdir = tools.config.get('jasperdir')
        if jasperdir:
            if jasperdir.endswith(os.sep):
                return jasperdir
            else:
                return os.path.join(jasperdir, '')
        return os.path.join(
            os.path.abspath(os.path.dirname(__file__)), '..', 'report', '')

    def extract_fields(self, field_tags, ns):
        # fields and fieldNames
        fields = {}
        field_names = []
        for tag in field_tags:
            name = tag.get('name')
            type = tag.get('class')
            path = tag.findtext('{%s}fieldDescription' % ns, '').strip()
            # Make the path relative if it isn't already
            if path.startswith('/data/record/'):
                path = self.path_prefix + path[13:]

            # Remove language specific data from the path so:
            # Empresa-partner_id/Nom-name becomes partner_id/name
            # We need to consider the fact that the name in user's language
            # might not exist, hence the easiest thing to do is split and [-1]
            new_path = [x.split('-')[-1] for x in path.split('/')]

            path = '/'.join(new_path)
            fields[path] = {
                'name': name,
                'type': type,
            }
            field_names.append(name)

        return fields, field_names

    def extract_properties(self):
        # The function will read all relevant information from the jrxml file

        doc = etree.parse(self.report_path)

        # Define namespaces
        ns = 'http://jasperreports.sourceforge.net/jasperreports'
        nss = {'jr': ns}

        # Language
        # is XPath.
        lang_tags = doc.xpath(
            '/jr:jasperReport/jr:queryString', namespaces=nss)
        if lang_tags:
            if lang_tags[0].get('language'):
                self.language = lang_tags[0].get('language').lower()

        # Relations
        ex_path = '/jr:jasperReport/jr:property[@name="ODOO_RELATIONS"]'
        relation_tags = doc.xpath(ex_path, namespaces=nss)

        if relation_tags and 'value' in relation_tags[0].keys():
            relation = relation_tags[0].get('value').strip()
            self.relations = [x.strip() for x in relation.split(',')]
            if relation.startswith('['):
                self.relations = safe_eval(relation_tags[0].get('value'), {})
            self.relations = [self.path_prefix + x for x in self.relations]

        if not self.relations and self.path_prefix:
            self.relations = [self.path_prefix[:-1]]

        # Repeat field
        path1 = '/jr:jasperReport/jr:property[@name="ODOO_COPIES_FIELD"]'
        copies_field_tags = doc.xpath(path1, namespaces=nss)
        if copies_field_tags and 'value' in copies_field_tags[0].keys():
            self.copies_field = (
                self.path_prefix + copies_field_tags[0].get('value'))

        # Repeat
        path2 = '/jr:jasperReport/jr:property[@name="ODOO_COPIES"]'
        copies_tags = doc.xpath(path2, namespaces=nss)
        if copies_tags and 'value' in copies_tags[0].keys():
            self.copies = int(copies_tags[0].get('value'))

        self.is_header = False
        path3 = '/jr:jasperReport/jr:property[@name="ODOO_HEADER"]'
        header_tags = doc.xpath(path3, namespaces=nss)
        if header_tags and 'value' in header_tags[0].keys():
            self.is_header = True

        field_tags = doc.xpath('/jr:jasperReport/jr:field', namespaces=nss)
        self.fields, self.field_names = self.extract_fields(field_tags, ns)

        # Subreports
        # Here we expect the following structure in the .jrxml file:
        # <subreport>
        #  <dataSourceExpression><![CDATA[$P{REPORT_DATA_SOURCE}]]>
        # </dataSourceExpression>
        # <subreportExpression class="java.lang.String">
        # <![CDATA[$P{STANDARD_DIR} + "report_header.jasper"]]>
        # </subreportExpression>
        # </subreport>

        subreport_tags = doc.xpath('//jr:subreport', namespaces=nss)

        for tag in subreport_tags:
            text1 = '{%s}dataSourceExpression'
            data_source_expression = tag.findtext(text1 % ns, '')

            if not data_source_expression:
                continue

            data_source_expression = data_source_expression.strip()
            m = DATA_SOURCE_EXPRESSION_REG_EXP.match(data_source_expression)

            if not m:
                continue

            data_source_expression = m.group(1)
            if data_source_expression == 'REPORT_DATA_SOURCE':
                continue

            subreport_expression = tag.findtext(
                '{%s}subreportExpression' % ns, '')
            if not subreport_expression:
                continue
            subreport_expression = subreport_expression.strip()
            subreport_expression = (
                subreport_expression.replace
                ('$P{STANDARD_DIR}', '"%s"' % self.standard_directory()))
            subreport_expression = (
                subreport_expression.replace
                ('$P{SUBREPORT_DIR}', '"%s"' % self.subreport_directory()))
            try:
                subreport_expression = safe_eval(subreport_expression, {})
            except Exception:
                continue
            if subreport_expression.endswith('.jasper'):
                subreport_expression = subreport_expression[:-6] + 'jrxml'

            # Model
            model = ''
            path4 = '//jr:reportElement/jr:property[@name="ODOO_MODEL"]'
            model_tags = tag.xpath(path4, namespaces=nss)
            if model_tags and 'value' in model_tags[0].keys():
                model = model_tags[0].get('value')

            path_prefix = ''
            pat = '//jr:reportElement/jr:property[@name="ODOO_PATH_PREFIX"]'
            path_prefix_tags = tag.xpath(pat, namespaces=nss)
            if path_prefix_tags and 'value' in path_prefix_tags[0].keys():
                path_prefix = path_prefix_tags[0].get('value')

            self.is_header = False
            path5 = '//jr:reportElement/jr:property[@name="ODOO_HEADER"]'
            header_tags = tag.xpath(path5, namespaces=nss)

            if header_tags and 'value' in header_tags[0].keys():
                self.is_header = True

            # Add our own path_prefix to subreport's path_prefix
            sub_prefix = []

            if self.path_prefix:
                sub_prefix.append(self.path_prefix)
            if path_prefix:
                sub_prefix.append(path_prefix)

            sub_prefix = '/'.join(sub_prefix)

            subreport = JasperReport(subreport_expression, sub_prefix)

            self.subreports.append({
                'parameter': data_source_expression,
                'filename': subreport_expression,
                'model': model,
                'pathPrefix': path_prefix,
                'report': subreport,
                'depth': 1})
            for subsub_info in subreport.subreports:
                subsub_info['depth'] += 1
                # Note hat 'parameter' (the one used to pass report's
                # DataSource) must be the same in all reports
                self.subreports.append(subsub_info)

        # Dataset
        # Here we expect the following structure in the .jrxml file:
        # <datasetRun>
        #  <dataSourceExpression><![CDATA[$P{REPORT_DATA_SOURCE}]]>
        # </dataSourceExpression>
        # </datasetRun>

        dataset_tags = doc.xpath('//jr:datasetRun', namespaces=nss)

        for tag in dataset_tags:
            path7 = '{%s}dataSourceExpression'
            data_source_expression = tag.findtext(path7 % ns, '')
            if not data_source_expression:
                continue
            data_source_expression = data_source_expression.strip()
            m = DATA_SOURCE_EXPRESSION_REG_EXP.match(data_source_expression)
            if not m:
                continue
            data_source_expression = m.group(1)
            if data_source_expression == 'REPORT_DATA_SOURCE':
                continue
            sub_dataset_name = tag.get('subDataset')
            if not sub_dataset_name:
                continue

            # Relations
            relations = []
            path8 = \
                '../../jr:reportElement/jr:property[@name="ODOO_RELATIONS"]'
            relation_tags = tag.xpath(path8, namespaces=nss)

            if relation_tags and 'value' in relation_tags[0].keys():
                relation = relation_tags[0].get('value').strip()

                if relation.startswith('['):
                    relations = safe_eval(relation_tags[0].get('value'), {})
                else:
                    relations = [x.strip() for x in relation.split(',')]

                relations = [self.path_prefix + x for x in relations]

            if not relations and self.path_prefix:
                relations = [self.path_prefix[:-1]]

            # Repeat field
            copies_field = None
            path9 = ('../../jr:reportElement/jr:property'
                     '[@name="ODOO_COPIES_FIELD"]')
            copies_field_tags = tag.xpath(path9, namespaces=nss)
            if copies_field_tags and 'value' in copies_field_tags[0].keys():
                copies_field = \
                    self.path_prefix + copies_field_tags[0].get('value')

            # Repeat
            copies = None
            path11 = \
                '../../jr:reportElement/jr:property[@name="ODOO_COPIES"]'
            copies_tags = tag.xpath(path11, namespaces=nss)
            if copies_tags and 'value' in copies_tags[0].keys():
                copies = int(copies_tags[0].get('value'))

            # Model
            model = ''
            path12 = \
                '../../jr:reportElement/jr:property[@name="ODOO_MODEL"]'
            model_tags = tag.xpath(path12, namespaces=nss)
            if model_tags and 'value' in model_tags[0].keys():
                model = model_tags[0].get('value')

            path_prefix = ''
            path13 = ('../../jr:reportElement/jr:property'
                      '[@name="ODOO_PATH_PREFIX"]')
            path_prefix_tags = tag.xpath(path13, namespaces=nss)

            if path_prefix_tags and 'value' in path_prefix_tags[0].keys():
                path_prefix = path_prefix_tags[0].get('value')

            # We need to find the appropriate subDataset definition
            # for this dataset run.
            path14 = '//jr:subDataset[@name="%s"]'
            sub_dataset = doc.xpath(
                path14 % sub_dataset_name, namespaces=nss)[0]
            field_tags = sub_dataset.xpath('jr:field', namespaces=nss)
            fields, field_names = self.extract_fields(field_tags, ns)

            dataset = JasperReport()
            dataset.fields = fields
            dataset.field_names = field_names
            dataset.relations = relations
            dataset.copies_field = copies_field
            dataset.copies = copies
            self.subreports.append({
                'parameter': data_source_expression,
                'model': model,
                'pathPrefix': path_prefix,
                'report': dataset,
                'filename': 'DATASET',
            })

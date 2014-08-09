# -*- coding: utf-8 -*-
{
    'name': "Marcos DGII",
    'description': "Generador de reporte para la DGII",
    'category': 'Hidden',
    'depends': ['base'],
    'depends': ['web', 'account', 'point_of_sale'],
    'data': [
        'marcos_dgii_view.xml',
        'wizard/marcos_z_report_view.xml'],
    'js': ['static/src/js/marcos_dgii.js'],
    'css': ['static/src/css/marcos_dgii.css'],
    'qweb': ['static/src/xml/marcos_dgii.xml'],
}

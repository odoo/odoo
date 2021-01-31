# -*- encoding: utf-8 -*-
{
    'name': "Row Number in tree/list view",
    'version': '14.0.1.0',
    'summary': 'Show row number in tree/list view.',
    'category': 'Other',
    'description': """By installing this module, user can see row number in Odoo backend tree view. sequence in list, Numbering List View, row count, row counting, show count list, list view row count, number in row, rij nummer, номер строки, numéro de ligne, Zeilennummer, numero de fila, رقم الصف , nomor baris, ListView Row Count,list view row number, number in list view, tree row number, tree view row number, list view row number, dynamic sequence, dynamic row number, line sequence, sequence in report, record count, dynamic list view, dynamic tree view, dynamic listview, listview advance, list editor, list row sequence, backup, sticky, document, list view number, listview number, list number, tree number, treeview number, stick list, row number report, sequence number, sequencial number, number in list, dynamic number""",
    'author': 'Nilesh Sheliya',
    "depends" : ['web'],
    "live_test_url": "https://odoo.sheliyainfotech.com/contactus?description=demo:rowno_in_tree&odoo_version=14.0",
    'data': [
             'views/listview_templates.xml',
             ],
    "images": ["static/description/screen1.png"],
    'license': 'LGPL-3',
    'qweb': [
            ],  
    
    'installable': True,
    'application'   : True,
    'auto_install'  : False,
}

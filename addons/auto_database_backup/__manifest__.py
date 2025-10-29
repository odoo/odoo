# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
{
    'name': "Automatic Database Backup To Local Server, Remote Server,"
            "Google Drive, Dropbox, Onedrive, Nextcloud and Amazon S3 Odoo19",
    'version': '19.0.1.0.0',
    'live_test_url': 'https://youtu.be/Q2yMZyYjuTI',
    'category': 'Extra Tools',
    'summary': 'Odoo Database Backup, Automatic Backup, Database Backup, Automatic Backup,Database auto-backup, odoo backup'
               'google drive, dropbox, nextcloud, amazon S3, onedrive or '
               'remote server, Odoo19, Backup, Database, Odoo Apps',
    'description': 'Odoo Database Backup, Database Backup, Automatic Backup, automatic database backup, odoo19, odoo apps,backup, automatic backup,odoo19 automatic database backup,backup google drive,backup dropbox, backup nextcloud, backup amazon S3, backup onedrive',
    'author': "Cybrosys Techno Solutions",
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': "https://www.cybrosys.com",
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'data/mail_template_data.xml',
        'views/db_backup_configure_views.xml',
        'wizard/dropbox_auth_code_views.xml',
    ],
    'external_dependencies': {
        'python': ['dropbox', 'pyncclient', 'boto3', 'nextcloud-api-wrapper','paramiko']},
    'images': ['static/description/banner.gif'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}

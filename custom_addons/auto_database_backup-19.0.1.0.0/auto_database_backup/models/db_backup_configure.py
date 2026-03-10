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
from email.policy import default

import boto3
import dropbox
import errno
import ftplib
import json
import logging
import nextcloud_client
import os
import paramiko
import requests
import shutil
import subprocess
import tempfile
import odoo
from datetime import datetime, timedelta
from nextcloud import NextCloud
from requests.auth import HTTPBasicAuth
from werkzeug import urls
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import find_pg_tool, exec_pg_environ
from odoo.http import request
from odoo.service import db

_logger = logging.getLogger(__name__)
ONEDRIVE_SCOPE = ['offline_access openid Files.ReadWrite.All']
MICROSOFT_GRAPH_END_POINT = "https://graph.microsoft.com"
GOOGLE_AUTH_ENDPOINT = 'https://accounts.google.com/o/oauth2/auth'
GOOGLE_TOKEN_ENDPOINT = 'https://accounts.google.com/o/oauth2/token'
GOOGLE_API_BASE_URL = 'https://www.googleapis.com'  


class DbBackupConfigure(models.Model):
    """DbBackupConfigure class provides an interface to manage database
       backups of Local Server, Remote Server, Google Drive, Dropbox, Onedrive,
       Nextcloud and Amazon S3"""
    _name = 'db.backup.configure'
    _description = 'Automatic Database Backup'

    name = fields.Char(string='Name', required=True, help='Add the name')
    db_name = fields.Char(string='Database Name', required=True,
                          help='Name of the database')
    master_pwd = fields.Char(string='Master Password', required=True,
                             help='Master password')
    backup_format = fields.Selection([
        ('zip', 'Zip'),
        ('dump', 'Dump')
    ], string='Backup Format', default='zip', required=True,
        help='Format of the backup')
    backup_destination = fields.Selection([
        ('local', 'Local Storage'),
        ('google_drive', 'Google Drive'),
        ('ftp', 'FTP'),
        ('sftp', 'SFTP'),
        ('dropbox', 'Dropbox'),
        ('onedrive', 'Onedrive'),
        ('next_cloud', 'Next Cloud'),
        ('amazon_s3', 'Amazon S3')
    ], string='Backup Destination', help='Destination of the backup')
    backup_frequency = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ], default='daily', string='Backup Frequency', help='Frequency of Backup Scheduling')
    backup_path = fields.Char(string='Backup Path',
                              help='Local storage directory path')
    sftp_host = fields.Char(string='SFTP Host', help='SFTP host details')
    sftp_port = fields.Char(string='SFTP Port', default=22,
                            help='SFTP port details')
    sftp_user = fields.Char(string='SFTP User', copy=False,
                            help='SFTP user details')
    sftp_password = fields.Char(string='SFTP Password', copy=False,
                                help='SFTP password')
    sftp_path = fields.Char(string='SFTP Path', help='SFTP path details')
    ftp_host = fields.Char(string='FTP Host', help='FTP host details')
    ftp_port = fields.Char(string='FTP Port', default=21,
                           help='FTP port details')
    ftp_user = fields.Char(string='FTP User', copy=False,
                           help='FTP user details')
    ftp_password = fields.Char(string='FTP Password', copy=False,
                               help='FTP password')
    ftp_path = fields.Char(string='FTP Path', help='FTP path details')
    dropbox_client_key = fields.Char(string='Dropbox Client ID', copy=False,
                                     help='Client id of the dropbox')
    dropbox_client_secret = fields.Char(string='Dropbox Client Secret',
                                        copy=False,
                                        help='Client secret id of the dropbox')
    dropbox_refresh_token = fields.Char(string='Dropbox Refresh Token',
                                        copy=False,
                                        help='Refresh token for the dropbox')
    is_dropbox_token_generated = fields.Boolean(
        string='Dropbox Token Generated',
        compute='_compute_is_dropbox_token_generated',
        copy=False, help='Is the dropbox token generated or not?')
    dropbox_folder = fields.Char(string='Dropbox Folder',
                                 help='Dropbox folder')
    active = fields.Boolean(default=False, string='Active',
                            help='Activate the Scheduled Action or not')
    hide_active = fields.Boolean(string="Hide Active",
                                 help="Make active field to readonly")
    auto_remove = fields.Boolean(string='Remove Old Backups',
                                 help='Remove old backups')
    days_to_remove = fields.Integer(string='Remove After',
                                    default=1,
                                    help='Automatically delete stored backups'
                                         ' after this specified number of days')
    google_drive_folder_key = fields.Char(string='Drive Folder ID',
                                          help='Folder id of the drive')
    notify_user = fields.Boolean(string='Notify User',
                                 help='Send an email notification to user when'
                                      'the backup operation is successful'
                                      ' or failed')
    user_id = fields.Many2one('res.users', string='User',
                              help='Name of the user')
    backup_filename = fields.Char(string='Backup Filename',
                                  help='For Storing generated backup filename')
    generated_exception = fields.Char(string='Exception',
                                      help='Exception Encountered while Backup '
                                           'generation')
    onedrive_client_key = fields.Char(string='Onedrive Client ID', copy=False,
                                      help='Client ID of the onedrive')
    onedrive_client_secret = fields.Char(string='Onedrive Client Secret',
                                         copy=False, help='Client secret id of'
                                                          ' the onedrive')
    onedrive_access_token = fields.Char(string='Onedrive Access Token',
                                        copy=False,
                                        help='Access token for one drive')
    onedrive_refresh_token = fields.Char(string='Onedrive Refresh Token',
                                         copy=False,
                                         help='Refresh token for one drive')
    onedrive_token_validity = fields.Datetime(string='Onedrive Token Validity',
                                              copy=False,
                                              help='Token validity date')
    onedrive_folder_key = fields.Char(string='Folder ID',
                                      help='Folder id of the onedrive')
    is_onedrive_token_generated = fields.Boolean(
        string='onedrive Tokens Generated',
        compute='_compute_is_onedrive_token_generated',
        copy=False, help='Whether to generate onedrive token?')
    gdrive_refresh_token = fields.Char(string='Google drive Refresh Token',
                                       copy=False,
                                       help='Refresh token for google drive')
    gdrive_access_token = fields.Char(string='Google Drive Access Token',
                                      copy=False,
                                      help='Access token for google drive')
    is_google_drive_token_generated = fields.Boolean(
        string='Google drive Token Generated',
        compute='_compute_is_google_drive_token_generated', copy=False,
        help='Google drive token generated or not')
    gdrive_client_key = fields.Char(string='Google Drive Client ID',
                                    copy=False,
                                    help='Client id of the google drive')
    gdrive_client_secret = fields.Char(string='Google Drive Client Secret',
                                       copy=False,
                                       help='Client secret id of the google'
                                            ' drive')
    gdrive_token_validity = fields.Datetime(
        string='Google Drive Token Validity', copy=False,
        help='Token validity of the google drive')
    onedrive_redirect_uri = fields.Char(string='Onedrive Redirect URI',
                                        compute='_compute_redirect_uri',
                                        help='Redirect URI of the onedrive')
    gdrive_redirect_uri = fields.Char(string='Google Drive Redirect URI',
                                      compute='_compute_redirect_uri',
                                      help='Redirect URI of the google drive')
    domain = fields.Char(string='Domain Name', help="Field used to store the "
                                                    "name of a domain")
    next_cloud_user_name = fields.Char(string='User Name',
                                       help="Field used to store the user name"
                                            " for a Nextcloud account.")
    next_cloud_password = fields.Char(string='Password',
                                      help="Field used to store the password"
                                           " for a Nextcloud account.")
    nextcloud_folder_key = fields.Char(string='Next Cloud Folder Id',
                                       help="Field used to store the unique "
                                            "identifier for a Nextcloud "
                                            "folder.")
    aws_access_key = fields.Char(string="Amazon S3 Access Key",
                                 help="Field used to store the Access Key"
                                      " for an Amazon S3 bucket.")
    aws_secret_access_key = fields.Char(string='Amazon S3 Secret Key',
                                        help="Field used to store the Secret"
                                             " Key for an Amazon S3 bucket.")
    bucket_file_name = fields.Char(string='Bucket Name',
                                   help="Field used to store the name of an"
                                        " Amazon S3 bucket.")
    aws_folder_name = fields.Char(string='File Name',
                                  help="field used to store the name of a"
                                       " folder in an Amazon S3 bucket.")

    def action_s3cloud(self):
        """If it has aws_secret_access_key, which will perform s3cloud
         operations for connection test"""
        if self.aws_access_key and self.aws_secret_access_key:
            try:
                s3_client = boto3.client(
                    's3',
                    aws_access_key_id=self.aws_access_key,
                    aws_secret_access_key=self.aws_secret_access_key
                )
                response = s3_client.head_bucket(Bucket=self.bucket_file_name)
                if response['ResponseMetadata']['HTTPStatusCode'] == 200:
                    self.active = self.hide_active = True
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'type': 'success',
                            'title': _("Connection Test Succeeded!"),
                            'message': _(
                                "Everything seems properly set up!"),
                            'sticky': False,
                        }
                    }
                raise UserError(
                    _("Bucket not found. Please check the bucket name and"
                      " try again."))
            except Exception:
                self.active = self.hide_active = False
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'type': 'danger',
                        'title': _("Connection Test Failed!"),
                        'message': _("An error occurred while testing the "
                                     "connection."),
                        'sticky': False,
                    }
                }

    def action_nextcloud(self):
        """If it has next_cloud_password, domain, and next_cloud_user_name
         which will perform an action for nextcloud connection test"""
        if self.domain and self.next_cloud_password and \
                self.next_cloud_user_name:
            try:
                ncx = NextCloud(self.domain,
                                auth=HTTPBasicAuth(self.next_cloud_user_name,
                                                   self.next_cloud_password))
                data = ncx.list_folders('/').__dict__
                if data['raw'].status_code == 207:
                    self.active = self.hide_active = True
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'type': 'success',
                            'title': _("Connection Test Succeeded!"),
                            'message': _("Everything seems properly set up!"),
                            'sticky': False,
                        }
                    }
                else:
                    self.active = self.hide_active = False
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'type': 'danger',
                            'title': _("Connection Test Failed!"),
                            'message': _("An error occurred while testing the "
                                         "connection."),
                            'sticky': False,
                        }
                    }
            except Exception:
                self.active = self.hide_active = False
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'type': 'danger',
                        'title': _("Connection Test Failed!"),
                        'message': _("An error occurred while testing the "
                                     "connection."),
                        'sticky': False,
                    }
                }

    @api.depends('onedrive_redirect_uri', 'gdrive_redirect_uri')
    def _compute_redirect_uri(self):
        """Compute the redirect URI for onedrive and Google Drive"""
        for rec in self:
            rec.onedrive_redirect_uri = self.get_base_url() + '/onedrive/authentication'
            rec.gdrive_redirect_uri = self.get_base_url() + '/google_drive/authentication'

    @api.depends('onedrive_access_token', 'onedrive_refresh_token')
    def _compute_is_onedrive_token_generated(self):
        """Set true if onedrive tokens are generated"""
        for rec in self:
            rec.is_onedrive_token_generated = bool(
                rec.onedrive_access_token) and bool(rec.onedrive_refresh_token)

    @api.depends('dropbox_refresh_token')
    def _compute_is_dropbox_token_generated(self):
        """Set True if the dropbox refresh token is generated"""
        for rec in self:
            rec.is_dropbox_token_generated = bool(rec.dropbox_refresh_token)

    @api.depends('gdrive_access_token', 'gdrive_refresh_token')
    def _compute_is_google_drive_token_generated(self):
        """Set True if the Google Drive refresh token is generated"""
        for rec in self:
            rec.is_google_drive_token_generated = bool(
                rec.gdrive_access_token) and bool(rec.gdrive_refresh_token)

    def action_get_dropbox_auth_code(self):
        """Open a wizards to set up dropbox Authorization code"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Dropbox Authorization Wizard',
            'res_model': 'dropbox.auth.code',
            'view_mode': 'form',
            'target': 'new',
            'context': {'dropbox_auth': True}
        }

    def action_get_onedrive_auth_code(self):
        """Generate OneDrive authorization code."""
        AUTHORITY = 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize'
        base_url = self.get_base_url()
        action_id = self.env["ir.actions.act_window"].sudo()._for_xml_id(
            "auto_database_backup.db_backup_configure_action")['id']
        url_return = f"{base_url}/web#id={self.id}&action={action_id}&view_type=form&model=db.backup.configure"
        state = {
            'backup_config_id': self.id,
            'url_return': url_return}
        params = {
            'response_type': 'code',
            'client_id': self.onedrive_client_key,
            'state': json.dumps(state),
            'scope': ONEDRIVE_SCOPE,
            'redirect_uri': f"{base_url}/onedrive/authentication",
            'prompt': 'consent',
            'access_type': 'offline'
        }
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': f"{AUTHORITY}?{urls.url_encode(params)}",
        }

    def action_get_gdrive_auth_code(self):
        """Generate Google Drive authorization code."""
        GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/auth"
        base_url = self.get_base_url()
        action_id = self.env["ir.actions.act_window"].sudo()._for_xml_id(
            "auto_database_backup.db_backup_configure_action")['id']
        url_return = f"{base_url}/web#id={self.id}&action={action_id}&view_type=form&model=db.backup.configure"
        state = {
            'backup_config_id': self.id,
            'url_return': url_return }
        params = {
            'response_type': 'code',
            'client_id': self.gdrive_client_key,
            'scope': 'https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/drive.file',
            'redirect_uri': f"{base_url}/google_drive/authentication",
            'access_type': 'offline',
            'state': json.dumps(state),
            'approval_prompt': 'force',
        }
        auth_url = f"{GOOGLE_AUTH_ENDPOINT}?{urls.url_encode(params)}"
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': auth_url,
        }

    def generate_onedrive_refresh_token(self):
        """Generate OneDrive access token from refresh token if expired."""
        base_url = self.get_base_url()
        token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        data = {
            'client_id': self.onedrive_client_key,
            'client_secret': self.onedrive_client_secret,
            'scope': ONEDRIVE_SCOPE,
            'grant_type': "refresh_token",
            'redirect_uri': f"{base_url}/onedrive/authentication",
            'refresh_token': self.onedrive_refresh_token,
        }
        try:
            res = requests.post(token_url, data=data, headers=headers)
            res.raise_for_status()
            response = res.json() if res.ok else {}
            if response:
                expires_in = response.get('expires_in', 0)
                self.write({
                    'onedrive_access_token': response.get('access_token'),
                    'onedrive_refresh_token': response.get('refresh_token'),
                    'onedrive_token_validity': fields.Datetime.now() + timedelta(seconds=expires_in),
                })
        except requests.HTTPError as error:
            _logger.exception("Bad Microsoft OneDrive request: %s", error.response.content)
            raise error

    def get_onedrive_tokens(self, authorize_code):
        """Generate OneDrive tokens from authorization code."""
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        base_url = self.get_base_url()
        data = {
            'code': authorize_code,
            'client_id': self.onedrive_client_key,
            'client_secret': self.onedrive_client_secret,
            'grant_type': 'authorization_code',
            'scope': ONEDRIVE_SCOPE,
            'redirect_uri': f"{base_url}/onedrive/authentication",
        }
        token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
        try:
            res = requests.post(token_url, data=data, headers=headers)
            res.raise_for_status()
            response = res.json() if res.ok else {}
            if response:
                expires_in = response.get('expires_in', 0)
                self.write({
                    'onedrive_access_token': response.get('access_token'),
                    'onedrive_refresh_token': response.get('refresh_token'),
                    'onedrive_token_validity': fields.Datetime.now() + timedelta(seconds=expires_in),
                })
        except requests.HTTPError as error:
            _logger.exception("Bad Microsoft OneDrive request: %s", error.response.content)
            raise error

    def generate_gdrive_refresh_token(self):
        """Generate Google Drive access token from refresh token if expired."""
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            'refresh_token': self.gdrive_refresh_token,
            'client_id': self.gdrive_client_key,
            'client_secret': self.gdrive_client_secret,
            'grant_type': 'refresh_token',
        }
        try:
            res = requests.post(GOOGLE_TOKEN_ENDPOINT, data=data, headers=headers)
            res.raise_for_status()
            response = res.json() if res.ok else {}
            if response:
                expires_in = response.get('expires_in', 0)
                self.write({
                    'gdrive_access_token': response.get('access_token'),
                    'gdrive_token_validity': fields.Datetime.now() + timedelta(seconds=expires_in),
                })
        except requests.HTTPError as error:
            error_key = error.response.json().get("error", "unknown error")
            error_msg = _(
                "An error occurred while generating the token. Your "
                "authorization code may be invalid or has already expired [%s]. "
                "Please check your Client ID and secret on the Google APIs "
                "platform or try stopping and restarting your calendar "
                "synchronization.",
                error_key
            )
            raise UserError(error_msg)

    def get_gdrive_tokens(self, authorize_code):
        """Generate Google Drive tokens from authorization code."""
        base_url = request.env['ir.config_parameter'].get_param('web.base.url')
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            'code': authorize_code,
            'client_id': self.gdrive_client_key,
            'client_secret': self.gdrive_client_secret,
            'grant_type': 'authorization_code',
            'redirect_uri': f"{base_url}/google_drive/authentication",
        }
        try:
            res = requests.post(GOOGLE_TOKEN_ENDPOINT, data=data, headers=headers)
            res.raise_for_status()
            response = res.json() if res.ok else {}
            if response:
                expires_in = response.get('expires_in', 0)
                self.write({
                    'gdrive_access_token': response.get('access_token'),
                    'gdrive_refresh_token': response.get('refresh_token'),
                    'gdrive_token_validity': fields.Datetime.now() + timedelta(
                        seconds=expires_in) if expires_in else False,
                })
        except requests.HTTPError:
            error_msg = _(
                "Something went wrong during your token generation. "
                "Your authorization code may be invalid."
            )
            raise UserError(error_msg)

    def get_dropbox_auth_url(self):
        """Return dropbox authorization url"""
        dbx_auth = dropbox.oauth.DropboxOAuth2FlowNoRedirect(
            self.dropbox_client_key,
            self.dropbox_client_secret,
            token_access_type='offline')
        return dbx_auth.start()

    def set_dropbox_refresh_token(self, auth_code):
        """Generate and set the dropbox refresh token from authorization code"""
        dbx_auth = dropbox.oauth.DropboxOAuth2FlowNoRedirect(
            self.dropbox_client_key,
            self.dropbox_client_secret,
            token_access_type='offline')
        outh_result = dbx_auth.finish(auth_code)
        self.dropbox_refresh_token = outh_result.refresh_token

    @api.constrains('db_name')
    def _check_db_credentials(self):
        """Validate entered database name and master password"""
        database_list = db.list_dbs(force=True)
        if self.db_name not in database_list:
            raise ValidationError(_("Invalid Database Name!"))
        try:
            odoo.service.db.check_super(self.master_pwd)
        except Exception:
            raise ValidationError(_("Invalid Master Password!"))

    def action_sftp_connection(self):
        """Test the sftp and ftp connection using entered credentials"""
        if self.backup_destination == 'sftp':
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                client.connect(hostname=self.sftp_host,
                               username=self.sftp_user,
                               password=self.sftp_password,
                               port=self.sftp_port)
                sftp = client.open_sftp()
                sftp.close()
            except Exception as e:
                raise UserError(_("SFTP Exception: %s", e))
            finally:
                client.close()
        elif self.backup_destination == 'ftp':
            try:
                ftp_server = ftplib.FTP()
                ftp_server.connect(self.ftp_host, int(self.ftp_port))
                ftp_server.login(self.ftp_user, self.ftp_password)
                ftp_server.quit()
            except Exception as e:
                raise UserError(_("FTP Exception: %s", e))
        self.active = self.hide_active = True
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Connection Test Succeeded!"),
                'message': _("Everything seems properly set up!"),
                'sticky': False,
            }
        }

    @api.onchange('backup_destination')
    def _onchange_back_up_local(self):
        """
        On change handler for the 'backup_destination' field. This method is
        triggered when the value of 'backup_destination' is changed. If the
        chosen backup destination is 'local', it sets the 'hide_active' field
        to True which make active field to readonly to False.
         """
        if self.backup_destination == 'local':
            self.hide_active = True

    def _schedule_auto_backup(self, frequency):
        """Function for generating and storing backup.
           Database backup for all the active records in backup configuration
           model will be created."""
        records = self.search([('backup_frequency', '=', frequency)])
        mail_template_success = self.env.ref(
            'auto_database_backup.mail_template_data_db_backup_successful')
        mail_template_failed = self.env.ref(
            'auto_database_backup.mail_template_data_db_backup_failed')
        for rec in records:
            backup_time = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
            backup_filename = f"{rec.db_name}_{backup_time}.{rec.backup_format}"
            rec.backup_filename = backup_filename
            # Local backup
            if rec.backup_destination == 'local':
                try:
                    if not os.path.isdir(rec.backup_path):
                        os.makedirs(rec.backup_path)
                    backup_file = os.path.join(rec.backup_path,
                                               backup_filename)
                    f = open(backup_file, "wb")
                    self.dump_data(rec.db_name, f, rec.backup_format, rec.backup_frequency)
                    f.close()
                    # Remove older backups
                    if rec.auto_remove:
                        for filename in os.listdir(rec.backup_path):
                            file = os.path.join(rec.backup_path, filename)
                            create_time = datetime.fromtimestamp(
                                os.path.getctime(file))
                            backup_duration = datetime.utcnow() - create_time
                            if backup_duration.days >= rec.days_to_remove:
                                os.remove(file)
                    if rec.notify_user:
                        mail_template_success.send_mail(rec.id, force_send=True)
                except Exception as e:
                    rec.generated_exception = e
                    _logger.info('FTP Exception: %s', e)
                    if rec.notify_user:
                        mail_template_failed.send_mail(rec.id, force_send=True)
            # FTP backup
            elif rec.backup_destination == 'ftp':
                try:
                    ftp_server = ftplib.FTP()
                    ftp_server.connect(rec.ftp_host, int(rec.ftp_port))
                    ftp_server.login(rec.ftp_user, rec.ftp_password)
                    ftp_server.encoding = "utf-8"
                    temp = tempfile.NamedTemporaryFile(
                        suffix='.%s' % rec.backup_format)
                    try:
                        ftp_server.cwd(rec.ftp_path)
                    except ftplib.error_perm:
                        ftp_server.mkd(rec.ftp_path)
                        ftp_server.cwd(rec.ftp_path)
                    with open(temp.name, "wb+") as tmp:
                        self.dump_data(rec.db_name, tmp,
                                                rec.backup_format, rec.backup_frequency)
                    ftp_server.storbinary('STOR %s' % backup_filename,
                                          open(temp.name, "rb"))
                    if rec.auto_remove:
                        files = ftp_server.nlst()
                        for file in files:
                            create_time = datetime.strptime(
                                ftp_server.sendcmd('MDTM ' + file)[4:],
                                "%Y%m%d%H%M%S")
                            diff_days = (
                                    datetime.now() - create_time).days
                            if diff_days >= rec.days_to_remove:
                                ftp_server.delete(file)
                    ftp_server.quit()
                    if rec.notify_user:
                        mail_template_success.send_mail(rec.id,
                                                        force_send=True)
                except Exception as e:
                    rec.generated_exception = e
                    _logger.info('FTP Exception: %s', e)
                    if rec.notify_user:
                        mail_template_failed.send_mail(rec.id, force_send=True)
            # SFTP backup
            elif rec.backup_destination == 'sftp':
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                try:
                    client.connect(hostname=rec.sftp_host,
                                   username=rec.sftp_user,
                                   password=rec.sftp_password,
                                   port=rec.sftp_port)
                    sftp = client.open_sftp()
                    temp = tempfile.NamedTemporaryFile(
                        suffix='.%s' % rec.backup_format)
                    with open(temp.name, "wb+") as tmp:
                        self.dump_data(rec.db_name, tmp, rec.backup_format, rec.backup_frequency)
                    try:
                        sftp.chdir(rec.sftp_path)
                    except IOError as e:
                        if e.errno == errno.ENOENT:
                            sftp.mkdir(rec.sftp_path)
                            sftp.chdir(rec.sftp_path)
                    sftp.put(temp.name, backup_filename)
                    if rec.auto_remove:
                        files = sftp.listdir()
                        expired = list(filter(
                            lambda fl: (fields.Datetime.now()
                                        - datetime.fromtimestamp(
                                        sftp.stat(fl).st_mtime)).days >=
                                       rec.days_to_remove, files))
                        for file in expired:
                            sftp.unlink(file)
                    sftp.close()
                    if rec.notify_user:
                        mail_template_success.send_mail(rec.id,
                                                        force_send=True)
                except Exception as e:
                    rec.generated_exception = e
                    _logger.info('SFTP Exception: %s', e)
                    if rec.notify_user:
                        mail_template_failed.send_mail(rec.id, force_send=True)
                finally:
                    client.close()
            # Google Drive backup
            elif rec.backup_destination == 'google_drive':
                try:
                    if rec.gdrive_token_validity <= fields.Datetime.now():
                        rec.generate_gdrive_refresh_token()
                    temp = tempfile.NamedTemporaryFile(
                        suffix='.%s' % rec.backup_format)
                    with open(temp.name, "wb+") as tmp:
                        self.dump_data(rec.db_name, tmp,
                                                rec.backup_format, rec.backup_frequency)
                    try:
                        headers = {
                            "Authorization": "Bearer %s" % rec.gdrive_access_token}
                        para = {
                            "name": backup_filename,
                            "parents": [rec.google_drive_folder_key],
                        }
                        files = {
                            'data': ('metadata', json.dumps(para),
                                     'application/json; charset=UTF-8'),
                            'file': open(temp.name, "rb")
                        }
                        requests.post(
                            "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
                            headers=headers,
                            files=files
                        )
                        if rec.auto_remove:
                            query = "parents = '%s'" % rec.google_drive_folder_key
                            files_req = requests.get(
                                "https://www.googleapis.com/drive/v3/files?q=%s" % query,
                                headers=headers)
                            for file in files_req.json()['files']:
                                file_date_req = requests.get(
                                    "https://www.googleapis.com/drive/v3/files/%s?fields=createdTime" %
                                    file['id'], headers=headers)
                                create_time = file_date_req.json()[
                                                  'createdTime'][
                                              :19].replace('T', ' ')
                                diff_days = (
                                        fields.Datetime.now() - datetime.strptime(
                                    create_time, '%Y-%m-%d %H:%M:%S')).days
                                if diff_days >= rec.days_to_remove:
                                    requests.delete(
                                        "https://www.googleapis.com/drive/v3/files/%s" %
                                        file['id'], headers=headers)
                        if rec.notify_user:
                            mail_template_success.send_mail(rec.id,
                                                            force_send=True)
                    except Exception as e:

                        rec.generated_exception = e
                        _logger.info('Google Drive Exception: %s', e)
                        if rec.notify_user:
                            mail_template_failed.send_mail(rec.id,
                                                           force_send=True)
                except Exception:
                    if rec.notify_user:
                        mail_template_failed.send_mail(rec.id, force_send=True)
                        raise ValidationError(
                            'Please check the credentials before activation')
                    else:
                        raise ValidationError('Please check connection')
            # Dropbox backup
            elif rec.backup_destination == 'dropbox':
                temp = tempfile.NamedTemporaryFile(
                    suffix='.%s' % rec.backup_format)
                with open(temp.name, "wb+") as tmp:
                    self.dump_data(rec.db_name, tmp,
                                            rec.backup_format, rec.backup_frequency)
                try:
                    dbx = dropbox.Dropbox(
                        app_key=rec.dropbox_client_key,
                        app_secret=rec.dropbox_client_secret,
                        oauth2_refresh_token=rec.dropbox_refresh_token)
                    dropbox_destination = (rec.dropbox_folder + '/' +
                                           backup_filename)
                    dbx.files_upload(temp.read(), dropbox_destination)
                    if rec.auto_remove:
                        files = dbx.files_list_folder(rec.dropbox_folder)
                        file_entries = files.entries
                        expired_files = list(filter(
                            lambda fl: (fields.Datetime.now() -
                                        fl.client_modified).days >=
                                       rec.days_to_remove,
                            file_entries))
                        for file in expired_files:
                            dbx.files_delete_v2(file.path_display)
                    if rec.notify_user:
                        mail_template_success.send_mail(rec.id,
                                                        force_send=True)
                except Exception as error:
                    rec.generated_exception = error
                    _logger.info('Dropbox Exception: %s', error)
                    if rec.notify_user:
                        mail_template_failed.send_mail(rec.id, force_send=True)
            # Onedrive Backup
            elif rec.backup_destination == 'onedrive':
                try:
                    if rec.onedrive_token_validity <= fields.Datetime.now():
                        rec.generate_onedrive_refresh_token()

                    with tempfile.NamedTemporaryFile(suffix=f'.{rec.backup_format}') as temp:
                        with open(temp.name, "wb+") as tmp:
                            self.dump_data(rec.db_name, tmp, rec.backup_format, rec.backup_frequency)

                        headers = {
                            'Authorization': f'Bearer {rec.onedrive_access_token}',
                            'Content-Type': 'application/json'
                        }

                        upload_session_url = (
                            f"{MICROSOFT_GRAPH_END_POINT}/v1.0/me/drive/items/"
                            f"{rec.onedrive_folder_key}:/{backup_filename}:/createUploadSession"
                        )

                        upload_session = requests.post(upload_session_url, headers=headers)
                        upload_session.raise_for_status()

                        upload_url = upload_session.json().get('uploadUrl')
                        if not upload_url:
                            raise ValueError("Failed to get upload URL from OneDrive")

                        file_size = os.path.getsize(temp.name)
                        with open(temp.name, 'rb') as f:
                            headers_upload = {
                                'Content-Length': str(file_size),
                                'Content-Range': f'bytes 0-{file_size - 1}/{file_size}'
                            }
                            upload_response = requests.put(upload_url, headers=headers_upload, data=f)
                            upload_response.raise_for_status()

                        if rec.auto_remove:
                            verify_url = (
                                f"{MICROSOFT_GRAPH_END_POINT}/v1.0/me/drive/items/"
                                f"{rec.onedrive_folder_key}:/{backup_filename}"
                            )
                            verify_response = requests.get(verify_url, headers=headers)

                            if verify_response.status_code == 200:
                                list_url = (
                                    f"{MICROSOFT_GRAPH_END_POINT}/v1.0/me/drive/items/"
                                    f"{rec.onedrive_folder_key}/children"
                                )
                                response = requests.get(list_url, headers=headers)
                                response.raise_for_status()

                                files = response.json().get('value', [])
                                current_time = fields.Datetime.now()

                                for file in files:
                                    if file['name'] == backup_filename:
                                        continue

                                    create_time_str = file['createdDateTime'][:19].replace('T', ' ')
                                    create_time = datetime.strptime(create_time_str, '%Y-%m-%d %H:%M:%S')
                                    diff_days = (current_time - create_time).days

                                    if diff_days >= rec.days_to_remove:
                                        delete_url = f"{MICROSOFT_GRAPH_END_POINT}/v1.0/me/drive/items/{file['id']}"
                                        requests.delete(delete_url, headers=headers).raise_for_status()

                        # Notify user on success
                        if rec.notify_user:
                            mail_template_success.send_mail(rec.id, force_send=True)

                except requests.exceptions.RequestException as req_error:
                    rec.generated_exception = str(req_error)
                    _logger.error('OneDrive API Error: %s', req_error, exc_info=True)
                    if rec.notify_user:
                        mail_template_failed.send_mail(rec.id, force_send=True)

                except Exception as error:
                    rec.generated_exception = str(error)
                    _logger.error('OneDrive Backup Error: %s', error, exc_info=True)
                    if rec.notify_user:
                        mail_template_failed.send_mail(rec.id, force_send=True)
            elif rec.backup_destination == 'next_cloud':
                try:
                    if rec.domain and rec.next_cloud_password and \
                            rec.next_cloud_user_name:
                        try:
                            # Connect to NextCloud using the provided username
                            # and password
                            ncx = NextCloud(rec.domain,
                                            auth=HTTPBasicAuth(
                                                rec.next_cloud_user_name,
                                                rec.next_cloud_password))
                            # Connect to NextCloud again to perform additional
                            # operations
                            nc = nextcloud_client.Client(rec.domain)
                            nc.login(rec.next_cloud_user_name,
                                     rec.next_cloud_password)
                            # Get the folder name from the NextCloud folder ID
                            folder_name = rec.nextcloud_folder_key
                            # If auto_remove is enabled, remove backup files
                            # older than specified days
                            if rec.auto_remove:
                                folder_path = "/" + folder_name
                                for item in nc.list(folder_path):
                                    backup_file_name = item.path.split("/")[-1]
                                    backup_date_str = \
                                        backup_file_name.split("_")[1]
                                    backup_date = datetime.strptime(
                                        backup_date_str, '%Y-%m-%d').date()
                                    if (fields.date.today() - backup_date).days \
                                            >= rec.days_to_remove:
                                        nc.delete(item.path)
                            # If notify_user is enabled, send a success email
                            # notification
                            if rec.notify_user:
                                mail_template_success.send_mail(rec.id,
                                                                force_send=True)
                        except Exception as error:
                            rec.generated_exception = error
                            _logger.info('NextCloud Exception: %s', error)
                            if rec.notify_user:
                                # If an exception occurs, send a failed email
                                # notification
                                mail_template_failed.send_mail(rec.id,
                                                               force_send=True)
                        # Get the list of folders in the root directory of NextCloud
                        data = ncx.list_folders('/').__dict__
                        folders = [
                            [file_name['href'].split('/')[-2],
                             file_name['file_id']]
                            for file_name in data['data'] if
                            file_name['href'].endswith('/')]
                        # If the folder name is not found in the list of folders,
                        # create the folder
                        if folder_name not in [file[0] for file in folders]:
                            nc.mkdir(folder_name)
                            # Dump the database to a temporary file
                            temp = tempfile.NamedTemporaryFile(
                                suffix='.%s' % rec.backup_format)
                            with open(temp.name, "wb+") as tmp:
                                self.dump_data(rec.db_name, tmp,
                                                        rec.backup_format, rec.backup_frequency)
                            backup_file_name = temp.name
                            remote_file_path = f"/{folder_name}/{rec.db_name}_" \
                                               f"{backup_time}.{rec.backup_format}"
                            nc.put_file(remote_file_path, backup_file_name)
                        else:
                            # Dump the database to a temporary file
                            temp = tempfile.NamedTemporaryFile(
                                suffix='.%s' % rec.backup_format)
                            with open(temp.name, "wb+") as tmp:
                                self.dump_data(rec.db_name, tmp,
                                                        rec.backup_format, rec.backup_frequency)
                            backup_file_name = temp.name
                            remote_file_path = f"/{folder_name}/{rec.db_name}_" \
                                               f"{backup_time}.{rec.backup_format}"
                            nc.put_file(remote_file_path, backup_file_name)
                except Exception:
                    raise ValidationError('Please check connection')
            # Amazon S3 Backup
            elif rec.backup_destination == 'amazon_s3':
                if rec.aws_access_key and rec.aws_secret_access_key:
                    try:
                        # Create a boto3 client for Amazon S3 with provided
                        # access key id and secret access key
                        bo3 = boto3.client(
                            's3',
                            aws_access_key_id=rec.aws_access_key,
                            aws_secret_access_key=rec.aws_secret_access_key)
                        # If auto_remove is enabled, remove the backups that
                        # are older than specified days from the S3 bucket
                        if rec.auto_remove:
                            folder_path = rec.aws_folder_name
                            response = bo3.list_objects(
                                Bucket=rec.bucket_file_name,
                                Prefix=folder_path)
                            today = fields.date.today()
                            for file in response['Contents']:
                                file_path = file['Key']
                                last_modified = file['LastModified']
                                date = last_modified.date()
                                age_in_days = (today - date).days
                                if age_in_days >= rec.days_to_remove:
                                    bo3.delete_object(
                                        Bucket=rec.bucket_file_name,
                                        Key=file_path)
                        # Create a boto3 resource for Amazon S3 with provided
                        # access key id and secret access key
                        s3 = boto3.resource(
                            's3',
                            aws_access_key_id=rec.aws_access_key,
                            aws_secret_access_key=rec.aws_secret_access_key)
                        # Create a folder in the specified bucket, if it
                        # doesn't already exist
                        s3.Object(rec.bucket_file_name,
                                  rec.aws_folder_name + '/').put()
                        bucket = s3.Bucket(rec.bucket_file_name)
                        # Get all the prefixes in the bucket
                        prefixes = set()
                        for obj in bucket.objects.all():
                            key = obj.key
                            if key.endswith('/'):
                                prefix = key[:-1]  # Remove the trailing slash
                                prefixes.add(prefix)
                        # If the specified folder is present in the bucket,
                        # take a backup of the database and upload it to the
                        # S3 bucket
                        if rec.aws_folder_name in prefixes:
                            temp = tempfile.NamedTemporaryFile(
                                suffix='.%s' % rec.backup_format)
                            with open(temp.name, "wb+") as tmp:
                                self.dump_data(rec.db_name, tmp,
                                                        rec.backup_format, rec.backup_frequency)
                            backup_file_name = temp.name
                            remote_file_path = f"{rec.aws_folder_name}/{rec.db_name}_" \
                                               f"{backup_time}.{rec.backup_format}"
                            s3.Object(rec.bucket_file_name,
                                      remote_file_path).upload_file(
                                backup_file_name)
                            # If notify_user is enabled, send an email to the
                            # user notifying them about the successful backup
                            if rec.notify_user:
                                mail_template_success.send_mail(rec.id,
                                                                force_send=True)
                    except Exception as error:
                        # If any error occurs, set the 'generated_exception'
                        # field to the error message and log the error
                        rec.generated_exception = error
                        _logger.info('Amazon S3 Exception: %s', error)
                        # If notify_user is enabled, email the user
                        # notifying them about the failed backup
                        if rec.notify_user:
                            mail_template_failed.send_mail(rec.id, force_send=True)

    def dump_data(self, db_name, stream, backup_format, backup_frequency):
        """Dump database `db` into file-like object `stream` if stream is None
        return a file object with the dump. """
        cron_user_id = self.env.ref(f'auto_database_backup.ir_cron_auto_db_backup_{backup_frequency}').user_id.id
        if cron_user_id != self.env.user.id:
            _logger.error(
                'Unauthorized database operation. Backups should only be available from the cron job.')
            raise ValidationError("Unauthorized database operation. Backups should only be available from the cron job.")
        _logger.info('DUMP DB: %s format %s', db_name, backup_format)
        cmd = [find_pg_tool('pg_dump'), '--no-owner', db_name]
        env = exec_pg_environ()
        if backup_format == 'zip':
            with tempfile.TemporaryDirectory() as dump_dir:
                filestore = odoo.tools.config.filestore(db_name)
                cmd.insert(-1,'--file=' + os.path.join(dump_dir, 'dump.sql'))
                subprocess.run(cmd, env=env, stdout=subprocess.DEVNULL,
                               stderr=subprocess.STDOUT, check=True)
                if os.path.exists(filestore):
                    shutil.copytree(filestore,
                                    os.path.join(dump_dir, 'filestore'))
                with open(os.path.join(dump_dir, 'manifest.json'), 'w') as fh:
                    db = odoo.sql_db.db_connect(db_name)
                    with db.cursor() as cr:
                        json.dump(self._dump_db_manifest(cr), fh, indent=4)
                if stream:
                    odoo.tools.osutil.zip_dir(dump_dir, stream,
                                              include_dir=False,
                                              fnct_sort=lambda
                                                  file_name: file_name != 'dump.sql')
                else:
                    t = tempfile.TemporaryFile()
                    odoo.tools.osutil.zip_dir(dump_dir, t, include_dir=False,
                                              fnct_sort=lambda
                                                  file_name: file_name != 'dump.sql')
                    t.seek(0)
                    return t
        else:
            cmd.insert(-1,'--format=c')
            process = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE)
            stdout, _ = process.communicate()
            if stream:
                stream.write(stdout)
            else:
                return stdout

    def _dump_db_manifest(self, cr):
        """ This function generates a manifest dictionary for database dump."""
        pg_version = "%d.%d" % divmod(cr._obj.connection.server_version / 100, 100)
        cr.execute(
            "SELECT name, latest_version FROM ir_module_module WHERE state = 'installed'")
        modules = dict(cr.fetchall())
        manifest = {
            'odoo_dump': '1',
            'db_name': cr.dbname,
            'version': odoo.release.version,
            'version_info': odoo.release.version_info,
            'major_version': odoo.release.major_version,
            'pg_version': pg_version,
            'modules': modules,
        }
        return manifest

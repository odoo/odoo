# Copyright 2019 Rafis Bikbov <https://it-projects.info/team/RafiZz>
# Copyright 2019 Alexandr Kolushov <https://it-projects.info/team/KolushovAlexandr>
# Copyright 2019-2020 Eugene Molotov <https://it-projects.info/team/em230418>
import os

import boto3

from odoo import _, api, fields, models


class NotAllCredentialsGiven(Exception):
    pass


class S3Settings(models.TransientModel):
    _inherit = "res.config.settings"

    s3_bucket = fields.Char(string="S3 bucket name", help="i.e. 'attachmentbucket'")
    s3_access_key_id = fields.Char(string="S3 access key id")
    s3_secret_key = fields.Char(string="S3 secret key")
    s3_endpoint_url = fields.Char(string="S3 Endpoint")
    s3_obj_url = fields.Char(string="S3 URL")
    s3_condition = fields.Char(
        string="S3 condition",
        help="""Specify valid odoo search domain here,
                               e.g. [('res_model', 'in', ['product.image'])] -- store data of product.image only.
                               Empty condition means all models""",
    )

    def _get_s3_settings(self, param_name, os_var_name):
        config_obj = self.env["ir.config_parameter"]
        res = config_obj.sudo().get_param(param_name)
        if not res:
            res = os.environ.get(os_var_name)
        return res

    def get_s3_obj_url(self, bucket, file_id):
        base_url = self._get_s3_settings("s3.obj_url", "S3_OBJ_URL")
        if base_url:
            return base_url + file_id
        return "https://{}.s3.amazonaws.com/{}".format(bucket.name, file_id)

    def get_s3_bucket(self):
        access_key_id = self._get_s3_settings("s3.access_key_id", "S3_ACCESS_KEY_ID")
        secret_key = self._get_s3_settings("s3.secret_key", "S3_SECRET_KEY")
        bucket_name = self._get_s3_settings("s3.bucket", "S3_BUCKET")
        endpoint_url = self._get_s3_settings("s3.endpoint_url", "S3_ENDPOINT_URL")

        if not access_key_id or not secret_key or not bucket_name:
            raise NotAllCredentialsGiven(
                _("Amazon S3 credentials are not defined properly")
            )

        s3 = boto3.resource(
            "s3",
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_key,
            endpoint_url=endpoint_url,
        )
        bucket = s3.Bucket(bucket_name)
        if not bucket:
            s3.create_bucket(Bucket=bucket_name)
            bucket = s3.Bucket(bucket_name)
        return bucket

    @api.model
    def get_values(self):
        res = super(S3Settings, self).get_values()
        ICPSudo = self.env["ir.config_parameter"].sudo()
        s3_bucket = ICPSudo.get_param("s3.bucket", default="")
        s3_access_key_id = ICPSudo.get_param("s3.access_key_id", default="")
        s3_secret_key = ICPSudo.get_param("s3.secret_key", default="")
        s3_endpoint_url = ICPSudo.get_param("s3.endpoint_url", default="")
        s3_obj_url = ICPSudo.get_param("s3.obj_url", default="")
        s3_condition = ICPSudo.get_param("s3.condition", default="")

        res.update(
            s3_bucket=s3_bucket,
            s3_access_key_id=s3_access_key_id,
            s3_secret_key=s3_secret_key,
            s3_condition=s3_condition,
            s3_endpoint_url=s3_endpoint_url,
            s3_obj_url=s3_obj_url,
        )
        return res

    def set_values(self):
        super(S3Settings, self).set_values()
        ICPSudo = self.env["ir.config_parameter"].sudo()
        ICPSudo.set_param("s3.bucket", self.s3_bucket or "")
        ICPSudo.set_param("s3.access_key_id", self.s3_access_key_id or "")
        ICPSudo.set_param("s3.secret_key", self.s3_secret_key or "")
        ICPSudo.set_param("s3.endpoint_url", self.s3_endpoint_url or "")
        ICPSudo.set_param("s3.obj_url", self.s3_obj_url or "")
        ICPSudo.set_param("s3.condition", self.s3_condition or "")

    def s3_upload_existing(self):
        self.env["ir.attachment"].force_storage_s3()

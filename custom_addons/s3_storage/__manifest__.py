{
    "name": "S3 Attachment Storage",
    "version": "19.0.1.0.0",
    "summary": "Redirect ir.attachment filestore to AWS S3",
    "description": """
        Override ir.attachment _file_read, _file_write and _file_delete to
        store files in an S3 bucket instead of the local filestore.

        Configure via Settings → Technical → System Parameters:
        - ir_attachment.s3_bucket  — S3 bucket name (empty = local filestore)
        - ir_attachment.s3_prefix  — optional key prefix (e.g. 'prod/filestore/')
        - ir_attachment.s3_region  — AWS region (default: eu-west-1)
    """,
    "depends": ["base"],
    "data": [
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}

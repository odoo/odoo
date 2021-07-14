=======================
 S3 Attachment Storage
=======================

Installation
============

* `Using this quickstart instruction <https://boto3.readthedocs.io/en/latest/guide/quickstart.html>`__ install boto3 library and get credentials for it
* `Using this instruction <https://aws.amazon.com/ru/blogs/security/writing-iam-policies-how-to-grant-access-to-an-amazon-s3-bucket/>`__ grant access to your s3 bucket
* Set your S3 bucket as public
* Optionaly, add following parameter to prevent heavy logs from boto3 library:

    --log-handler=boto3.resources.action:WARNING


IAM
---

Minimal access policy for s3 credentials are as following::

  {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:CreateBucket",
                "s3:GetBucketLocation",
                "s3:PutObjectAcl"
            ],
            "Resource": [
                "arn:aws:s3:::YOUBUCKETNAMEHERE",
                "arn:aws:s3:::YOUBUCKETNAMEHERE/*"
            ]
        }
    ]
  }


You can also remove ``"s3:CreateBucket"`` if bucket already exists.

Configuration
=============

* `Activate developer mode <https://odoo-development.readthedocs.io/en/latest/odoo/usage/debug-mode.html>`__
* Open menu ``Settings >> Technical >> Parameters >> System Parameters`` and specify the following parameters there

  * ``s3.bucket``: the name of your bucket (e.g. ``mybucket``)
  * ``s3.condition``: only the attachments that meet the condition will be sent to s3 (e.g. ``[('res_model', 'in', ['product.image'])]``) - it is actually the way of specifying the models with ``fields.Binary`` fields that should be stored on s3 instead of local file storage or db. Don't specify anything if you want to store all your attachment data from ``fields.Binary`` and also ordinary attachments on s3.
  * ``s3.access_key_id``: S3 access key ID
  * ``s3.secret_key``: S3 secret access key
  * ``s3.endpoint_url``: optional parameter for s3-compatible storage. E.g. http://minio.example.com:9000
  * ``s3.obj_url``: optional parameter for s3-compatible storage. E.g. http://minio.example.com:9000/bucketname/

Alternatively, you can set the parameters via environmental variables: ``S3_BUCKET``, ``S3_CONDITION``, ``S3_ACCESS_KEY_ID``, ``S3_SECRET_KEY``, ``S3_ENDPOINT_URL``, ``S3_OBJ_URL``

The settings are also available from the ``Settings >> Technical >> Database Structure >> S3 Settings``.

S3
--

Minimal access policy for s3 credentials are as following::

  {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:CreateBucket",
                "s3:GetBucketLocation",
                "s3:PutObjectAcl"
            ],
            "Resource": [
                "arn:aws:s3:::YOUBUCKETNAMEHERE",
                "arn:aws:s3:::YOUBUCKETNAMEHERE/*"
            ]
        }
    ]
  }


You can also remove ``"s3:CreateBucket"`` if bucket already exists.

Usage
=====

Depending on what you have in the ``s3.condition`` setting, some or all attachments will be uploaded on your s3.
For example upload by editing product template from ``Sales >> Product`` menu some image for your product.
By doing this you have uploaded image on your s3 storage.

Upload existing attachments
---------------------------

* There are 2 ways to upload existing attachments:
  1. Open odoo shell and run `env["ir.attachment"].force_storage_s3()`
  2. Go to the ``Settings >> Technical >> Database Structure >> S3 Settings`` menu and click on the ``[Upload existing attachments]`` button there

  It is recommended to upload attachments via shell, because upload progress is visible in this method.

* To add link of existing S3 bucket object to binary fields of existing odoo records:

  * Take ``Link`` urls from Amazon. If you open ``Overview`` of the object on Amazon you should see it at the bottom of the page

  * make sure that you have properly configured your odoo, see the ``Configuration`` section of this instruction once again in the ``To enable feature of linking...`` part

  * to link objects one-by-one from an odoo backend (this option is only available for images attachments):

    * In any place where you can upload images to odoo (i.e. from ``Sales >> Sales >> Products`` when you select a product and push ``[Edit]`` button there and hover your mouse pointer under the place on a form view where an image should be)
      along with standard pencil and trash bin buttons you can see the additional ``[@]`` button. Click on this button.
    * Copy-paste your url for image and click ``[Save]`` button

  * to link objects in batch you may use default import/export feature in odoo:

    * for example, export records of model ``product.template``. Choose ``image`` field in the export dialog and save in file.
    * open the file with your favorite text editor and paste urls into ``image`` column there
    * import records from the edited CSV file
    * now when you open from ``Sales >> Sales >> Products`` your product form, you should see the image you specified by url in the file

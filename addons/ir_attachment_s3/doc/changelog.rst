`3.0.0`
-------
- **New:** support direct downloading chatter attachments

`2.1.0`
-------
- **New:** endpoint_url support (e.g. to use with minio storage)

`2.0.0`
-------
- **Improvement:** "ir.attachment.resized" model is moved to "web_image_cache" module
- **Improvement:** "Upload existing data" functionality is now also available via shell by running env["ir.attachment"].force_storage_s3()
- **Improvement:** Module is working with S3 files like binary files, but also stores url
- **Improvement:** Using virtual-hosted style addressing model instead of path-style

`1.2.2`
-------

- **Fix:** Executing S3 controller when ir_attachment_url.storage config is not s3
- **Fix:** Executing _inverse_datas when ir_attachment_url.storage config is not s3

`1.2.1`
-------

- **FIX:** Stop saving s3-related environtment variables to Odoo parameters
- **Improvement:** Correct handling with resizing product images

`1.2.0`
-------

- **Improvement:** Save resized image to s3 instead of passing original (big) image

`1.1.2`
-------

- **FIX:** there is no need to create Bucker object if there is no attachments are found to be stored on s3

`1.1.1`
-------

- **FIX:** non-supersusers cannot save attachments in s3

`1.1.0`
-------

- **NEW:** All related to s3 settings is here now ``Settings >> Technical >> Database Structure >> S3 Settings``
- **NEW:** The new ``[Upload existing attachments]`` button on the ``Settings >> Technical >> Database Structure >> S3 Settings`` form that allows to upload existing attachments that correspond to an s3 condition, but for some reason are not stored on S3 yet (i.e. attachments that was created before this module had been installed)

`1.0.0`
-------

- Init version

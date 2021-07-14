`3.0.0`
-------
- **New:** allow saving filename on uploading to external storage

`2.1.1`
-------

- **Fix:** integration with ir_attachment_s3 module

`2.1.0`
-------

- **Improvement:** Performance improvement

`2.0.1`
-------

- **Fix:** error on creating new record with Binary field

`2.0.0`
-------

- **Improvement:** Images defined by URL are now uploaded as binary files
- **Improvement:** Request to binary files with non-falsy `url` attribute return HTTP 301 response
- **Improvement:** Removed requirement of setting ir_attachment_url as server wide module
- **Discard:** Passing url to Binary/Image field is no longer supported
- **Fix:** Returing 302 instead of 301 http redirections to escape browser caching

`1.1.10`
-------

- **Improvement:** Define attachment type as URL immediately if URL given


`1.1.9`
-------

- **Fix:** Added 5 seconds timeout on retreiving remote contents
- **Improvement:** Added option to switch url storage

`1.1.8`
-------

- **Fix:**  When a link to a picture that does not have an extension is written in a binary field, its mimetype is not determined, which leads to an "binascii.Error: decoding with base64 codec failed (Error: Incorrect padding)"
- **Improvement:**  The `index_content` field is filled for attachments when a link to a file is written in a binary field.

`1.1.7`
-------

- **Fix:** Product Variant were downloaded on server instead of passing url

`1.1.6`
-------

- **Fix**  When the "image_resize_image" function was called, they received the error "binascii.Error: decoding with base64 codec failed (Error: Incorrect padding)", since the value of the binary field is the URL, not the base_64 string.

`1.1.5`
-------

- **Fix** Update of an inherited function binary_content according to original one. Update is necessary to support the work with access_token argument.

`1.1.4`
-------

- **Improvement:** exclude `ir.ui.menu` attachments from eligible to be stored outside (e.g. `ir_attachment_s3`). There is only one small web icon image in this model - no point to store it outside

`1.1.3`
-------

- **FIX:** Error when using `avatar` controller (in `mail` module). For example it is used in `website_project` on `/my/projects` page

`1.1.2`
-------

- **FIX:** Error on saving multiple URLs at once

`1.1.1`
-------

- **FIX:** Ability to use the module for res.partner model
- **FIX:** Images are displayed in kanban view correctly

`1.1.0`
-------

- **NEW:** Specify images URL from interface (e.g. product form) directly

`1.0.0`
-------

- Init version

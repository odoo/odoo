.. image:: https://itpp.dev/images/infinity-readme.png
   :alt: Tested and maintained by IT Projects Labs
   :target: https://itpp.dev

================
 Attachment Url
================

The module allows to use url in Binary fields (e.g. in product images) and
upload files to external storage (ftp, s3, some web server, etc). On requesting
that field, it pass url to client, instead of downloading binary from the
storage to odoo server and then passing to client. This allows to reduce load on
the server.

Roadmap
=======

* we may need to remove ``_compute_raw`` overriding and always redirect user to the link, instead of downloading content to odoo server. If so, url-attachments created with this module must always have ``type="binary"``

Questions?
==========

To get an assistance on this module contact us by email :arrow_right: help@itpp.dev

Contributors
============
* Ildar Nasyrov <iledarn@it-projects.info>

Further information
===================

Odoo Apps Store: https://apps.odoo.com/apps/modules/14.0/ir_attachment_url/


Tested on `Odoo 14.0 <https://github.com/odoo/odoo/commit/e9ef98410fa6acba165f3056d9c52f8e68cc768b>`_

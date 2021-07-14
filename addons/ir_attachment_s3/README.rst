.. image:: https://itpp.dev/images/infinity-readme.png
   :alt: Tested and maintained by IT Projects Labs
   :target: https://itpp.dev

=======================
 S3 Attachment Storage
=======================

* The module allows to upload the attachments in Amazon S3 automatically without storing them in Odoo database. It will allow to reduce the load on your server. Attachments will be uploaded on S3 depending on the condition you specified in Odoo settings. So you can choose and manage which type of attachments should be uploaded on S3.
* It is useful in cases where your database was crashed, because you will be able to easily restore all attachments from external storage at any time.
* The possibility to use one external storage for any number of databases.

Roadmap
=======

* In settings add options:

  * condition, if object in s3 must be stored as public (as it does now)
  * condition, if object in s3 must be stored as private and think about, how to return it to user, 'cos you cannot use link to that. Possibly read from bucket and return and uncomment this: https://github.com/it-projects-llc/misc-addons/pull/775/files#r302856876
  * how to name a file in s3 storage. As for now it is "odoo/{hash}". Maybe we could add database name to filename

* Fix these bugs (possible in ir_attachment_url):

  * After loading image url to existing product variant, image does not change in backend
  * Set image with url, then upload other image as binary file (s3), backend shows old image. It can be fixed with clearing cache. Reason: there is no 'unique' parameter in image source attribute (<img src)
  * In backend. Set product image as binary file (s3), in product page it shows new image, in product list it shows old image.
    Reason: there is no 'unique' parameter in image source attribute (<img src)
  * Using `website_sale` addon. Upload main image to product variant. Then

    * in list of products old image is shown (bug)
    * in product page main image is shown as main, previous main image is extra (maybe not a bug, but don't know how to remove previous main image)

* S3 Condition is ignored in attachment creation

Sandbox
=======

To install local minio add following specification to your docker-compose.yml::

    services:

      # ...

      minio:
        image: minio/minio
        networks: *public  # for doodba
        ports:
          - "127.0.0.1:9000:9000"
        environment:
          MINIO_ACCESS_KEY: "admin"
          MINIO_SECRET_KEY: "password"
      command:
        server /data
      volumes:
        - s3:/data:z

    volumes:

      # ...

      s3:

Add to your ``/etc/hosts`` file::

    127.0.0.1 minio

Now make minio publicly accessable:

* `install minio client <https://docs.min.io/docs/minio-client-complete-guide.html>`__, e.g.
  ::

    wget https://dl.min.io/client/mc/release/linux-amd64/mc
    chmod +x mc
* create *alias*
  ::

    ./mc alias set local http://minio:9000 admin password
* create bucket
  ::
    
    ./mc mb local/mybucket

* set policy
  ::

    ./mc policy set public local/mybucket

Then set parameters:

* ``s3.bucket``: ``mybucket``
* ``s3.access_key_id``: ``admin``
* ``s3.secret_key``: ``password``
* ``s3.endpoint_url``: ``http://minio:9000``
* ``s3.obj_url``: ``http://minio:9000/mybucket/``

Questions?
==========

To get an assistance on this module contact us by email :arrow_right: help@itpp.dev

Contributors
============

* `Ivan Yelizariev <https://twitter.com/yelizariev>`
* `Ildar Nasyrov <https://it-projects.info/team/iledarn>`
* `Kolushov Alexandr <https://it-projects.info/team/KolushovAlexandr>`
* `Dinar Gabbasov <https://it-projects.info/team/GabbasovDinar>`
* `Eugene Molotov <https://it-projects.info/team/em230418>`

===================

Odoo Apps Store: https://apps.odoo.com/apps/modules/14.0/ir_attachment_s3/


Tested on `Odoo 14.0 <https://github.com/odoo/odoo/commit/120366491f58a802deef68a17ebb26199ef829a2>`_

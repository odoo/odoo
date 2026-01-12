In some cases, you need to store attachment in another system that the
Odoo's filestore. For example, when your deployment is based on a
multi-server architecture to ensure redundancy and scalability, your
attachments must be stored in a way that they are accessible from all
the servers. In this way, you can use a shared storage system like NFS
or a cloud storage like S3 compliant storage, or....

This addon extend the storage mechanism of Odoo's attachments to allow
you to store them in any storage filesystem supported by the Python
library [fsspec](https://filesystem-spec.readthedocs.io/en/latest/) and
made available via the fs_storage addon.

In contrast to Odoo, when a file is stored into an external storage,
this addon ensures that the filename keeps its meaning (In odoo the
filename into the filestore is the file content checksum). Concretely
the filename is based on the pattern:
'\<name-without-extension\>-\<attachment-id\>-\<version\>.\<extension\>'

This addon also adds on the attachments 2 new fields to use to retrieve
the file content from a URL:

- `Internal URL`: URL to retrieve the file content from the Odoo's
  filestore.
- `Filesystem URL`: URL to retrieve the file content from the external
  storage.

Note

The internal URL is always available, but the filesystem URL is only
available when the attachment is stored in an external storage.
Particular attention has been paid to limit as much as possible the
consumption of resources necessary to serve via Odoo the content stored
in an external filesystem. The implementation is based on an end-to-end
streaming of content between the external filesystem and the Odoo client
application by default. Nevertheless, if your content is available via a
URL on the external filesystem, you can configure the storage to use the
x-sendfile mechanism to serve the content if it's activated on your Odoo
instance. In this case, the content served by Odoo at the internal URL
will be proxied to the filesystem URL by nginx.

Last but not least, the addon adds a new method open on the attachment.
This method allows you to open the attachment as a file. For attachments
stored into the filestore or in an external filesystem, it allows you to
directly read from and write to the file and therefore minimize the
memory consumption since data are not kept into memory before being
written into the database.

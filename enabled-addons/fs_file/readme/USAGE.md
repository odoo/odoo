The new field **FSFile** has been developed to allows you to store files
in an external filesystem storage. Its design is based on the following
principles:

- The content of the file must be read from the filesystem only when
  needed.
- It must be possible to manipulate the file content as a stream by
  default.
- Unlike Odoo's Binary field, the content is the raw file content by
  default (no base64 encoding).
- To allows to exchange the file content with other systems, writing the
  content as base64 is possible. The read operation will return a json
  structure with the filename, the mimetype, the size and a url to
  download the file.

This design allows to minimize the memory consumption of the server when
manipulating large files and exchanging them with other systems through
the default jsonrpc interface.

Concretely, this design allows you to write code like this:

``` python
from IO import BytesIO
from odoo import models, fields
from odoo.addons.fs_file.fields import FSFile

class MyModel(models.Model):
    _name = 'my.model'

    name = fields.Char()
    file = FSFile()

# Create a new record with a raw content
my_model = MyModel.create({
    'name': 'My File',
    'file': BytesIO(b"content"),
})

assert(my_model.file.read() == b"content")

# Create a new record with a base64 encoded content
my_model = MyModel.create({
    'name': 'My File',
    'file': b"content".encode('base64'),
})
assert(my_model.file.read() == b"content")

# Create a new record with a file content
my_model = MyModel.create({
    'name': 'My File',
    'file': open('my_file.txt', 'rb'),
})
assert(my_model.file.read() == b"content")
assert(my_model.file.name == "my_file.txt")

# create a record with a file content as base64 encoded and a filename
# This method is useful to create a record from a file uploaded
# through the web interface.
my_model = MyModel.create({
    'name': 'My File',
    'file': {
        'filename': 'my_file.txt',
        'content': base64.b64encode(b"content"),
    },
})
assert(my_model.file.read() == b"content")
assert(my_model.file.name == "my_file.txt")

# write the content of the file as base64 encoded and a filename
# This method is useful to update a record from a file uploaded
# through the web interface.
my_model.write({
    'file': {
        'name': 'my_file.txt',
        'file': base64.b64encode(b"content"),
    },
})

# the call to read() will return a json structure with the filename,
# the mimetype, the size and a url to download the file.
info = my_model.file.read()
assert(info["file"] == {
    "filename": "my_file.txt",
    "mimetype": "text/plain",
    "size": 7,
    "url": "/web/content/1234/my_file.txt",
})

# use the field as a file stream
# In such a case, the content is read from the filesystem without being
# stored in memory.
with my_model.file.open("rb) as f:
  assert(f.read() == b"content")

# use the field as a file stream to write the content
# In such a case, the content is written to the filesystem without being
# stored in memory. This kind of approach is useful to manipulate large
# files and to avoid to use too much memory.
# Transactional behaviour is ensured by the implementation!
with my_model.file.open("wb") as f:
    f.write(b"content")
```

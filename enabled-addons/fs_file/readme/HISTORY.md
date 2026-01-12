## 16.0.1.0.6 (2024-02-23)

**Bugfixes**

- Fixes the creation of empty files.

  Before this change, the creation of empty files resulted in a
  constraint violation error. This was due to the fact that even if a
  name was given to the file it was not preserved into the FSFileValue
  object if no content was given. As result, when the corresponding
  ir.attachment was created in the database, the name was not set and
  the 'required' constraint was violated.
  ([\#341](https://github.com/OCA/storage/issues/341))

## 16.0.1.0.5 (2023-11-30)

**Bugfixes**

- Ensure the cache is properly set when a new value is assigned to a
  FSFile field. If the field is stored the value to the cache must be a
  FSFileValue object linked to the attachment record used to store the
  file. Otherwise the value must be one given since it could be the
  result of a compute method.
  ([\#290](https://github.com/OCA/storage/issues/290))

## 16.0.1.0.4 (2023-10-17)

**Bugfixes**

- Browse attachment with sudo() to avoid read access errors

  In models that have a multi fs image relation, a new line in form will
  trigger onchanges and will call the fs.file model 'convert_to_cache()'
  method that will try to browse the attachment with user profile that
  could have no read rights on attachment model.
  ([\#288](https://github.com/OCA/storage/issues/288))

## 16.0.1.0.3 (2023-10-05)

**Bugfixes**

- Fix the *mimetype* property on *FSFileValue* objects.

  The *mimetype* value is computed as follow:

  - If an attachment is set, the mimetype is taken from the attachment.
  - If no attachment is set, the mimetype is guessed from the name of
    the file.
  - If the mimetype cannot be guessed from the name, the mimetype is
    guessed from the content of the file.
    ([\#284](https://github.com/OCA/storage/issues/284))

## 16.0.1.0.1 (2023-09-29)

**Features**

- Add a *url_path* property on the *FSFileValue* object. This property
  allows you to easily get access to the relative path of the file on
  the filesystem. This value is only available if the filesystem storage
  is configured with a *Base URL* value.
  ([\#281](https://github.com/OCA/storage/issues/281))

**Bugfixes**

- The *url_path*, *url* and *internal_url* properties on the
  *FSFileValue* object return *None* if the information is not available
  (instead of *False*).

  The *url* property on the *FSFileValue* object returns the filesystem
  url nor the url field of the attachment.
  ([\#281](https://github.com/OCA/storage/issues/281))

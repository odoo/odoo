## 16.0.1.0.3 (2024-02-23)

**Bugfixes**

- ([\#305](https://github.com/OCA/storage/issues/305))

## 16.0.1.0.2 (2023-12-02)

**Bugfixes**

- Fix view crash when uploading an image

  The rawCacheKey is appropriately managed by the base class and
  reflects the record's last update datetime (write_date). Since it
  lacks a setter, attempting to invalidate its value results in a view
  crash. Nevertheless, the value will automatically be updated upon
  saving the record.
  ([\#305](https://github.com/OCA/storage/issues/305))

## 16.0.1.0.1 (2023-12-02)

**Bugfixes**

- Avoid to generate an SQL update query when an image field is read.

  Fix a bug in the initialization of the image field value object when
  the field is read. Before this fix, every time the value object was
  initialized with an attachment, an assignment of the alt text was done
  into the constructor. This assignment triggered the mark of the field
  as modified and an SQL update query was generated at the end of the
  request. The alt text in the constructor of the FSImageValue class
  must only be used when the class is initialized without an attachment.
  We now check if an attachment and an alt text are provided at the same
  time and throw an exception if this is the case.
  ([\#307](https://github.com/OCA/storage/issues/307))

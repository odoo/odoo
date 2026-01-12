## 18.0.2.2.0 (2025-10-20)

### Features

- Adapt to handle {db_name} in directory_path. ([#db_name](https://github.com/OCA/storage/issues/db_name))


## 18.0.1.1.0 (2024-11-10)

### Bugfixes

- No crash o missign file.

  Prior to this change, Odoo was crashing as soon as access to a file stored into
  an external filesytem was not possible. This can lead to a complete system block.
  This change prevents this kind of blockage by ignoring access error to files
  stored into external system on read operations. These kind of errors are logged
  into the log files for traceability. ([#361](https://github.com/OCA/storage/issues/361))


## 16.0.1.0.8 (2023-12-20)

**Bugfixes**

- Fix the error retrieving attachment files when the storage is set to
  optimize directory paths.
  ([\#312](https://github.com/OCA/storage/issues/312))

## 16.0.1.0.6 (2023-12-02)

**Bugfixes**

- Improve performance at creation of an attachment or when the
  attachment is updated.

  Before this change, when the fs_url was computed the computed value
  was always reassigned to the fs_url attribute even if the value was
  the same. In a lot of cases the value was the same and the
  reassignment was not necessary. Unfortunately this reassignment has as
  side effect to mark the record as dirty and generate a SQL update
  statement at the end of the transaction.
  ([\#307](https://github.com/OCA/storage/issues/307))

## 16.0.1.0.5 (2023-11-29)

**Bugfixes**

- When manipulating the file system api through a local variable named
  *fs*, we observed some strange behavior when it was wrongly redefined
  in an enclosing scope as in the following example: *with fs.open(...)
  as fs*. This commit fixes this issue by renaming the local variable
  and therefore avoiding the name clash.
  ([\#306](https://github.com/OCA/storage/issues/306))

## 16.0.1.0.4 (2023-11-22)

**Bugfixes**

- Fix error when an url is computed for an attachment in a storage
  configure wihtout directory path.
  ([\#302](https://github.com/OCA/storage/issues/302))

## 16.0.1.0.3 (2023-10-17)

**Bugfixes**

- Fix access to technical models to be able to upload attachments for
  users with basic access
  ([\#289](https://github.com/OCA/storage/issues/289))

## 16.0.1.0.2 (2023-10-09)

**Bugfixes**

- Ensures python 3.9 compatibility.
  ([\#285](https://github.com/OCA/storage/issues/285))
- If a storage is not used to store all the attachments by default, the
  call to the get_force_db_for_default_attachment_rules method must
  return an empty dictionary.
  ([\#286](https://github.com/OCA/storage/issues/286))

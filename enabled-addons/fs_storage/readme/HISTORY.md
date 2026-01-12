## 18.0.2.1.0 (2025-10-20)

### Features

- Replace {db_name} by the database name in directory_path ([#db_name](https://github.com/OCA/storage/issues/db_name))


## 18.0.2.0.1 (2025-07-23)

### Features

- Allow setting check_connection_method in configuration file.


## 18.0.1.0.1 (2024-11-10)

### Features

- Invalidate FS filesystem object cache when the connection fails, forcing a reconnection. ([#320](https://github.com/OCA/storage/issues/320))


## 16.0.1.1.0 (2023-12-22)

**Features**

- Add parameter on storage backend to resolve protocol options values
  starting with \$ from environment variables
  ([\#303](https://github.com/OCA/storage/issues/303))

## 16.0.1.0.3 (2023-10-17)

**Bugfixes**

- Fix access to technical models to be able to upload attachments for
  users with basic access
  ([\#289](https://github.com/OCA/storage/issues/289))

## 16.0.1.0.2 (2023-10-09)

**Bugfixes**

- Avoid config error when using the webdav protocol. The auth option is
  expected to be a tuple not a list. Since our config is loaded from a
  json file, we cannot use tuples. The fix converts the list to a tuple
  when the config is related to a webdav protocol and the auth option is
  into the confix. ([\#285](https://github.com/OCA/storage/issues/285))

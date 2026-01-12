This addon is a technical addon that allows you to define filesystem
like storage for your data. It's used by other addons to store their
data in a transparent way into different kind of storages.

Through the fs.storage record, you get access to an object that
implements
the [fsspec.spec.AbstractFileSystem](https://filesystem-spec.readthedocs.io/en/latest/api.html#fsspec.spec.AbstractFileSystem)
interface and
therefore give you an unified interface to access your data whatever the
storage protocol you decide to use.

The list of supported protocols depends on the installed fsspec
implementations. By default, the addon will install the following
protocols:

- LocalFileSystem
- MemoryFileSystem
- ZipFileSystem
- TarFileSystem
- FTPFileSystem
- CachingFileSystem
- WholeFileSystem
- SimplCacheFileSystem
- ReferenceFileSystem
- GenericFileSystem
- DirFileSystem
- DatabricksFileSystem
- GitHubFileSystem
- JupiterFileSystem
- OdooFileSystem

The OdooFileSystem is the one that allows you to store your data into a
directory mounted into your Odoo's storage directory. This is the
default FS Storage when creating a new fs.storage record.

Others protocols are available through the installation of additional
python packages:

- DropboxDriveFileSystem -\> pip install fsspec\[dropbox\]
- HTTPFileSystem -\> pip install fsspec\[http\]
- HTTPSFileSystem -\> pip install fsspec\[http\]
- GCSFileSystem -\> pip install fsspec\[gcs\]
- GSFileSystem -\> pip install fsspec\[gs\]
- GoogleDriveFileSystem -\> pip install gdrivefs
- SFTPFileSystem -\> pip install fsspec\[sftp\]
- HaddoopFileSystem -\> pip install fsspec\[hdfs\]
- S3FileSystem -\> pip install fsspec\[s3\]
- WandbFS -\> pip install wandbfs
- OCIFileSystem -\> pip install fsspec\[oci\]
- AsyncLocalFileSystem -\> pip install 'morefs\[asynclocalfs\]
- AzureDatalakeFileSystem -\> pip install fsspec\[adl\]
- AzureBlobFileSystem -\> pip install fsspec\[abfs\]
- DaskWorkerFileSystem -\> pip install fsspec\[dask\]
- GitFileSystem -\> pip install fsspec\[git\]
- SMBFileSystem -\> pip install fsspec\[smb\]
- LibArchiveFileSystem -\> pip install fsspec\[libarchive\]
- OSSFileSystem -\> pip install ossfs
- WebdavFileSystem -\> pip install webdav4
- DVCFileSystem -\> pip install dvc
- XRootDFileSystem -\> pip install fsspec-xrootd

This list of supported protocols is not exhaustive or could change in
the future depending on the fsspec releases. You can find more
information about the supported protocols on the [fsspec
documentation](https://filesystem-spec.readthedocs.io/en/latest/api.html#fsspec.spec.AbstractFileSystem).

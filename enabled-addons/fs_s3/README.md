# FS S3 Storage

Amazon S3 backend for fs_storage module.

## Features

- Full S3 protocol support
- Compatible with AWS S3
- Compatible with S3-compatible services (LocalStack, MinIO, etc)
- Multi-tenant support via directory paths
- Configurable endpoints and regions

## Configuration

After installing the module, create a new FS Storage:

1. Go to: Settings → Technical → Storage → FS Storages
2. Create new storage:
   - Protocol: Amazon S3
   - AWS Access Key ID: your-access-key
   - AWS Secret Access Key: your-secret-key
   - AWS Region: us-east-1
   - AWS S3 Bucket Name: your-bucket
   - AWS S3 Endpoint URL: (optional, for LocalStack/MinIO)
   - Use HTTPS: checked (uncheck for LocalStack)
   - Directory Path: (optional, for multi-tenant isolation)

## Requirements

- fsspec >= 2024.5.0
- s3fs >= 2024.5.0
- boto3 >= 1.34.0

## Credits

- ACSONE SA/NV
- Odoo Community Association (OCA)

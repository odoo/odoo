import json
from urllib.parse import quote

import boto3
from botocore.exceptions import ClientError

from odoo.exceptions import UserError

PARAM_BUCKET = "cloud_storage_s3_bucket_name"
PARAM_REGION = "cloud_storage_s3_region"
CREDENTIAL_CATEGORY_XMLID = "cloud_storage_s3.credential_category_cloud_storage_s3"
CREDENTIAL_NAME = "Cloud Storage S3"

_ClientCache = {}


def get_credential(env):
    category = env.ref(CREDENTIAL_CATEGORY_XMLID, raise_if_not_found=False)
    if not category:
        return env["credential.credential"].sudo()
    return (
        env["credential.credential"]
        .sudo()
        .search(
            [("category_id", "=", category.id), ("active", "=", True)],
            order="write_date desc, id desc",
            limit=1,
        )
    )


def get_keys(env):
    credential = get_credential(env)
    keys = credential.get_credential_dict() if credential else {}
    if not (keys.get("access_key_id") and keys.get("secret_access_key")):
        return {}
    return keys


def store_keys(env, access_key_id, secret_access_key):
    payload = json.dumps(
        {"access_key_id": access_key_id, "secret_access_key": secret_access_key}
    )
    credential = get_credential(env)
    if credential:
        credential.credential_data = payload
    else:
        env["credential.credential"].sudo().create(
            {
                "name": CREDENTIAL_NAME,
                "category_id": env.ref(CREDENTIAL_CATEGORY_XMLID).id,
                "credential_data": payload,
            }
        )
    clear_cache(env)


def get_config(env):
    icp = env["ir.config_parameter"].sudo()
    credential = get_credential(env)
    config = {
        "bucket_name": icp.get_param(PARAM_BUCKET),
        "region": icp.get_param(PARAM_REGION),
        "credential": f"{credential.id}:{credential.write_date}"
        if credential and credential.storage_method == "json"
        else False,
    }
    return config if all(config.values()) else {}


def get_client(env):
    config = get_config(env)
    if not config:
        raise UserError(
            env._(
                "Amazon S3 is not fully configured: set the bucket, region and "
                "IAM keys in Settings → Cloud Storage."
            )
        )
    signature = (config["region"], config["credential"])
    db_name = env.registry.db_name
    cached_signature, cached_client = _ClientCache.get(db_name, (None, None))
    if cached_signature == signature and cached_client:
        return cached_client
    keys = get_keys(env)
    if not keys:
        raise UserError(env._("The Amazon S3 IAM keys are missing or unreadable."))
    client = boto3.client(  # noqa: E8518 - botocore opens its own connections and takes no requests session
        "s3",
        aws_access_key_id=keys["access_key_id"],
        aws_secret_access_key=keys["secret_access_key"],
        region_name=config["region"],
    )
    _ClientCache[db_name] = (signature, client)
    return client


def clear_cache(env=None):
    if env is None:
        _ClientCache.clear()
    else:
        _ClientCache.pop(env.registry.db_name, None)


def object_exists(client, bucket, key):
    try:
        client.head_object(Bucket=bucket, Key=key)
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") in (
            "404",
            "NoSuchKey",
            "NotFound",
        ):
            return False
        raise
    return True


def object_url(bucket, region, key):
    return f"https://{bucket}.s3.{region}.amazonaws.com/{quote(key)}"

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from urllib.parse import quote

from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError

from .. import uninstall_hook


class TestCloudStorageGoogleCommon(TransactionCase):
    def setUp(self):
        super().setUp()
        self.DUMMY_GOOGLE_ACCOUNT_INFO = r'''
{
    "type": "service_account",
    "project_id": "project_id",
    "private_key_id": "1234",
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCjmpzbYZQpiCSN\nQAw45TLENOyz27cPwY6hC3JD6ceHlblGpB4I2vVvRf7Qmv5Uv1oK7C5OfHUU7MmC\nfIaJfDlxciZrtTCCuCidm569tOgv57/DY+L3MFpQrIjSG2SiFO6LncqbZ74u4K7b\nABu3AheCFtZLGh0DyXA6wsv6tZuz4HC5UKDGEVc0wD8ZESmgPRXiY9IWKcEmRp3m\nbLv7gBT6j1zOrtLlxmU/gCzHPnBzJyPhl6Hxufj7Fmnkq84BfiMo8tEjQAIkS3RR\nSG7aP+GdOx1MEd5wKBT5bOrJX9+61CqAE6LupnTiAzt4iDDUQdRxaN1aQ3Q0MxrE\nzpRSawZbAgMBAAECggEALnN2KMWuSxJ4ClDOh5Lv1IyQTkrKUaNrqyb0VPr553Gn\nzrpHOs1sVSEjBbiUEJzZ5HMFfMxSc9P9LNrNWhjWuHKoHPmvYdYG1iT6r7M/H2bl\n6ASiyvtEEVbDbCBR9MELr8Fn5rLQaT/q9Yw00kO6R/nS8zThWxNlFZH8V10b7biN\na6EQr8udA4zUhYy+m3bnX47kBWFmXp8zJl4zHm70eT+WDurN8O3oMqcimozWFnsz\nT4QTJn6WKoVKQ5CAHRTf9iRH0FFzeWLkNZQmYY4pEljKajgvGyfQfAKXWuRIveGQ\nI5TOwvbDNtb+bDdvzD/hFi0EhjKGrV97yqdcvNHPOQKBgQDkn1lEu2V741tMa6s+\n80KySMfynJ4yH0KSR+NGp4jhVqP6MKL5imk9TO5E9WwrNrQjJErnmblURp6SnZPL\nrXi8ngmFq6Bdp+jMtpdlZZa5zKryGyyfDABrHZTSVXZloP1qA0DO45uFfH0b137W\nJsELXHNUx2u/jBraoOK0W/rXAwKBgQC3Mg537ImTHUEJ81GmL591YDGNBR68uVS2\nB866v5z+E/oIfUbhFeqHyMFPzJnf/MfWQImv1O9HWWtDJgJhFaZcRaocvn5mQRj6\n2Mhpgq+1nD5oqT+JRDXPw6ESmxz8E4wddF68BmYrDKUjGZsT3sSEkRoertpc2Sc1\nwhK4xVJnyQKBgAcyWO4H9B7dPk9+iCp4H95a2ihx86ziPQc7yhS8S1vEjW7fvxGZ\n4Mw0Mr/q9de6ZhtBFjaKKUJU4sL8wN1Ffap6UxRpHag1E+f1y3g+pWr93Ve3sUTk\nbNLyYG/qjsqOMcv3hD++/HNMQufwdaaqG6OO6nZ9vI+QCnxdWiWRS6kfAoGAV+6F\n9VgrHNsg2cbZ/RvEvVFD132KqGmI2KrcttS8ZVRvYl3HhMjBPxXEfCon/dRWk2d8\n71IU3Dl2e8+lurXqmUWzBoMFJs2+UMF3SPW6o0Bw0EnUvm1oKuaqzMR5YCF90rGF\nu1iS97zlEvj6b8owp7UCRZIGLCTrZilWVSwZhskCgYEA43vM7PzBf7FZANZEaZlz\nt4LjgJMLEfUeL7XULqx5jNqR9oLNFANgHRr1t/NknJsrmg/8BUEK39Xs9qz7Vkkh\nanXqyrE2o65I7a6AMXostCDmBeIhk4diYAZARWtPLTHf5YCb0N7/llOmmx3rDP+r\n8Ij56mh2K6CodWbFby9GjNY=\n-----END PRIVATE KEY-----\n",
    "client_email": "account@project_id.iam.gserviceaccount.com",
    "client_id": "1234",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/account%40project_id.iam.gserviceaccount.com",
    "universe_domain": "googleapis.com"
}
'''
        self.bucket_name = 'bucket_name'
        ICP = self.env['ir.config_parameter']
        ICP.set_param('cloud_storage_provider', 'google')
        ICP.set_param('cloud_storage_google_bucket_name', self.bucket_name)
        ICP.set_param('cloud_storage_google_account_info', self.DUMMY_GOOGLE_ACCOUNT_INFO)


class TestCloudStorageGoogle(TestCloudStorageGoogleCommon):
    def test_generate_signed_url(self):
        file_name = ' ¥®°²Æçéðπ⁉€∇⓵▲☑♂♥✓➔『にㄅ㊀中한︸🌈🌍👌😀.txt'
        attachment = self.env['ir.attachment'].create([{
            'name': file_name,
            'mimetype': 'text/plain',
            'datas': b'',
        }])
        attachment._post_add_create(cloud_storage=True)
        attachment._generate_cloud_storage_upload_info()
        attachment._generate_cloud_storage_download_info()
        self.assertTrue(attachment.url.startswith(f'https://storage.googleapis.com/{self.bucket_name}/'))
        self.assertTrue(attachment.url.endswith(quote(file_name)))

    def test_uninstall_fail(self):
        with self.assertRaises(UserError, msg="Don't uninstall the module if there are Google attachments in use"):
            attachment = self.env['ir.attachment'].create([{
                'name': 'test.txt',
                'mimetype': 'text/plain',
                'datas': b'',
            }])
            attachment._post_add_create(cloud_storage=True)
            attachment.flush_recordset()
            uninstall_hook(self.env)

    def test_uninstall_success(self):
        uninstall_hook(self.env)
        # make sure all sensitive data are removed
        ICP = self.env['ir.config_parameter']
        self.assertFalse(ICP.get_param('cloud_storage_provider'))
        self.assertFalse(ICP.get_param('cloud_storage_google_bucket_name'))
        self.assertFalse(ICP.get_param('cloud_storage_google_account_info'))

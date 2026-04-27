import json
import requests
from contextlib import contextmanager
from unittest.mock import patch

from odoo.addons.base.tests.test_ir_cron import CronMixinCase
from odoo.addons.social.tests.common import SocialCase
from odoo.addons.social.tests.tools import mock_void_external_calls


class SocialInstagramCommon(SocialCase, CronMixinCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with mock_void_external_calls():
            cls.social_accounts.write({
                'instagram_account_id': 'instagram_account_id',
                'instagram_access_token': 'instagram_access_token',
            })

    @classmethod
    def _get_social_media(cls):
        return cls.env.ref('social_instagram.social_media_instagram')

    @contextmanager
    def mock_instagram_api(self, status='FINISHED', media_id='ig_media_id'):
        state = {'container_counter': 0}

        def _patched_post(url, *args, **kwargs):
            response = requests.Response()
            response.status_code = 200
            if 'media_publish' in url:
                response._content = json.dumps({'id': media_id}).encode()
            elif '/media' in url:
                container_id = f'{media_id}_{state["container_counter"]}'
                state['container_counter'] += 1
                response._content = json.dumps({'id': container_id}).encode()
            return response

        def _patched_get(url, *args, **kwargs):
            params = kwargs.get('params', {})
            fields = params.get('fields', '').split(',')
            response = requests.Response()
            if 'ig_id' in fields and status != 'PUBLISHED':
                response.status_code = 400
                response._content = json.dumps({'error': {'message': 'Tried accessing nonexisting field (ig_id)'}}).encode()
                return response

            response.status_code = 200
            response_data = {'id': url.split('/')[-1]}
            if 'status_code' in fields:
                response_data['status_code'] = status
            if 'ig_id' in fields:
                response_data['ig_id'] = media_id
            response._content = json.dumps(response_data).encode()
            return response

        with patch.object(requests.Session, 'post', side_effect=_patched_post), \
             patch.object(requests.Session, 'get', side_effect=_patched_get):
            yield

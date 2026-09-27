import logging
import requests

from odoo import _
from odoo.exceptions import UserError
from odoo.tools import human_size
from odoo.tools.urls import urljoin

from werkzeug.urls import url_encode

_logger = logging.getLogger(__name__)


class LinkedInAPI:
    API_ENDPOINT = 'https://api.linkedin.com/v2'
    OAUTH_ENDPOINT = 'https://www.linkedin.com/oauth/v2'

    def __init__(self, env, access_token=None):
        self._access_token = access_token
        self._app_id = None
        self._app_secret = None
        self._db_uuid = None
        self._iap_endpoint = None
        ConfigParameterSudo = env['ir.config_parameter'].sudo()
        if ConfigParameterSudo.get_bool('social.linkedin_use_own_account'):
            self._app_id = ConfigParameterSudo.get_str('social.linkedin_app_id')
            self._app_secret = ConfigParameterSudo.get_str('social.linkedin_client_secret')
        else:
            self._db_uuid = ConfigParameterSudo.get_str('database.uuid')
            self._iap_endpoint = ConfigParameterSudo.get_str('social.social_iap_endpoint') or 'https://social.api.odoo.com'

    def _get_headers(self):
        if not self._access_token:
            raise UserError(_('You must be authentified with LinkedIn to do this.'))
        return {
            'Authorization': f'Bearer {self._access_token}',
        }

    def get_authorization_url(self, redirect_uri, state, scope):
        """Get an authorization url for a user to give their consent for the requested scopes.

        This requires either LinkedIn app credentials, set on the same parameters as the social linkedin app.
        Or an odoo subscription to use the IAP route, without any need for user configuration.

        :param redirect_uri: uri where to redirect the user after they give (or not) their consent.
        :param state: any string we may want to retrieve when the user is redirected after giving their consent.
        :param scope: a comma-separated list of linkedin oauth scopes, such as 'openid' to get their profile name.
        :return: a url to the page where users will need to log in and give their consent.
        """
        if self._app_id:
            params = {
                'client_id': self._app_id,
                'redirect_uri': redirect_uri,
                'response_type': 'code',
                'state': state,
                'scope': scope,
            }
            return f'{self.OAUTH_ENDPOINT}/authorization?{url_encode(params)}'

        iap_response = requests.get(urljoin(self._iap_endpoint, 'api/social/linkedin/1/add_accounts'), params={
            'state': state,
            'scope': scope,
            'o_redirect_uri': redirect_uri,
            'db_uuid': self._db_uuid,
        }, timeout=5).text
        if iap_response in ('unauthorized', 'linkedin_missing_configuration', 'missing_parameters'):
            raise UserError(_('Error on generating an authorization url: %(iap_error_string)s', iap_error_string=iap_response))
        return iap_response

    def fetch_access_token(self, linkedin_authorization_code, redirect_uri):
        """Fetch an access token for the requested scopes for the user performing the authentication.

        :param linkedin_authorization_code: a code received from linkedin representing the consent of the user.
        :param redirect_uri: the uri to which the user was redirected when they gave their consent. Must be the same as get_authorization_url.
        :return: the access token, which can be safely ignored unless the caller needs to store it outside of this object.
        """
        if not self._app_id:
            raise UserError(_('Missing LinkedIn app credentials.'))

        linkedin_url = f'{self.OAUTH_ENDPOINT}/accessToken'

        params = {
            'grant_type': 'authorization_code',
            'code': linkedin_authorization_code,
            'redirect_uri': redirect_uri,
            'client_id': self._app_id,
            'client_secret': self._app_secret
        }

        response = requests.post(linkedin_url, data=params, timeout=5).json()

        error_description = response.get('error_description')
        if error_description:
            _logger.warning('Fetching of LinkedIn access token from authorization code failed with: %s', error_description)
            raise UserError(error_description)

        self._access_token = response.get('access_token')
        return self._access_token

    def get_user_info(self):
        """Retrieve id, name and profile picture url from a user using a basic openid authentication token."""
        response = requests.get(f'{self.API_ENDPOINT}/userinfo', headers=self._get_headers(), timeout=5)

        if not response.ok:
            _logger.warning('Fetching of LinkedIn user info via openid failed with HTTP %d:\n%s', response.status_code, response.text)
            raise UserError(_('Error when fetching user info'))

        return response.json()

    def upload_image(self, image_bytes, owner_id):
        """Upload an image as an asset that can be posted with an ugcPost request, returning its unique resource name.

        :param image_bytes: Bytes representing a valid jpeg, png or gif image. At most 100MB.
        :param owner_id: unique resource id of the send (only the id part, expecting a person)
        :return: full urn of the uploaded image
        """
        if len(image_bytes) > 100_000_000:
            raise UserError(_('The image is too large: %(image_size_human_readable)s', human_size(len(image_bytes))))

        headers = self._get_headers()
        upload_registration_res = requests.post(f'{self.API_ENDPOINT}/assets?action=registerUpload', headers=headers, json={
            'registerUploadRequest': {
                'recipes': ['urn:li:digitalmediaRecipe:feedshare-image'],
                'owner': f'urn:li:person:{owner_id}',
                'serviceRelationships': [{
                    'relationshipType': 'OWNER',
                    'identifier': 'urn:li:userGeneratedContent'
                }]
            }
        }, timeout=5)
        if not upload_registration_res.ok:
            _logger.warning(
                'Registering of upload of an image to LinkedIn failed with HTTP %d:\n%s',
                upload_registration_res.status_code, upload_registration_res.text,
            )
            raise UserError(_('Error when registering an image upload'))

        upload_registration = upload_registration_res.json()
        upload_url = upload_registration['value']['uploadMechanism']['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
        image_urn = upload_registration['value']['asset']

        upload_res = requests.put(upload_url, headers=headers, data=image_bytes, timeout=20)
        if not upload_res.ok:
            _logger.warning('Uploading of an image to LinkedIn failed with HTTP %d:\n%s', upload_res.status_code, upload_res.text)
            raise UserError(_('Error when uploading an image'))
        return image_urn

    def post_image(self, author_id, image_bytes, image_title, text="", image_description=""):
        """Post 1 image and some text on the author's public feed.

        :param author_id: urn id of the author, expected to be a person.
        :param image_bytes: Bytes representing the image.
        :param image_title: name of the image.
        :param text: optional text to post along with the image.
        :param image_description: image alt description for accessibility.
        :return: Response of the call as a dict, notably containing the id of the post.
        """
        image_urn = self.upload_image(image_bytes, owner_id=author_id)
        media_object = {
            'status': 'READY',
            'media': image_urn,
            'title': {
                'text': image_title,
            }
        }
        if image_description:
            media_object['description'] = {'text': image_description}

        response = requests.post(
            f'{self.API_ENDPOINT}/ugcPosts',
            headers=self._get_headers(),
            timeout=5,
            json={
                'author': f'urn:li:person:{author_id}',
                'lifecycleState': 'PUBLISHED',
                'specificContent': {
                    'com.linkedin.ugc.ShareContent': {
                        'shareCommentary': {
                            'text': text or '',
                        },
                        'shareMediaCategory': 'IMAGE',
                        'media': [media_object]
                    }
                },
                'visibility': {
                    'com.linkedin.ugc.MemberNetworkVisibility': 'PUBLIC'
                }
            }
        )
        if not response.ok:
            _logger.warning('Posting an image on LinkedIn failed with HTTP %d:\n%s', response.status_code, response.text)
            raise UserError(_('Error when posting an image'))
        return response.json().get('id')

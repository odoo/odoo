import requests
import werkzeug

from odoo.addons.web_unsplash.controllers import main
from odoo import http
from odoo.http import request

# ID of the unsplash collection, used as a fallback for knowledge covers when we can't find a suitable image
UNSPLASH_COLLECTION_ID = 317099

class KnowledgeUnsplash(main.Web_Unsplash):

    @http.route('/knowledge/article/<model("knowledge.article"):article>/add_random_cover', type='json', auth='user')
    def add_random_cover(self, article, **kwargs):
        """ This route will try to fetch a random image from unsplash using the
        params in kwargs. If successful, the image will be saved as a knowledge
        cover, and added as cover of the article given in the params.
        """
        if not article.has_access('write'):
            raise werkzeug.exceptions.Forbidden()

        # Fetch a random image
        access_key = self._get_access_key()
        app_id = self.get_unsplash_app_id()
        # Return errors so that client knows it needs to open the CoverSelector
        # Associated values could be used in the future to adapt client behaviour wr to the error
        if not access_key or not app_id:
            return {'error': 'key_not_found'}
        kwargs['client_id'] = access_key

        q = kwargs.pop('query', None)
        params_seq = filter(None, [
            {**kwargs, 'query': q} if q else {},
            {**kwargs, 'collections': UNSPLASH_COLLECTION_ID},
        ])
        fetch_random_image_request = None
        for params in params_seq:
            try:
                fetch_random_image_request = requests.get('https://api.unsplash.com/photos/random', params=params, timeout=5)
            except requests.exceptions.RequestException:
                return {'error': 'request_failed'}
            if fetch_random_image_request.ok:
                break
        else:
            return {'error': fetch_random_image_request.status_code}

        image_info = fetch_random_image_request.json()

        # Save image
        attachment = self.save_unsplash_url({
            image_info['id']: {
                'url': image_info['urls']['regular'],
                'download_url': image_info['links']['download_location'],
                'description': image_info['alt_description'],
            }
        }, res_model='knowledge.cover', **kwargs)[0]

        # Create new cover using new attachment
        cover = request.env['knowledge.cover'].create({'attachment_id': attachment['id']})
        return {'cover_id': cover['id']}

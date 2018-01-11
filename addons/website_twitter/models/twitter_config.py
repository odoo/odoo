import logging

from openerp.osv import fields, osv
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)

class twitter_config_settings(osv.osv_memory):
    _inherit = 'website.config.settings'

    _columns = {
         'twitter_api_key': fields.related(
                'website_id', 'twitter_api_key', type="char",
                string='Twitter API Key',
                help="Twitter API key you can get it from https://apps.twitter.com/app/new"),
         'twitter_api_secret': fields.related(
                'website_id', 'twitter_api_secret', type="char",
                string='Twitter API secret',
                help="Twitter API secret you can get it from https://apps.twitter.com/app/new"),
         'twitter_tutorial': fields.dummy(
                type="boolean", string="Show me how to obtain the Twitter API Key and Secret"),
         'twitter_screen_name': fields.related(
                'website_id', 'twitter_screen_name',
                type="char", string='Get favorites from this screen name',
                help="Screen Name of the Twitter Account from which you want to load favorites."
                "It does not have to match the API Key/Secret."),
    }
    
    def _check_twitter_authorization(self, cr, uid, config_id, context=None):
        website_obj = self.pool['website']
        website_config = self.browse(cr, uid, config_id, context=context)
        try:
            website_obj.fetch_favorite_tweets(cr, uid, [website_config.website_id.id], context=context)
        except Exception:
            _logger.warning('Failed to verify twitter API authorization', exc_info=True)
            raise osv.except_osv(_('Twitter authorization error!'), _('Please double-check your Twitter API Key and Secret'))

    def create(self, cr, uid, vals, context=None):
        res_id = super(twitter_config_settings, self).create(cr, uid, vals, context=context)
        if vals.get('twitter_api_key') and vals.get('twitter_api_secret'):
            self._check_twitter_authorization(cr, uid, res_id, context=context)
        return res_id
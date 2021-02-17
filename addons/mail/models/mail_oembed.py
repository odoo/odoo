# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import html
import requests
import json
from urllib.parse import urlparse
from pathlib import Path

from odoo import api, models, fields, tools

class oEmbed(models.Model):
    _name = 'mail.oembed'
    _description = "Store oembed link data's"

    attachment_id = fields.Many2one('ir.attachment', 'Attachement previewed', index=True, ondelete='cascade')
    json = fields.Text('oembed')
    type = fields.Char('type')
    # We do not use an Html field here because they are too restrictive. We
    # need to remove <script> but allow iframe's
    html = fields.Text('html')
    url = fields.Char('url')
    width = fields.Char('width')
    height = fields.Char('height')
    thumbnail_url = fields.Char('thumbnail_url')
    thumbnail_width = fields.Char('thumbnail_width')
    thumbnail_height = fields.Char('thumbnail_height')

    def urlKey(self, url):
        """
        Build a tuple based on the url ('com', 'twitter')
        This is to be used as scheme key to avoid using a regex to match the service.
        """
        info = urlparse(url)
        if info.hostname:
            split = info.hostname.split('.')
            # remove the subdomain
            if len(split) == 3:
                split.pop(0)
            split.reverse()
            return tuple(split)

    @tools.ormcache()
    def processProviderJson(self):
        """
        Read the oembed_provider.json and optimise all scheme in a tuple based
        array. This should be cached somehow.
        ('com', 'twitter') = url_oembed
        """
        path = Path("../static/src/oembed_provider.json")
        providers_path = Path(__file__).absolute().parent / path
        provider_file = open(providers_path, 'r')
        providers = json.load(provider_file)

        providerUrlTree = {}
        for provider in providers:
            for endpoints in provider.get('endpoints'):
                if endpoints.get('schemes'):
                    for scheme in endpoints.get('schemes'):
                        urlKey = self.urlKey(scheme)
                        if urlKey:
                            providerUrlTree[urlKey] = endpoints.get('url')
        return providerUrlTree

    @api.model
    def getoEmbedJson(self, url):
        oEmbedUrl = False
        oEmbedJson = False

        # is the URL inside the provider.json
        provider = self.processProviderJson()
        urlKey = self.urlKey(url)
        if provider.get(urlKey):
            oEmbedUrl = [provider.get(urlKey)]

        # Search the oembed endpoints inside the html page
        if not oEmbedUrl:
            page = requests.get(url)
            tree = html.fromstring(page.content)
            oEmbedUrl = tree.xpath('//link[@type="application/json+oembed"]/@href')

        for oEmbed in oEmbedUrl:
            # Some oEmbed url have a {format} that should be replaced by json or xml
            oEmbed = oEmbed.replace('{format}', 'json')
            info = urlparse(oEmbed)
            oEmbedRequest = requests.get(oEmbed + '?url=' + url + '&format=json&maxwidth=560&maxheight=315&')
            # SSL could be requiered (eg. youtube)
            if oEmbedRequest.status_code == 403 and info.scheme == 'http':
                oEmbedRequest = requests.get(oEmbed.replace('http://', 'https://'))
            if (oEmbedRequest.ok):
                oEmbedJson = json.loads(oEmbedRequest.text)
                return {'url': url, 'json': oEmbedJson}
        return False

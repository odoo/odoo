# -*- coding: utf-8 -*-
from odoo.addons.web.controllers import webmanifest
from odoo import http

class CustomWebManifest(webmanifest.WebManifest):
    @http.route('/web/manifest.webmanifest', type='http', auth='public', methods=['GET'], readonly=True)
    def webmanifest(self):
        """ Surcharge du manifeste PWA pour personnalisation """
        return http.request.make_json_response(self._get_webmanifest(), {
            'Content-Type': 'application/manifest+json'
        })

    def _get_webmanifest(self):
        manifest = super()._get_webmanifest()
        # Remplace le nom de l'app par le nom de l'entreprise Sunsoft
        manifest['name'] = 'Sunsoft'
        manifest['description'] = 'Sunsoft ERP - Gestion commerciale, CRM, Comptabilité et plus'
        manifest['background_color'] = '#714B67'
        manifest['theme_color'] = '#714B67'
        # Ajout des icônes générées par pwa-asset-generator
        manifest['icons'] = [
            {
                "src": "/custom_pwa_manifest/static/img/manifest-icon-192.maskable.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any"
            },
            {
                "src": "/custom_pwa_manifest/static/img/manifest-icon-192.maskable.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "maskable"
            },
            {
                "src": "/custom_pwa_manifest/static/img/manifest-icon-512.maskable.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any"
            },
            {
                "src": "/custom_pwa_manifest/static/img/manifest-icon-512.maskable.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "maskable"
            }
        ]
        
        manifest['screenshots'] = [
            {
                "src": "/custom_pwa_manifest/static/img/acceuil_sunsoft.png",
                "sizes": "1839x991",
                "type": "image/png",
                "form_factor": "wide",
                "label": "Wonder Widgets"
            },
            {
                "src": "/custom_pwa_manifest/static/img/acceuil.png",
                "sizes": "1839x991",
                "type": "image/png",
                "form_factor": "wide",
                "label": "Wonder Widgets"
            },
            {
                "src": "/custom_pwa_manifest/static/img/Solution.png",
                "sizes": "1839x991",
                "type": "image/png",
                "form_factor": "wide",
                "label": "Wonder Widgets"
            },
            {
                "src": "/custom_pwa_manifest/static/img/mobile1.png",
                "sizes": "860x1746",
                "type": "image/png",
                "form_factor": "narrow",
                "label": "Wonder Widgets"
            },
            {
                "src": "/custom_pwa_manifest/static/img/mobile2.png",
                "sizes": "860x1746",
                "type": "image/png",
                "form_factor": "narrow",
                "label": "Wonder Widgets"
            },
            {
                "src": "/custom_pwa_manifest/static/img/mobile3.png",
                "sizes": "860x1746",
                "type": "image/png",
                "form_factor": "narrow",
                "label": "Wonder Widgets"
            }
        ]
        return manifest

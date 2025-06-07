
import logging
import qrcode
from odoo import models
from urllib.parse import urlparse


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def _generate_single_qr_code(self, url):
        # Appel de la méthode originale pour obtenir les QR codes de base
        _logger = logging.getLogger(__name__)
        # À l'intérieur de votre méthode:
        _logger.info("_generate_single_qr_code surchargée est appelée")

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        restaurantId = self.env['ir.config_parameter'].sudo().get_param('restaurant_id')
        # Ajout du paramètre restoId à l'URL
        modified_url = "https://menupro.tn/" + self.get_mobile_qr_url(url) +'&restoId='+restaurantId
        qr.add_data(modified_url)
        qr.make(fit=True)
        return qr.make_image(fill_color="black", back_color="white")

    def get_mobile_qr_url(self, url):
        # Analyse l'URL
        parsed_url = urlparse(url)
        #print(parsed_url)
        # Extrait le chemin et la chaîne de requête
        path_and_query = parsed_url.path + "?" + parsed_url.query

        # Trouve la position de "pos-self" dans le chemin
        start_index = path_and_query.find("pos-self")

        # Extrait la partie de l'URL commençant par "pos-self"
        if start_index != -1:
            result = path_and_query[start_index:]
        else:
            result = None
        return result
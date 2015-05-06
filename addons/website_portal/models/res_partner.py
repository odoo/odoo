from openerp import models, fields
from openerp.tools.safe_eval import safe_eval

from lxml import etree, objectify
from urllib import urlencode
import urllib2
import urlparse
from collections import OrderedDict
from unicodedata import normalize


class res_partner(models.Model):
    _name = "res.partner"
    _inherit = "res.partner"

    default_shipping_id = fields.Many2one('res.partner', 'Default Shipping Address', help="Used by the e-commerce to set a shipping address other than the partner's address")

    def validate_address(self, address):
        """ Validate an address using USPS Address Verification API
            :address : dictionnary containing the address to verify with the following keys:
                :street
                :city
                :state (2-letters state code)
                :zip
        """
        params = self.env['ir.config_parameter']
        usps_url = "http://production.shippingapis.com/ShippingAPI.dll"
        usps_username = params.get_param('website_portal.usps_username', default='')
        usps_password = params.get_param('website_portal.usps_password', default='')

        xml = '<AddressValidateRequest USERID="%s">' % usps_username
        xml += '<Address ID="0">'
        xml += '<FirmName></FirmName>'
        xml += '<Address1></Address1>'
        if isinstance(address.get('street'), unicode):
            address['street'] = normalize('NFKD', address.get('street')).encode('ascii', 'ignore')
        xml += '<Address2>%s</Address2>' % (address.get('street') or '')
        if isinstance(address.get('city'), unicode):
            address['city'] = normalize('NFKD', address.get('city')).encode('ascii', 'ignore')
        xml += '<City>%s</City>' % (address.get('city') or '')
        xml += '<State>%s</State>' % (address.get('state') or '')
        xml += '<Zip5>%s</Zip5>' % (address.get('zip') or '')
        xml += '<Zip4></Zip4>'
        xml += '</Address></AddressValidateRequest>'

        url_params = OrderedDict([('API', 'verify'), ('XML', xml)])
        url = '{api_url}?{params}'.format(api_url=usps_url, params=urlencode(url_params))

        request = urllib2.Request(url)
        response = urllib2.urlopen(request)
        response = etree.parse(response)
        address = response.getroot()[0]

        if response.getroot().tag == 'Error':
            return {'Error': 'Something went wrong.'}
        elif address[0].tag == 'Error':
            return {'Error': address[0][2].text}

        else:
            return {
                'street': address[0].text.title(),
                'city': address[1].text.title(),
                'zip': address[3].text.title(),
                'state': address[2].text,
            }

    def validate_partner_address(self):
        params = self.env['ir.config_parameter']
        validate = safe_eval(params.get_param('website_portal.address_validation', default='False'))
        res = {}
        
        if validate:
            for partner in self:
                if partner.country_id.name == 'United States':
                    vals = {
                        'street': partner.street2 or partner.street,
                        'city': partner.city,
                        'zip': partner.zip,
                        'state': partner.state_id.code,
                    }
                    res.update({partner.id: partner.validate_address(vals)})

        return res


from odoo import http
from odoo.http import request
from datetime import date
import base64

class NationalIDApplicationController(http.Controller):

    @http.route('/national/application', type='http', auth='public', website=True)
    def national_application_form(self, **kw):
        countries = request.env['res.country'].sudo().search([])
        
        return request.render('national_application.website_national_id_application_form',{
            'countries': countries,
        })
    @http.route('/submit_application', type='http', auth='public', website=True)
    def submit_application(self, **post):
        if request.httprequest.method == 'POST':
            picture = request.httprequest.files.get('picture')
            lc_reference_letter = request.httprequest.files.get('lc_reference_letter')
            applicant_name = post.get('applicant_name')
            date_of_birth = post.get('date_of_birth')
            village = post.get('village')
            applicant_phone = post.get('applicant_phone')
            email = post.get('email')
            country_id = post.get('country_id')
            address = post.get('address')
            # Retrieve other form fields similarly

            # Create a new record in the NationalIDApplication model
            NationalIDApplication = request.env['national.application']
            new_application = NationalIDApplication.sudo().create({
                'applicant_name': applicant_name,
                'date_of_birth': date_of_birth,
                'picture':base64.b64encode(picture.read()) if picture else False,
                'lc_reference_letter':base64.b64encode(lc_reference_letter.read()) if lc_reference_letter else False,
                'applicant_phone':applicant_phone,
                'village':village,
                'country_id': country_id,
                'email': email,
                'address': address,
                'state': 'draft',  #
            })

            
            return request.redirect('/client-thank-you')  # Redirect to a thank you page



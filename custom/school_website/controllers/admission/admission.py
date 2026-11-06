from odoo import http, fields, _
from odoo.http import request


class UniversityAdmissionController(http.Controller):

    @http.route(['/admission/apply'], type='http', auth='public', website=True, methods=['GET', 'POST'], csrf=True)
    def admission_apply(self, **post):
        Program = request.env['university.program'].sudo()
        programs = Program.search([('active', '=', True)], order='degree_type, name')
        error_msg = None

        if request.httprequest.method == 'POST':
            applicant_name = (post.get('applicant_name') or '').strip()
            email = (post.get('email') or '').strip()
            phone = (post.get('phone') or '').strip()
            program_id = post.get('program_id')
            dob = post.get('date_of_birth')
            gender = post.get('gender')
            address = (post.get('address') or '').strip()

            if not applicant_name or not email or not program_id:
                error_msg = _('Please complete all required fields.')
            else:
                try:
                    vals = {
                        'applicant_name': applicant_name,
                        'email': email,
                        'phone': phone,
                        'program_id': int(program_id),
                        'address': address,
                        'gender': gender if gender in ['male', 'female', 'other'] else False,
                        'application_date': fields.Date.context_today(request.env['university.admission.application']),
                    }
                    if dob:
                        vals['date_of_birth'] = dob

                    application = request.env['university.admission.application'].sudo().create(vals)
                    return request.redirect(f'/admission/thank-you?ref={application.name}')
                except Exception as e:
                    error_msg = str(e)

        values = {
            'programs': programs,
            'error_msg': error_msg,
            'post': post,
        }
        return request.render('school_website.admission_apply_template', values)

    @http.route(['/admission/thank-you'], type='http', auth='public', website=True)
    def admission_thank_you(self, ref=None, **kw):
        return request.render('school_website.admission_thank_you_template', {
            'application_ref': ref or 'New Application',
        })

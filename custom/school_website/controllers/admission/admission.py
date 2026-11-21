from odoo import http, fields, _
from odoo.http import request


class UniversityAdmissionController(http.Controller):

    def _get_current_intake(self):
        """Return the (academic year, semester) new applications are filed under."""
        year_model = request.env['university.academic.year'].sudo()
        academic_year = year_model.search(
            [('active', '=', True), ('current', '=', True)], limit=1
        ) or year_model.search(
            [('active', '=', True)], order='date_start desc', limit=1
        )
        if not academic_year:
            return academic_year, request.env['university.semester'].sudo()

        semester_model = request.env['university.semester'].sudo()
        semester = semester_model.search(
            [
                ('academic_year_id', '=', academic_year.id),
                ('active', '=', True),
                ('is_current', '=', True),
            ],
            limit=1,
        ) or semester_model.search(
            [('academic_year_id', '=', academic_year.id), ('active', '=', True)],
            order='date_start',
            limit=1,
        )
        return academic_year, semester

    @http.route(['/admission/apply'], type='http', auth='public', website=True, methods=['GET', 'POST'], csrf=True)
    def admission_apply(self, **post):
        Program = request.env['university.program'].sudo()
        programs = Program.search([('active', '=', True)], order='degree_type, name')
        error_msg = None
        academic_year, semester = self._get_current_intake()

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
            elif not academic_year or not semester:
                error_msg = _('Admissions are temporarily closed. Please try again later.')
            else:
                try:
                    vals = {
                        'applicant_name': applicant_name,
                        'email': email,
                        'phone': phone,
                        'program_id': int(program_id),
                        'academic_year_id': academic_year.id,
                        'semester_id': semester.id,
                        'address': address,
                        'gender': gender if gender in ['male', 'female', 'other'] else False,
                        'application_date': fields.Date.context_today(request.env['university.admission.application']),
                    }
                    if dob:
                        vals['date_of_birth'] = dob

                    application = request.env['university.admission.application'].sudo().create(vals)
                    return request.redirect(f'/admission/thank-you?ref={application.name}')
                except Exception as e:
                    # A failed INSERT leaves the cursor transaction aborted; roll
                    # back so the error template can still be rendered.
                    request.env.cr.rollback()
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

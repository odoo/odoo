# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
import base64
import json


class PatientRegistrationForm(http.Controller):
    @http.route(['/patient_registration'], type='http', auth="user", website=True)
    def mbs_online_appointment(self, **kw):
        if kw.get('is_submitted'):
            request.session['dr_details'] = {}
            request.session['patient_appointment'] = {}
        values = request.session.get('dr_details')
        if values and not kw.get('is_submitted'):
            return request.render("mbs_online_appointment.online_patient_appointment_details_form", {'values': values})
        else:
            return request.render("mbs_online_appointment.online_patient_appointment_details_form", {'values': {}})

class PatientForm(http.Controller):
   @http.route(['/appointment_details'], type='http', auth="user", website=True)
   def patient_detail(self, **kw):
      if kw:
         request.session['dr_details'] = kw


      hospital_id = kw.get('hospital')
      hospital = request.env['confi.hospital'].sudo().browse(int(hospital_id))
      hospital_address = hospital.address or ''
      hospital_phone = hospital.phone or ''
      hospital_email = hospital.email or ''

      doctor_id = kw.get('dr_nm')
      doctor = request.env['doctor.config'].sudo().browse(int(doctor_id))
      doctor_name = doctor.dr_id.name or ''

      patient_values = {}
      patient_values = request.session.get('patient_appointment') if request.session.get('patient_appointment') else {}
      patient_values.update({
          'dr_details': request.session.get('dr_details'),
          'hospital_address': hospital_address,
          'hospital_phone': hospital_phone,
          'hospital_email': hospital_email,
          'doctor_name': doctor_name,
          'appointment_date': kw.get('date'),
          'appointment_time': kw.get('time')
      })
      if patient_values:
         return request.render("mbs_online_appointment.patient_appointment_form", {'patient_values':patient_values})
      else:
         return request.render("mbs_online_appointment.patient_appointment_form", {'patient_values':{}})

   @http.route('/get_states', type='http', auth='user', website=True)
   def get_states(self, **kw):
       country_id = int(kw.get('country_id'))

       # Query the states based on the selected country
       states = request.env['res.country.state'].sudo().search([('country_id', '=', country_id)])

       # Prepare the response JSON
       response = {'states': [{'id': state.id, 'name': state.name} for state in states]}

       # Return the JSON response
       return json.dumps(response)

class OnlineSubmitForm(http.Controller):
    @http.route(['/patient_appointment'], type='http', auth="user", website=True)
    def final_submission(self, **kw):
        if kw:
            request.session['patient_appointment'] = kw
        final_values = {}
        final_values.update({'dr_details': request.session.get('dr_details'),
                            'patient_appointment': request.session.get('patient_appointment')})

        if final_values:
            return request.render("mbs_online_appointment.mbs_online_appointment_submit_form", {'final_values': final_values})
        else:
            return request.render("mbs_online_appointment.mbs_online_appointment_submit_form", {'final_values': {}})


class ThanksForm(http.Controller):
    @http.route(['/mbs_online_appointment/finalsubmit'], type='http', auth="user", website=True, save_session=False)
    def thank_you(self, **kw):
        dr_data = request.session.get('dr_details')
        patient_data = request.session.get('patient_appointment')

        request.env['patient.appointment'].create({
            'hospital': dr_data.get('hospital') or False,
            'dr_nm': dr_data.get('dr_nm') or False,
            'date': dr_data.get('date') or False,
            'time': dr_data.get('time') or False,
            'name': patient_data.get('name') or False,
            'date_of_birth': patient_data.get('date_of_birth') or False,
            'blood_id': patient_data.get('blood_id') or False,
            'gender': patient_data.get('gender') or False,
            'mobile': patient_data.get('mobile') or False,
            'city': patient_data.get('city') or False,
            'dieases': patient_data.get('dieases') or False,
        })

        # Check if the patient already exists based on name and date of birth
        existing_patient = request.env['patient.information'].search([
            ('patient_id', '=', patient_data.get('patient_id')),
            ('date_of_birth', '=', patient_data.get('date_of_birth'))
        ], limit=1)

        if existing_patient:
            patient = existing_patient
        else:
            # Create a new patient record if it doesn't exist
            patient = request.env['patient.information'].create({
                'patient_name': patient_data.get('name'),
                'blood_id': patient_data.get('blood_id') or False,
                'city': patient_data.get('city') or False,
                'country_id': patient_data.get('country_id') or False,
                'state_id': patient_data.get('state_id') or False,
                'date_of_birth': patient_data.get('date_of_birth') or False,
            })

        request.env['appoinment.appoinment'].create({
            'hospital': dr_data.get('hospital') or False,
            'dr_nm': dr_data.get('dr_nm') or False,
            'date': dr_data.get('date') or False,
            'time': dr_data.get('time') or False,
            'patient_info_id': patient.id or False,
            'gender': patient_data.get('gender') or False,
            'mobile': patient_data.get('mobile') or False,
            'email': patient_data.get('email') or False,
            'blood_id': patient_data.get('blood_id') or False,
            'dieases': patient_data.get('dieases') or False,
        })

        return request.render("mbs_online_appointment.thank_you_template_id")

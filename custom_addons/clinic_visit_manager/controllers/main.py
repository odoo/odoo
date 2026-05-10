from odoo import http
from odoo.http import request


class ClinicVisitController(http.Controller):
    @http.route("/clinic/visit", auth="user", type="jsonrpc")
    def get_visits(self):
        visits = request.env["clinic.visit"].search([], limit=10)
        return [
            {
                "id": visit.id,
                "name": visit.name,
                "token_number": visit.token_number,
                "patient_name": visit.patient_name,
                "doctor_name": visit.doctor_name,
                "visit_date": visit.visit_date,
                "temperature_celsius": visit.temperature_celsius,
                "blood_pressure_systolic": visit.blood_pressure_systolic,
                "blood_pressure_diastolic": visit.blood_pressure_diastolic,
                "pulse_rate": visit.pulse_rate,
                "oxygen_saturation": visit.oxygen_saturation,
                "bmi": visit.bmi,
                "fee": visit.fee,
                "state": visit.state,
            }
            for visit in visits
        ]

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
                "patient_name": visit.patient_name,
                "doctor_name": visit.doctor_name,
                "visit_date": visit.visit_date,
                "fee": visit.fee,
                "state": visit.state,
            }
            for visit in visits
        ]

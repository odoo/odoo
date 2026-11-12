from odoo import api, models

from .website import OD19_ENQUIRY_TYPES


class CrmLead(models.Model):
    _inherit = "crm.lead"

    def website_form_input_filter(self, request, values):
        """Route website enquiries coming from the RFQ form (SP6).

        ``website_crm`` already assigns the default medium / team / user and
        decides whether the record is a lead or an opportunity.  On top of
        that we read the enquiry type chosen on ``/contactus`` and route the
        record to the matching sales team plus a CRM tag, and give it a
        meaningful subject when the visitor did not provide one.
        """
        values = super().website_form_input_filter(request, values)

        enquiry = self._od19_enquiry_type_from_request(request)
        if not enquiry:
            return values

        team = self.env["crm.team"].sudo().search(
            [("name", "=", enquiry["team"])], limit=1)
        if team:
            values["team_id"] = team.id
            values["type"] = "lead" if team.use_leads else "opportunity"

        tag = self.env["crm.tag"].sudo().search(
            [("name", "=", enquiry["tag"])], limit=1)
        if not tag:
            tag = self.env["crm.tag"].sudo().create({"name": enquiry["tag"]})
        values["tag_ids"] = [(4, tag.id)]

        if not values.get("name"):
            values["name"] = "Website RFQ — %s" % enquiry["label"]

        return values

    @api.model
    def _od19_enquiry_type_from_request(self, request):
        """Return the OD19_ENQUIRY_TYPES entry selected on the RFQ form."""
        key = request.params.get("Enquiry Type")
        if not key:
            return None
        return next((t for t in OD19_ENQUIRY_TYPES if t["key"] == key), None)

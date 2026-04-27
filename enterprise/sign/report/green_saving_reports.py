from odoo import api, models

class GreenSavingsReport(models.AbstractModel):
    _name = 'report.sign.green_savings_report'
    _description = 'Green Savings Report model'

    @api.model
    def _get_report_values(self, docids, data=None):
        sent_or_signed_sign_requests = self.env['sign.request'].sudo().with_context(active_test=False).search([('state', 'in', ['sent', 'signed'])])
        sheets_sum = sum([self._sheets_from_sign_request(sign_request) for sign_request in sent_or_signed_sign_requests])

        # reference https://c.environmentalpaper.org/
        total_kilos_paper = 0.005 * sheets_sum
        total_kilos_paper = total_kilos_paper * 0.9  # consider 10% recycled paper

        water = total_kilos_paper * 88.578
        showers = water / 65

        wood = total_kilos_paper * 3.62
        trees = (wood * 12) / 1000

        carbon = total_kilos_paper * 8.482
        gas_fuel = carbon / 8.9

        waste = total_kilos_paper * 0.585
        cans = (1000 * waste) / 15

        energy = total_kilos_paper * 7.913
        computer_hours = energy / 0.75

        return {
            'sheets_sum': sheets_sum,
            'total_kilos_paper': round(total_kilos_paper, 2),
            'water': round(water, 2),
            'showers': round(showers),
            'wood': round(wood, 2),
            'trees': round(trees),
            'carbon': round(carbon, 2),
            'gas_fuel': round(gas_fuel, 2),
            'waste': round(waste, 2),
            'cans': round(cans),
            'energy': round(energy, 2),
            'computer_hours': round(computer_hours),
            'title': 'Green Savings Report'
        }

    @api.model
    def _sheets_from_sign_request(self, sign_request):
        signers = sign_request.request_item_ids.partner_id
        if sign_request.state == 'sent':
            # if sign request is sent, followers didn't receive the request yet. So we only account for signers
            return sign_request.template_id.num_pages * len(signers)
        # else we count cc_partners and signers
        return sign_request.template_id.num_pages * (len(sign_request.cc_partner_ids) + len(signers))

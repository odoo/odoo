# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, SUPERUSER_ID, _


class Job(models.Model):
    _name = "hr.job"
    _inherit = ["hr.job"]

    def _get_indeed_data(self):
        self.ensure_one()
        return {
            'jobRefCode': self.id,
            'JobInformation': {
                'JobTitle': self.name,
                'PhysicalAddress': {
                    'StreetAddress': self.address_id.street,
                    'City': self.address_id.city,
                    'State': self.address_id.state_id.name,
                    'CountryCode': self.address_id.country_code,
                    'PostalCode': self.address_id.zip
                },
                'JobBody': self.description,
            },
            'JobPostings': {
                'JobPosting': {
                    'Location': {
                        'City': self.address_id.city,
                        'State': self.address_id.state_id.name,
                        'CountryCode': self.address_id.country_code,
                        'PostalCode': self.address_id.zip
                    },
                }
            }
        }

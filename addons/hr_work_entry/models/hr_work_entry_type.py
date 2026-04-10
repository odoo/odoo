# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError


class HrWorkEntryType(models.Model):
    _name = 'hr.work.entry.type'
    _description = 'Work Entry Type'
    _order = 'sequence'

    name = fields.Char(required=True, translate=True)
    display_code = fields.Char(string="Display Code", size=3, translate=True, help="This code can be changed, it is only for a display purpose (3 letters max)")
    code = fields.Char(
        string="Payroll Code",
        required=True,
        help="The code is used as a reference in salary rules. Careful, changing an existing code can lead to unwanted behaviors.")
    external_code = fields.Char(help="Use this code to export your data to a third party")
    color = fields.Integer(default=0)
    sequence = fields.Integer(default=25)
    active = fields.Boolean(
        'Active', default=True,
        help="If the active field is set to false, it will allow you to hide the time type without removing it.")
    country_id = fields.Many2one(
        'res.country',
        string="Country",
        domain=lambda self: [('id', 'in', self.env.companies.country_id.ids)]
    )
    country_code = fields.Char(related='country_id.code')
    count_as = fields.Selection(
        [("working_time", "Working Time"), ("absence", "Absence")],
        default="working_time",
        required=True,
        help="Determines if the entry counts as working time or absence.",
    )
    amount_rate = fields.Float(
        string="Rate",
        default=1.0,
        help="If you want the hours to be paid double, the rate should be set to 200%.")
    is_extra_hours = fields.Boolean(
        string="Added to Monthly Pay",
        help="Check this setting if you want the hours to be considered as extra time and added as a bonus to the basic salary.")
    description = fields.Text(translate=True)

    @api.constrains('code', 'country_id')
    def _check_code_unicity(self):
        """
        There should be maximum one work entry type per code, per country.
        """
        # check if self does not already contain duplicates
        grouped_duplicates = self.grouped(lambda wt: (wt.code, wt.country_id))
        for code, country_id in grouped_duplicates:
            if len(grouped_duplicates[code, country_id]) > 1:
                raise UserError(self.env._(
                    'You cannot create more than one time type of code "%(code)s" for the same country (%(country)s)',
                    code=code, country=(country_id.name if country_id else self.env._("All")),
                ))

        related_we_types = self.search([
            ('code', 'in', self.mapped('code')),
            ('country_id', 'in', self.country_id.ids + [False]),
            ('id', 'not in', self.ids),
        ]).grouped(lambda wt: (wt.code, wt.country_id))

        for we_type in self:
            if not related_we_types.get((we_type.code, we_type.country_id)):
                continue  # no duplicate work entry type
            # we're not supposed to have more than one duplicate
            duplicate = related_we_types[we_type.code, we_type.country_id][:1]
            if we_type.country_id:
                raise UserError(self.env._(
                    """
Cannot insert "%(insert_name)s":
Time type "%(name)s" of code "%(code)s" already exists for country "%(country)s".
                    """,
                    insert_name=we_type.name,
                    name=duplicate.name,
                    code=duplicate.code,
                    country=duplicate.country_id.name,
                ))
            raise UserError(self.env._(
                    """
Cannot insert "%(insert_name)s":
Time type "%(name)s" of code "%(code)s", with no country assigned, already exists.
                    """,
                insert_name=we_type.name,
                name=duplicate.name,
                code=duplicate.code,
            ))

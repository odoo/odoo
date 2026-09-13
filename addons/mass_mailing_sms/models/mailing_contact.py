from odoo import fields, models


class MailingContact(models.Model):
    _name = "mailing.contact"
    _inherit = ["mailing.contact", "mixin.mail.thread.phone"]

    phone_ids = fields.Many2many(
        comodel_name="phone.number",
        relation="mailing_contact_phone_number_rel",
        column1="contact_id",
        column2="phone_number_id",
        string="Phone Numbers",
    )

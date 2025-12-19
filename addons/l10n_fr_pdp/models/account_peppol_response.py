from types import MappingProxyType

from odoo import fields, models

from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__)

NEW_STATUSES = MappingProxyType({
    'submitted': _lt('Submitted'),  # required by PPF
    'made_available': _lt('Made Available'),  # required by Peppol
    'refused': _lt('Refused'),  # required by Peppol and PPF; used for PPF messages
    'cancelled': _lt('Cancelled'),
})

PDP_STATUSES = MappingProxyType({
    'AB': _lt('Received'),  # required by Peppol and PPF; used for PPF messages
    'AP': _lt('Approved'),  # used for PPF messages
    'PD': _lt('(Partially) Paid'),  # required by PPF
    'RE': _lt('Rejected'),  # required by Peppol and PPF; used for PPF messages
    **NEW_STATUSES,
})

PEPPOL_TO_PDP_STATUS = MappingProxyType({
    'AB': 'received',
    'AP': 'approved',
    'PD': 'paid',
    'RE': 'rejected',
})


class AccountPeppolResponse(models.Model):
    _inherit = 'account.peppol.response'

    response_code = fields.Selection(
        selection_add=[(status, lt._source) for status, lt in NEW_STATUSES.items()],
        ondelete={value: 'cascade' for value in NEW_STATUSES},
    )
    pdp_ref_response_code = fields.Selection(
        string="Original Response Code",
        selection=[(status, lt._source) for status, lt in PDP_STATUSES.items()],
    )
    pdp_flow_number = fields.Selection(
        string="Flow Number",
        selection=[
            ('1', 'Tax Extract'),
            ('2', 'Status'),
            ('6', 'Mandatory Status'),
            ('10', 'Report'),
        ],
    )
    pdp_fully_paid = fields.Boolean(string="Fully Paid")
    pdp_issue_date = fields.Datetime(string="Issue Date")
    pdp_status_info = fields.Text(string="Status Info")

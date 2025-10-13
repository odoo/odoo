"""Overrides to Odoo's sequence.mixin for Croatian fiscal invoice format.

This logic shapes the generated `name` for Croatian sales invoices and credit
notes into the legally required pattern that embeds two journal-level fields:

  {JOURNAL_CODE}-{YEAR}-{SEQ}/{OZNAKA_POSLOVNOG_PROSTORA}/{OZNAKA_NAPLATNOG_UREĐAJA}

- For credit notes using a separate refund sequence, alternate identifiers
  (odobrenje) can be configured on the journal.
- Sequences reset yearly and use a fixed zero-padded counter.

Legal reference: https://porezna-uprava.gov.hr/Regulations#169%7C228, https://porezna-uprava.gov.hr/Propisi#3149|3150
"""

import pytz

from odoo import models, api
from odoo.exceptions import ValidationError
import re
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)
HR_FORMAT_STR = '{code}-{year:0{year_length}d}-{seq:0{seq_length}d}/{premises_label}/{device_label}'
HR_REGEX_STR = r'^(?P<code>.*?)-(?P<year>\d{4})-(?P<seq>\d+)/(?P<premises_label>[^/]+)/(?P<device_label>[^/]+)$'


class SequenceMixin(models.AbstractModel):
    _inherit = 'sequence.mixin'

    @api.model
    def _get_sequence_format_param(self, previous):
        """
        Build the format string and values for Croatian invoice numbering.
        Extends the base implementation to inject journal fields into the
        name. Handles both the first number of a period and subsequent ones.
        """
        if self.env.company.country_code != 'HR' or not self.is_sale_document():
            return super()._get_sequence_format_param(previous)

        if not self.journal_id:
            _logger.error("Journal is not set for this invoice.")
            raise ValidationError(self.env._("Journal is not set for this invoice."))
        if self.move_type == 'out_refund' and self.journal_id.refund_sequence:
            premises_label = self.journal_id.l10n_hr_business_premises_label_refund
            device_label = self.journal_id.l10n_hr_issuing_device_label_refund
        else:
            premises_label = self.journal_id.l10n_hr_business_premises_label
            device_label = self.journal_id.l10n_hr_issuing_device_label
        if not premises_label:
            _logger.error("Business premises label is not set on the journal.")
            raise ValidationError("Business premises label is not set on the journal.")
        if not device_label:
            _logger.error("Issuing device label is not set on the journal.")
            raise ValidationError(self.env._("Issuing device label is not set on the journal."))

        current_year = datetime.now(pytz.timezone('Europe/Zagreb')).year
        format_values = {
            'code': self.journal_id.code,
            'year': current_year,
            'seq': 1,
            'premises_label': premises_label,
            'device_label': device_label,
            'seq_length': 4,    # Adjust as needed, e.g., 4 for zero-padding
            'year_length': 4,
            'year_end_length': 0,   # Not used in this format
            'month': 0,     # Setting to 0 indicates that month is not used
        }

        # Existing logic for handling previous sequences
        match = re.match(HR_REGEX_STR, previous)
        if not match:
            if previous != self._get_starting_sequence():   # First invoice in the sequence = no need to raise warnings
                _logger.warning("The previous sequence '%s' does not match the expected format. Resetting to initial sequence.", previous)
            _logger.debug("Reset sequence format: %s, Format values: %s", HR_FORMAT_STR, format_values)
            return HR_FORMAT_STR, format_values

        format_values = match.groupdict()
        # Convert 'seq' and 'year' to integers
        try:
            format_values['seq'] = int(format_values.get('seq', '0'))
        except ValueError:
            _logger.error("Invalid sequence number in '%s': seq='%s'", previous, format_values.get('seq'))
            raise ValidationError("Invalid sequence number format.")
        try:
            format_values['year'] = int(format_values.get('year', '0'))
        except ValueError:
            _logger.error("Invalid year in '%s': year='%s'", previous, format_values.get('year'))
            raise ValidationError("Invalid year format.")

        format_values['code'] = self.journal_id.code
        format_values['premises_label'] = premises_label
        format_values['device_label'] = device_label
        # Handle 'year_end' if it exists, else set to 0
        format_values['year_end'] = int(format_values.get('year_end', '0')) if 'year_end' in format_values else 0
        # Set lengths for dynamic formatting
        format_values['seq_length'] = 4  # Fixed to 4
        format_values['year_length'] = len(str(format_values['year']))
        format_values['year_end_length'] = len(str(format_values['year_end']))  # Ensure 'year_end_length' is always set
        # Add 'month' key with a default value
        format_values['month'] = 0  # Setting to 0 indicates that month is not used

        _logger.debug("Sequence format: %s, Format values: %s", HR_FORMAT_STR, format_values)
        return HR_FORMAT_STR, format_values

    @api.model
    def _deduce_sequence_number_reset(self, name):
        """
        Detect if the used sequence resets yearly, monthly or never.
        :param name: the sequence that is used as a reference to detect the resetting periodicity.
        """
        if self.env.company.country_code != 'HR' or not self.is_sale_document():
            return super()._deduce_sequence_number_reset(name)

        match = re.match(HR_REGEX_STR, name or '')
        if match:
            return 'year'
        return super()._deduce_sequence_number_reset(name)

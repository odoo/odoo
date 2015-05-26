# -*- coding: utf-8 -*-
from blinker import Namespace

# Define a new namespace for prevent collide with other modules
_invoice_signals = Namespace()

# Default Invoice signals from OpenERP workflow
invoice_set_paid = _invoice_signals.signal('set_paid')
invoice_open_test = _invoice_signals.signal('open_test')
invoice_cancel = _invoice_signals.signal('invoice_cancel')
invoice_open = _invoice_signals.signal('invoice_open')
invoice_proforma = _invoice_signals.signal('invoice_proforma')
invoice_validate = _invoice_signals.signal('invoice_validate')

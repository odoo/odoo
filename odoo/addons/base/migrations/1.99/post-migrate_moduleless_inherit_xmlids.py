"""The inheritance rows of a custom model carry no module, and until 1.99
their reflection wrote an xmlid under the module name ``False`` anyway.

`_process_end` only sweeps real module names, so those rows were never
cleaned, and deleting the custom model left them orphaned. Reflection no
longer writes them; this drops the ones already there.
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        "DELETE FROM ir_model_data WHERE module = 'False' AND model = 'ir.model.inherit'"
    )
    _logger.info("Dropped %s module-less ir.model.inherit xmlid(s)", cr.rowcount)

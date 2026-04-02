# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import subprocess
from typing import Optional

from odoo.tools.misc import find_in_path

_logger = logging.getLogger(__name__)

FALLBACK_BINARY = '/opt/paper-muncher/bin/paper-muncher'


def get_paper_muncher_binary() -> Optional[str]:
    """Find and validate the Paper Muncher binary."""
    try:
        binary = find_in_path('paper-muncher')
    except OSError:
        _logger.debug("Cannot locate in path paper-muncher", exc_info=True)
        binary = FALLBACK_BINARY

    try:
        subprocess.run(
            [binary, '--version'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    except subprocess.CalledProcessError:
        _logger.debug("Cannot use paper-muncher", exc_info=True)
        return None

    return binary

try:
    binary = get_paper_muncher_binary()
except OSError:
    binary = ''

if binary:
    _logger.info('Will use the \'paper-muncher\' binary at %s', binary)
    status = 'ok'
else:
    _logger.info('You need \'paper-muncher\' to print a pdf version of the reports.')
    status = 'install'

# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import subprocess

from odoo.tools.misc import find_in_path


_logger = logging.getLogger(__name__)


def _get_paper_muncher_bin():
    return find_in_path('paper-muncher')


try:
    binary = _get_paper_muncher_bin()
except OSError:
    binary = ''

if binary:
    try:
        subprocess.Popen([binary, '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError:
        _logger.info('You need \'paper-muncher\' to print a pdf version of the reports.')
        status = 'broken'
    else:
        _logger.info('Will use the \'paper-muncher\' binary at %s', binary)
        status = 'ok'
else:
    status = 'install'

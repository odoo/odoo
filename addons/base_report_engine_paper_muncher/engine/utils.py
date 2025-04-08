# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import subprocess

from odoo.tools.misc import find_in_path


_logger = logging.getLogger(__name__)

def _get_paper_muncher_bin():
    return find_in_path('paper-muncher')


binary = _get_paper_muncher_bin()
try:
    subprocess.Popen([binary, '--usage'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
except (OSError, IOError):
    _logger.info('You need \'paper-muncher\' to print a pdf version of the reports.')
    status = 'broken'
else:
    _logger.info(f'Will use the \'paper-muncher\' binary at {binary}')
    status = 'ok'

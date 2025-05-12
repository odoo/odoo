# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re
import subprocess

from odoo.tools import config, parse_version
from odoo.tools.misc import find_in_path

_logger = logging.getLogger(__name__)


def _get_wkhtmltopdf_bin():
    return find_in_path('wkhtmltopdf')


def _get_wkhtmltoimage_bin():
    return find_in_path('wkhtmltoimage')


wkhtmltopdf_dpi_zoom_ratio = False
wkhtmltopdf_status = 'install'

try:
    wkhtmltopdf_binary = _get_wkhtmltopdf_bin()
except OSError:
    wkhtmltopdf_binary = ''

if wkhtmltopdf_binary:
    try:
        process = subprocess.Popen(
            [wkhtmltopdf_binary, '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
    except OSError:
        _logger.info('You need Wkhtmltopdf to print a pdf version of the reports.')
        wkhtmltopdf_status = 'broken'
    else:
        _logger.info('Will use the Wkhtmltopdf binary at %s', wkhtmltopdf_binary)
        out, err = process.communicate()
        match = re.search(rb'([0-9.]+)', out)
        if match:
            version = match.group(0).decode('ascii')
            if parse_version(version) < parse_version('0.12.0'):
                _logger.info('Upgrade Wkhtmltopdf to (at least) 0.12.0')
                wkhtmltopdf_status = 'upgrade'
            else:
                wkhtmltopdf_status = 'ok'
            if parse_version(version) >= parse_version('0.12.2'):
                wkhtmltopdf_dpi_zoom_ratio = True

            if config['workers'] == 1:
                _logger.info('You need to start Odoo with at least two workers to print a pdf version of the reports.')
                wkhtmltopdf_status = 'workers'
        else:
            _logger.info('Wkhtmltopdf seems to be broken.')
            wkhtmltopdf_status = 'broken'

wkhtmltoimage_version = None
wkhtmltoimage_status = 'install'

try:
    wkhtmltoimage_binary = _get_wkhtmltoimage_bin()
except OSError:
    wkhtmltoimage_binary = ''

if wkhtmltoimage_binary:
    try:
        process = subprocess.Popen(
            [wkhtmltoimage_binary, '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
    except OSError:
        _logger.info('You need Wkhtmltoimage to generate images from html.')
        wkhtmltoimage_status = 'broken'
    else:
        _logger.info('Will use the Wkhtmltoimage binary at %s', wkhtmltoimage_binary)
        out, err = process.communicate()
        match = re.search(rb'([0-9.]+)', out)
        if match:
            wkhtmltoimage_version = parse_version(match.group(0).decode('ascii'))
            wkhtmltoimage_status = 'ok'
            if config['workers'] == 1:
                _logger.info('You need to start Odoo with at least two workers to convert images to html.')
                wkhtmltoimage_status = 'workers'
        else:
            _logger.info('Wkhtmltoimage seems to be broken.')
            wkhtmltoimage_status = 'broken'

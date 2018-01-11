# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 P. Christeas, Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2010-2013 OpenERP SA. (http://www.openerp.com)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from reportlab import rl_config
import logging
import glob
import os

# .apidoc title: TTF Font Table

"""This module allows the mapping of some system-available TTF fonts to
the reportlab engine.

This file could be customized per distro (although most Linux/Unix ones)
should have the same filenames, only need the code below).

Due to an awful configuration that ships with reportlab at many Linux
and Ubuntu distros, we have to override the search path, too.
"""
_logger = logging.getLogger(__name__)

CustomTTFonts = []

# Search path for TTF files, in addition of rl_config.TTFSearchPath
TTFSearchPath = [
            '/usr/share/fonts/truetype', # SuSE
            '/usr/share/fonts/dejavu', '/usr/share/fonts/liberation', # Fedora, RHEL
            '/usr/share/fonts/truetype/*','/usr/local/share/fonts' # Ubuntu,
            '/usr/share/fonts/TTF/*', # Mandriva/Mageia
            '/usr/share/fonts/TTF', # Arch Linux
            '/usr/lib/openoffice/share/fonts/truetype/',
            '~/.fonts',
            '~/.local/share/fonts',

            # mac os X - from
            # http://developer.apple.com/technotes/tn/tn2024.html
            '~/Library/Fonts',
            '/Library/Fonts',
            '/Network/Library/Fonts',
            '/System/Library/Fonts',

            # windows
            'c:/winnt/fonts',
            'c:/windows/fonts'
]

def list_all_sysfonts():
    """
        This function returns list of font directories of system.
    """
    filepath = []

    # Perform the search for font files ourselves, as reportlab's
    # TTFOpenFile is not very good at it.
    searchpath = list(set(TTFSearchPath + rl_config.TTFSearchPath))
    for dirname in searchpath:
        for filename in glob.glob(os.path.join(os.path.expanduser(dirname), '*.[Tt][Tt][FfCc]')):
            filepath.append(filename)
    return filepath

def SetCustomFonts(rmldoc):
    """ Map some font names to the corresponding TTF fonts

        The ttf font may not even have the same name, as in
        Times -> Liberation Serif.
        This function is called once per report, so it should
        avoid system-wide processing (cache it, instead).
    """
    for family, font, filename, mode in CustomTTFonts:
        if os.path.isabs(filename) and os.path.exists(filename):
            rmldoc.setTTFontMapping(family, font, filename, mode)
    return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

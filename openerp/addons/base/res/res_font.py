# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

from reportlab.pdfbase import ttfonts
from openerp.osv import fields, osv
from openerp.report.render.rml2pdf import customfonts

import logging

"""This module allows the mapping of some system-available TTF fonts to
the reportlab engine.

This file could be customized per distro (although most Linux/Unix ones)
should have the same filenames, only need the code below).

Due to an awful configuration that ships with reportlab at many Linux
and Ubuntu distros, we have to override the search path, too.
"""
_logger = logging.getLogger(__name__)


class res_font(osv.Model):
    _name = "res.font"
    _description = 'Fonts available'
    _order = 'name,family,id'

    _columns = {
        'family': fields.char("Font family", required=True),
        'name': fields.char("Font Name", required=True),
        'path': fields.char("Path", required=True),
        'mode': fields.char("Mode", required=True),
    }

    _sql_constraints = [
        ('name_font_uniq', 'unique(family, name)', 'You can not register two fonts with the same name'),
    ]

    def _base_populate_font(self, cr, uid, context=None):
        if not self.search(cr, uid, [('path', '=', '/dev/null')], context=context):
            # populate db with basic pdf fonts
            for family, name, path, mode in customfonts.BasePDFFonts:
                self.create(cr, uid, {
                    'family': family, 'name': name,
                    'path': path, 'mode': mode,
                }, context=context)
        return True

    def font_scan(self, cr, uid, context=None):
        self._discover_fonts(cr, uid, context=context)
        return self._register_fonts(cr, uid, context=context)

    def _discover_fonts(self, cr, uid, context=None):
        """Scan fonts on the file system, add them to the list of known fonts
        and create font object for the new ones"""
        customfonts.CustomTTFonts = []

        found_fonts = {}
        for font_path in customfonts.list_all_sysfonts():
            try:
                font = ttfonts.TTFontFile(font_path)
                _logger.debug("Found font %s at %s", font.name, font_path)
                if not found_fonts.get(font.familyName):
                    found_fonts[font.familyName] = {'name': font.familyName}

                mode = font.styleName.lower().replace(" ", "")

                customfonts.CustomTTFonts.append((font.familyName, font.name, font_path, mode))
            except ttfonts.TTFError:
                _logger.warning("Could not register Font %s", font_path)

    def _register_fonts(self, cr, uid, context=None):
        # add new custom fonts
        for family, name, path, mode in customfonts.CustomTTFonts:
            if not self.search(cr, uid, [('family', '=', family), ('name', '=', name)], context=context):
                self.create(cr, uid, {
                    'family': family, 'name': name,
                    'path': path, 'mode': mode,
                }, context=context)

        # remove fonts not present on disk
        existing_font_names = [name for (family, name, path, mode) in customfonts.CustomTTFonts]
        inexistant_fonts = self.search(cr, uid, [('name', 'not in', existing_font_names)], context=context)
        if inexistant_fonts:
            return self.unlink(cr, uid, inexistant_fonts, context=context)
        return True

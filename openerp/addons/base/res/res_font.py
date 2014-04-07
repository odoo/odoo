# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013 OpenERP SA (<http://openerp.com>).
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
from openerp.modules.registry import RegistryManager
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

# Alternatives for the [broken] builtin PDF fonts. Default order chosen to match
# the pre-v8 mapping from openerp.report.render.rml2pdf.customfonts.CustomTTFonts.
# Format: [ (BuiltinFontFamily, mode, [AlternativeFontName, ...]), ...]
BUILTIN_ALTERNATIVES = [
    ('Helvetica', "normal", ["DejaVuSans", "LiberationSans"]),
    ('Helvetica', "bold", ["DejaVuSans-Bold", "LiberationSans-Bold"]),
    ('Helvetica', 'italic', ["DejaVuSans-Oblique", "LiberationSans-Italic"]),
    ('Helvetica', 'bolditalic', ["DejaVuSans-BoldOblique", "LiberationSans-BoldItalic"]),
    ('Times', 'normal', ["LiberationSerif", "DejaVuSerif"]),
    ('Times', 'bold', ["LiberationSerif-Bold", "DejaVuSerif-Bold"]),
    ('Times', 'italic', ["LiberationSerif-Italic", "DejaVuSerif-Italic"]),
    ('Times', 'bolditalic', ["LiberationSerif-BoldItalic", "DejaVuSerif-BoldItalic"]),
    ('Courier', 'normal', ["FreeMono", "DejaVuSansMono"]),
    ('Courier', 'bold', ["FreeMonoBold", "DejaVuSansMono-Bold"]),
    ('Courier', 'italic', ["FreeMonoOblique", "DejaVuSansMono-Oblique"]),
    ('Courier', 'bolditalic', ["FreeMonoBoldOblique", "DejaVuSansMono-BoldOblique"]),
]

class res_font(osv.Model):
    _name = "res.font"
    _description = 'Fonts available'
    _order = 'family,name,id'
    _rec_name = 'family'

    _columns = {
        'family': fields.char("Font family", required=True),
        'name': fields.char("Font Name", required=True),
        'path': fields.char("Path", required=True),
        'mode': fields.char("Mode", required=True),
    }

    _sql_constraints = [
        ('name_font_uniq', 'unique(family, name)', 'You can not register two fonts with the same name'),
    ]

    def font_scan(self, cr, uid, lazy=False, context=None):
        """Action of loading fonts
        In lazy mode will scan the filesystem only if there is no founts in the database and sync if no font in CustomTTFonts
        In not lazy mode will force scan filesystem and sync
        """
        if lazy:
            # lazy loading, scan only if no fonts in db
            found_fonts_ids = self.search(cr, uid, [('path', '!=', '/dev/null')], context=context)
            if not found_fonts_ids:
                # no scan yet or no font found on the system, scan the filesystem
                self._scan_disk(cr, uid, context=context)
            elif len(customfonts.CustomTTFonts) == 0:
                # CustomTTFonts list is empty
                self._sync(cr, uid, context=context)
        else:
            self._scan_disk(cr, uid, context=context)
        return True

    def _scan_disk(self, cr, uid, context=None):
        """Scan the file system and register the result in database"""
        found_fonts = []
        for font_path in customfonts.list_all_sysfonts():
            try:
                font = ttfonts.TTFontFile(font_path)
                _logger.debug("Found font %s at %s", font.name, font_path)
                found_fonts.append((font.familyName, font.name, font_path, font.styleName))
            except KeyError, ex:
                if ex.args and ex.args[0] == 'head':
                    # Sometimes, the system can have a lot of Bitmap fonts, and
                    # in this case, Reportlab can't load the 'head' table from
                    # the structure of the TTF file (ex: NISC18030.ttf)
                    # In this case, we have to bypass the loading of this font!
                    _logger.warning("Could not register Fond %s (Old Bitmap font)", font_path)
                else:
                    raise
            except ttfonts.TTFError:
                _logger.warning("Could not register Font %s", font_path)

        for family, name, path, mode in found_fonts:
            if not self.search(cr, uid, [('family', '=', family), ('name', '=', name)], context=context):
                self.create(cr, uid, {
                    'family': family, 'name': name,
                    'path': path, 'mode': mode,
                }, context=context)

        # remove fonts not present on the disk anymore
        existing_font_names = [name for (family, name, path, mode) in found_fonts]
        inexistant_fonts = self.search(cr, uid, [('name', 'not in', existing_font_names), ('path', '!=', '/dev/null')], context=context)
        if inexistant_fonts:
            self.unlink(cr, uid, inexistant_fonts, context=context)

        RegistryManager.signal_caches_change(cr.dbname)
        self._sync(cr, uid, context=context)
        return True

    def _sync(self, cr, uid, context=None):
        """Set the customfonts.CustomTTFonts list to the content of the database"""
        customfonts.CustomTTFonts = []
        local_family_modes = set()
        local_font_paths = {}
        found_fonts_ids = self.search(cr, uid, [('path', '!=', '/dev/null')], context=context)
        for font in self.browse(cr, uid, found_fonts_ids, context=None):
            local_family_modes.add((font.family, font.mode))
            local_font_paths[font.name] = font.path
            customfonts.CustomTTFonts.append((font.family, font.name, font.path, font.mode))

        # Attempt to remap the builtin fonts (Helvetica, Times, Courier) to better alternatives
        # if available, because they only support a very small subset of unicode
        # (missing 'č' for example)
        for builtin_font_family, mode, alts in BUILTIN_ALTERNATIVES:
            if (builtin_font_family, mode) not in local_family_modes:
                # No local font exists with that name, try alternatives
                for altern_font in alts:
                    if local_font_paths.get(altern_font):
                        altern_def = (builtin_font_family, altern_font,
                                      local_font_paths[altern_font], mode)
                        customfonts.CustomTTFonts.append(altern_def)
                        _logger.debug("Builtin remapping %r", altern_def)
                        break
                else:
                    _logger.warning("No local alternative found for builtin font `%s` (%s mode)." 
                                    "Consider installing the DejaVu fonts if you have problems "
                                    "with unicode characters in RML reports",
                                    builtin_font_family, mode)
        return True

    def clear_caches(self):
        """Force worker to resync at next report loading by setting an empty font list"""
        customfonts.CustomTTFonts = []
        return super(res_font, self).clear_caches()

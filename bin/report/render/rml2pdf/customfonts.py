# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 P. Christeas, Tiny SPRL (<http://tiny.be>).
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
import os

"""This module allows the mapping of some system-available TTF fonts to
the reportlab engine.

This file could be customized per distro (although most Linux/Unix ones)
should have the same filenames, only need the code below).
"""

CustomTTFonts = [ ('Helvetica',"DejaVu Sans", "DejaVuSans.ttf", 'normal'),
        ('Helvetica',"DejaVu Sans Bold", "DejaVuSans-Bold.ttf", 'bold'),
        ('Helvetica',"DejaVu Sans Oblique", "DejaVuSans-Oblique.ttf", 'italic'),
        ('Helvetica',"DejaVu Sans BoldOblique", "DejaVuSans-BoldOblique.ttf", 'bolditalic'),
        ('Times',"Liberation Serif", "LiberationSerif-Regular.ttf", 'normal'),
        ('Times',"Liberation Serif Bold", "LiberationSerif-Bold.ttf", 'bold'),
        ('Times',"Liberation Serif Italic", "LiberationSerif-Italic.ttf", 'italic'),
        ('Times',"Liberation Serif BoldItalic", "LiberationSerif-BoldItalic.ttf", 'bolditalic'),
        ('Times-Roman',"Liberation Serif", "LiberationSerif-Regular.ttf", 'normal'),
        ('Times-Roman',"Liberation Serif Bold", "LiberationSerif-Bold.ttf", 'bold'),
        ('Times-Roman',"Liberation Serif Italic", "LiberationSerif-Italic.ttf", 'italic'),
        ('Times-Roman',"Liberation Serif BoldItalic", "LiberationSerif-BoldItalic.ttf", 'bolditalic'),
        ('ZapfDingbats',"DejaVu Serif", "DejaVuSerif.ttf", 'normal'),
        ('ZapfDingbats',"DejaVu Serif Bold", "DejaVuSerif-Bold.ttf", 'bold'),
        ('ZapfDingbats',"DejaVu Serif Italic", "DejaVuSerif-Italic.ttf", 'italic'),
        ('ZapfDingbats',"DejaVu Serif BoldItalic", "DejaVuSerif-BoldItalic.ttf", 'bolditalic'),
        ('Courier',"FreeMono", "FreeMono.ttf", 'normal'),
        ('Courier',"FreeMono Bold", "FreeMonoBold.ttf", 'bold'),
        ('Courier',"FreeMono Oblique", "FreeMonoOblique.ttf", 'italic'),
        ('Courier',"FreeMono BoldOblique", "FreeMonoBoldOblique.ttf", 'bolditalic'),]

__foundFonts = []

def FindCustomFonts():
    """Fill the __foundFonts list with those filenames, whose fonts
       can be found in the reportlab ttf font path.
       
       This process needs only be done once per loading of this module,
       it is cached. But, if the system admin adds some font in the
       meanwhile, the server must be restarted eventually.
    """
    dirpath =  []
    global __foundFonts
    for dirname in rl_config.TTFSearchPath:
        abp = os.path.abspath(dirname)
        if os.path.isdir(abp):
            dirpath.append(abp)
        
    for k, (name, font, fname, mode) in enumerate(CustomTTFonts):
        if fname in __foundFonts:
            continue
        for d in dirpath:
            if os.path.exists(os.path.join(d, fname)):
                print "found font %s in %s" % (fname, d)
                __foundFonts.append(fname)
                break
                
    # print "Found fonts:", __foundFonts


def SetCustomFonts(rmldoc):
    """ Map some font names to the corresponding TTF fonts
    
        The ttf font may not even have the same name, as in
        Times -> Liberation Serif.
        This function is called once per report, so it should
        avoid system-wide processing (cache it, instead).
    """
    if not len(__foundFonts):
        FindCustomFonts()
    global __foundFonts
    for name, font, fname, mode in CustomTTFonts:
        if fname in __foundFonts:
            rmldoc.setTTFontMapping(name, font, fname, mode)
    return True

#eof

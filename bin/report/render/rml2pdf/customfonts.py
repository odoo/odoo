# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 P. Christeas, Tiny SPRL (<http://tiny.be>). 
#    All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


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

def SetCustomFonts(rmldoc):
	for name, font, fname, mode in CustomTTFonts:
		rmldoc.setTTFontMapping(name, font,fname, mode)

#eof
# -*- coding: utf-8 -*-
#
# Copyright (C) 2000-2005 by Yasushi Saito (yasushi.saito@gmail.com)
# 
# Jockey is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2, or (at your option) any
# later version.
#
# Jockey is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#
import sys,string,re,math
from xml.dom.minidom import Document,Comment
import theme
import basecanvas
import version
from scaling import *

# Note we flip all y-coords and negate all angles because SVG's coord
# system is inverted wrt postscript/PDF - note it's not enough to
# scale(1,-1) since that turns text into mirror writing with wrong origin

_comment_p = 0                           # whether comment() writes output

# Convert a PyChart color object to an SVG rgb() value
def _svgcolor(color):                   # see color.py
    return 'rgb(%d,%d,%d)' % tuple(map(lambda x:int(255*x),
                                       [color.r,color.g,color.b]))

# Take an SVG 'style' attribute string like 'stroke:none;fill:black'
# and parse it into a dictionary like {'stroke' : 'none', 'fill' : 'black'}
def _parseStyleStr(s):
    styledict = {}
    if s :
        # parses L -> R so later keys overwrite earlier ones
        for keyval in s.split(';'):
            l = keyval.strip().split(':')
            if l and len(l) == 2: styledict[l[0].strip()] = l[1].strip()
    return styledict

# Make an SVG style string from the dictionary described above
def _makeStyleStr(styledict):
    s = ''
    for key in styledict.keys():
        s += "%s:%s;"%(key,styledict[key])
    return s

def _protectCurrentChildren(elt):
    # If elt is a group, check to see whether there are any non-comment
    # children, and if so, create a new group to hold attributes
    # to avoid affecting previous children.  Return either the current
    # elt or the newly generated group.
    if (elt.nodeName == 'g') :
        for kid in elt.childNodes :
            if kid.nodeType != Comment.nodeType:
                g = elt.ownerDocument.createElement('g')
                g.setAttribute('auto','')
                if _comment_p:
                    g.appendChild(g.ownerDocument.createComment
                                  ('auto-generated group'))
                elt.appendChild(g)
                elt = g
                break
    return elt
            
class T(basecanvas.T):
    def __init__(self, fname):
        basecanvas.T.__init__(self)
        self.__out_fname = fname
        self.__xmin, self.__xmax, self.__ymin, self.__ymax = 0,0,0,0
        self.__doc = Document()
        self.__doc.appendChild(self.__doc.createComment
             ('Created by PyChart ' + version.version + ' ' + version.copyright))
        self.__svg = self.__doc.createElement('svg') # the svg doc
        self.__doc.appendChild(self.__svg)
        self.__defs = self.__doc.createElement('defs') # for clip paths
        self.__svg.appendChild(self.__defs)
        self.__currElt = self.__svg
        self.gsave()       # create top-level group for dflt styles
        self._updateStyle(font_family = theme.default_font_family,
                          font_size = theme.default_font_size,
                          font_style = 'normal',
                          font_weight = 'normal',
                          font_stretch = 'normal',
                          fill = 'none',
                          stroke = 'rgb(0,0,0)', #SVG dflt none, PS dflt blk
                          stroke_width = theme.default_line_width,
                          stroke_linejoin = 'miter',
                          stroke_linecap = 'butt',
                          stroke_dasharray = 'none')
        
    def _updateStyle(self, **addstyledict): 
        elt = _protectCurrentChildren(self.__currElt)

        # fetch the current styles for this node
        mystyledict = _parseStyleStr(elt.getAttribute('style'))

        # concat all parent style strings to get dflt styles for this node
        parent,s = elt.parentNode,''
        while parent.nodeType != Document.nodeType :
            # prepend parent str so later keys will override earlier ones
            s = parent.getAttribute('style') + s
            parent = parent.parentNode
        dfltstyledict = _parseStyleStr(s)

        # Do some pre-processing on the caller-supplied add'l styles
        # Convert '_' to '-' so caller can specify style tags as python
        # variable names, eg. stroke_width => stroke-width.
        # Also convert all RHS values to strs 
        for key in addstyledict.keys():
            k = re.sub('_','-',key)
            addstyledict[k] = str(addstyledict[key]) # all vals => strs
            if (k != key) : del addstyledict[key]

        for k in addstyledict.keys() :
            if (mystyledict.has_key(k) or # need to overwrite it
                (not dfltstyledict.has_key(k)) or # need to set it
                dfltstyledict[k] != addstyledict[k]) : # need to override it
                mystyledict[k] = addstyledict[k]
        
        s = _makeStyleStr(mystyledict)
        if s : elt.setAttribute('style',s)

        self.__currElt = elt

    ####################################################################
    # methods below define the pychart backend device API

    # First are a set of methods to start, construct and finalize a path
    
    def newpath(self):                  # Start a new path
        if (self.__currElt.nodeName != 'g') :
            raise OverflowError, "No containing group for newpath"
        # Just insert a new 'path' element into the document
        p = self.__doc.createElement('path')
        self.__currElt.appendChild(p)
        self.__currElt = p

    # This set of methods add data to an existing path element,
    # simply add to the 'd' (data) attribute of the path elt
    
    def moveto(self, x, y):             # 
        if (self.__currElt.nodeName != 'path') :
            raise OverflowError, "No path for moveto"
        d = ' '.join([self.__currElt.getAttribute('d'),'M',`x`,`-y`]).strip()
        self.__currElt.setAttribute('d', d)
    def lineto(self, x, y):
        if (self.__currElt.nodeName != 'path') :
            raise OverflowError, "No path for lineto"
        d = ' '.join([self.__currElt.getAttribute('d'),'L',`x`,`-y`]).strip()
        self.__currElt.setAttribute('d', d)
    def path_arc(self, x, y, radius, ratio, start_angle, end_angle):
        # mimic PS 'arc' given radius, yr/xr (=eccentricity), start and
        # end angles.  PS arc draws from CP (if exists) to arc start,
        # then draws arc in counterclockwise dir from start to end
        # SVG provides an arc command that draws a segment of an
        # ellipse (but not a full circle) given these args:
        # A xr yr rotate majorArcFlag counterclockwiseFlag xe ye
        # We don't use rotate(=0) and flipped axes => all arcs are clockwise

        if (self.__currElt.nodeName != 'path') :
            raise OverflowError, "No path for path_arc"

        self.comment('x=%g, y=%g, r=%g, :=%g, %g-%g' 
                     % (x,y,radius,ratio,start_angle,end_angle))

        xs = x+radius*math.cos(2*math.pi/360.*start_angle)
        ys = y+ratio*radius*math.sin(2*math.pi/360.*start_angle)
        xe = x+radius*math.cos(2*math.pi/360.*end_angle)
        ye = y+ratio*radius*math.sin(2*math.pi/360.*end_angle)
        if (end_angle < start_angle) :  # make end bigger than start
            while end_angle <= start_angle: # '<=' so 360->0 becomes 360->720
                end_angle += 360
        full_circ = (end_angle - start_angle >= 360) # draw a full circle?
            
        d = self.__currElt.getAttribute('d')
        d += ' %s %g %g' % (d and 'L' or 'M',xs,-ys) # draw from CP, if exists
        if (radius > 0) : # skip, eg. 0-radius 'rounded' corners which blowup
            if (full_circ) :
                # If we're drawing a full circle, move to the end coord
                # and draw half a circle to the reflected xe,ye
                d += ' M %g %g A %g %g 0 1 0 %g %g'%(xe,-ye,
                                                     radius,radius*ratio,
                                                     2*x-xe,-(2*y-ye))
            # Draw arc from the CP (either reflected xe,ye for full circle else
            # xs,ys) to the end coord - note with full_circ the
            # 'bigArcFlag' value is moot, with exactly 180deg left to draw
            d += ' A %g %g 0 %d 0 %g %g' % (radius,radius*ratio,
                                            end_angle-start_angle>180,
                                            xe,-ye)
        self.__currElt.setAttribute('d',d.strip())
    def curveto(self, x1,y1,x2,y2,x3,y3):
        # Equivalent of PostScript's x1 y1 x2 y2 x3 y3 curveto which
        # draws a cubic bezier curve from curr pt to x3,y3 with ctrl points
        # x1,y1, and x2,y2
        # In SVG this is just d='[M x0 y0] C x1 y1 x2 y2 x3 y3'
        #! I can't find an example of this being used to test it
        if (self.__currElt.nodeNode != 'path') :
            raise OverflowError, "No path for curveto"
        d = ' '.join([self.__currElt.getAttribute('d'),'C',
                      `x1`,`-y1`,`x2`,`-y2`,`x3`,`-y3`,]).strip()
        self.__currElt.setAttribute('d', d)
    def closepath(self):                # close back to start of path
        if (self.__currElt.nodeName != 'path') :
            raise OverflowError, "No path for closepath"
        d = ' '.join([self.__currElt.getAttribute('d'),'Z']).strip()
        self.__currElt.setAttribute('d', d)

    # Next we have three methods for finalizing a path element,
    # either fill it, clip to it, or draw it (stroke)
    # canvas.polygon() can generate fill/clip cmds with
    # no corresponding path so just ignore them
    def stroke(self):
        if (self.__currElt.nodeName != 'path') :
            self.comment('No path - ignoring stroke')
            return
        self._updateStyle(fill='none')
        self.__currElt = self.__currElt.parentNode
    def fill(self):
        if (self.__currElt.nodeName != 'path') :
            self.comment('No path - ignoring fill')
            return
        self._updateStyle(stroke='none')
        self.__currElt = self.__currElt.parentNode
    def clip_sub(self):
        if (self.__currElt.nodeName != 'path') :
            self.comment('No path - ignoring clip')
            return

        # remove the current path from the tree ...
        p = self.__currElt
        self.__currElt=p.parentNode
        self.__currElt.removeChild(p)

        # ... add it to a clipPath elt in the defs section
        clip = self.__doc.createElement('clipPath')
        clipid = 'clip'+`len(self.__defs.childNodes)`
        clip.setAttribute('id',clipid)
        clip.appendChild(p)
        self.__defs.appendChild(clip)

        # ... update the local style to point to it
        self._updateStyle(clip_path = 'url(#%s)'%clipid)

    # The text_xxx routines specify the start/end and contents of text
    def text_begin(self):
        if (self.__currElt.nodeName != 'g') :
            raise ValueError, "No group for text block"
        t = self.__doc.createElement('text')
        self.__currElt.appendChild(t)
        self.__currElt = t
    def text_moveto(self, x, y, angle):
        if (self.__currElt.nodeName != 'text') :
            raise ValueError, "No text for moveto"
        self.__currElt.setAttribute('x',`x`)
        self.__currElt.setAttribute('y',`-y`)
        if (angle) :
            self.__currElt.setAttribute('transform',
                                        'rotate(%g,%g,%g)' % (-angle,x,-y))
    def text_show(self, font_name, size, color, str):
        if (self.__currElt.nodeName != 'text') :
            raise ValueError, "No text for show"

        # PyChart constructs a postscript font name, for example:
        #
        # Helvetica Helvetica-Bold Helvetica-Oblique Helvetica-BoldOblique
        # Helvetica-Narrow Times-Roman Times-Italic
        # Symbol Palatino-Roman Bookman-Demi Courier AvantGarde-Book
        #
        # We need to deconstruct this to get the font-family (the
        # piece before the '-'), and other characteristics.
        # Note that 'Courier' seems to correspond to SVGs 'CourierNew'
        # and that the SVG Symbol font is Unicode where the ascii text
        # 'Symbol' doesn't create greek characters like 'Sigma ...' -
        # should really pass a unicode string, or provide translation
        #
        # SVG defines:
        # font-style = normal (aka roman) | italic | oblique
        # font-weight = normal | bold (aka demi?)
        # font-stretch = normal | wider | narrower | ultra-condensed |
        #	extra-condensed | condensed | semi-condensed |
        #	semi-expanded | expanded | extra-expanded | ultra-expanded
        # ('narrow' seems to correspond to 'condensed')

        m = re.match(r'([^-]*)(-.*)?',font_name)
        font_name,modifiers = m.groups()
        if font_name == 'Courier' : font_name = 'CourierNew'
        font_style = font_weight = font_stretch = 'normal'
        if modifiers :
            if re.search('Italic',modifiers) : font_style = 'italic'
            elif re.search('Oblique',modifiers) : font_style = 'oblique'
            if re.search('Bold|Demi',modifiers) : font_weight = 'bold'
            if re.search('Narrow',modifiers) : font_stretch = 'condensed'
        #! translate ascii symbol font chars -> unicode (see www.unicode.org)
        #! http://www.unicode.org/Public/MAPPINGS/VENDORS/ADOBE/symbol.txt
        #! but xml Text element writes unicode chars as '?' to XML file...
        str = re.sub(r'\\([()])',r'\1',str) # unescape brackets
        self._updateStyle(fill=_svgcolor(color),
                          stroke='none',
                          font_family=font_name,
                          font_size=size,
                          font_style=font_style,
                          font_weight=font_weight,
                          font_stretch=font_stretch)
        self.__currElt.appendChild(self.__doc.createTextNode(str))
    def text_end(self):
        if (self.__currElt.nodeName != 'text') :
            raise ValueError, "No text for close"
        self.__currElt = self.__currElt.parentNode


    # Three methods that change the local style of elements
    # If applied to a group, they persist until the next grestore,
    # If applied within a path element, they only affect that path -
    # although this may not in general correspond to (say) PostScript
    # behavior, it appears to correspond to reflect mode of use of this API
    def set_fill_color(self, color):
        self._updateStyle(fill=_svgcolor(color))
    def set_stroke_color(self, color):
        self._updateStyle(stroke=_svgcolor(color))
    def set_line_style(self, style):  # see line_style.py
        linecap = {0:'butt', 1:'round', 2:'square'}
        linejoin = {0:'miter', 1:'round', 2:'bevel'}
        if style.dash: dash = ','.join(map(str,style.dash))
        else : dash = 'none'
        self._updateStyle(stroke_width = style.width,
                          stroke = _svgcolor(style.color),
                          stroke_linecap = linecap[style.cap_style],
                          stroke_linejoin = linejoin[style.join_style],
                          stroke_dasharray = dash)

    # gsave & grestore respectively push & pop a new context to hold
    # new style and transform parameters.  push/pop transformation are
    # similar but explicitly specify a coordinate transform at the
    # same time
    def gsave(self):
        if (self.__currElt.nodeName not in ['g','svg']) :
            raise ValueError, "No group for gsave"
        g = self.__doc.createElement('g')
        self.__currElt.appendChild(g)
        self.__currElt = g
    def grestore(self):
        if (self.__currElt.nodeName != 'g'):
            raise ValueError, "No group for grestore"
        # first pop off any auto-generated groups (see protectCurrentChildren)
        while (self.__currElt.hasAttribute('auto')) :
            self.__currElt.removeAttribute('auto')
            self.__currElt = self.__currElt.parentNode
        # then pop off the original caller-generated group
        self.__currElt = self.__currElt.parentNode

    def push_transformation(self, baseloc, scale, angle, in_text=0):
        #? in_text arg appears to always be ignored

        # In some cases this gets called after newpath, with
        # corresonding pop_transformation called after the path is
        # finalized so we check specifically for that, and generate
        # an enclosing group to hold the incomplete path element
        # We could add the transform directly to the path element
        # (like we do with line-style etc) but that makes it harder
        # to handle the closing 'pop' and might lead to inconsitency
        # with PostScript if the closing pop doesn't come right after
        # the path element

        elt = self.__currElt
        if elt.nodeName == 'g':
            elt = None
        elif (elt.nodeName == 'path' and not elt.hasAttribute('d')) :
            g = elt.parentNode
            g.removeChild(elt)
            self.__currElt = g
        else:
            raise ValueError, "Illegal placement of push_transformation"
            
        t = ''
        if baseloc :
            t += 'translate(%g,%g) '%(baseloc[0],-baseloc[1])
        if angle :
            t += 'rotate(%g) '%-angle
        if scale :
            t += 'scale(%g,%g) '%tuple(scale)
            
        self.gsave()
        self.__currElt.setAttribute('transform',t.strip())
        if elt:                         # elt has incomplete 'path' or None
            self.__currElt.appendChild(elt)
            self.__currElt = elt

    def pop_transformation(self, in_text=0): #? in_text unused?
        self.grestore()

    # If verbose, add comments to the output stream (helps debugging)
    def comment(self, str):
        if _comment_p : 
            self.__currElt.appendChild(self.__doc.createComment(str))

    # The verbatim method is currently not supported - presumably with
    # the SVG backend the user would require access to the DOM since
    # we're not directly outputting plain text here
    def verbatim(self, str):
        self.__currElt.appendChild(self.__doc.createComment('verbatim not implemented: ' + str))

    # The close() method finalizes the SVG document and flattens the
    # DOM document to XML text to the specified file (or stdout)
    def close(self):
        basecanvas.T.close(self)
        self.grestore()           # matching the gsave in __init__
        if (self.__currElt.nodeName != 'svg') :
            raise ValueError, "Incomplete document at close!"

        # Don't bother to output an empty document - this can happen
        # when we get close()d immediately by theme reinit
        if (len(self.__svg.childNodes[-1].childNodes) == 0) :
            return
            
        fp, need_close = self.open_output(self.__out_fname)
        bbox = theme.adjust_bounding_box([self.__xmin, self.__ymin,
                                          self.__xmax, self.__ymax])
        self.__svg.setAttribute('viewBox','%g %g %g %g'
                                % (xscale(bbox[0]),
                                   -yscale(bbox[3]),
                                   xscale(bbox[2])-xscale(bbox[0]),
                                   yscale(bbox[3])-yscale(bbox[1])))
        self.__doc.writexml(fp,'','  ','\n')
        if need_close:
            fp.close()

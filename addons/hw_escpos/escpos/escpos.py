# -*- coding: utf-8 -*-

from __future__ import print_function
import base64
import copy
import io
import math
import re
import traceback
import codecs
from hashlib import md5

from PIL import Image
from xml.etree import ElementTree as ET

from odoo.tools import pycompat

try:
    import jcconv
except ImportError:
    jcconv = None

try: 
    import qrcode
except ImportError:
    qrcode = None

from .constants import *
from .exceptions import *

def utfstr(stuff):
    """ converts stuff to string and does without failing if stuff is a utf8 string """
    if isinstance(stuff,pycompat.string_types):
        return stuff
    else:
        return str(stuff)

class StyleStack:
    """ 
    The stylestack is used by the xml receipt serializer to compute the active styles along the xml
    document. Styles are just xml attributes, there is no css mechanism. But the style applied by
    the attributes are inherited by deeper nodes.
    """
    def __init__(self):
        self.stack = []
        self.defaults = {   # default style values
            'align':     'left',
            'underline': 'off',
            'bold':      'off',
            'size':      'normal',
            'font'  :    'a',
            'width':     48,
            'indent':    0,
            'tabwidth':  2,
            'bullet':    ' - ',
            'line-ratio':0.5,
            'color':    'black',

            'value-decimals':           2,
            'value-symbol':             '',
            'value-symbol-position':    'after',
            'value-autoint':            'off',
            'value-decimals-separator':  '.',
            'value-thousands-separator': ',',
            'value-width':               0,
            
        }

        self.types = { # attribute types, default is string and can be ommitted
            'width':    'int',
            'indent':   'int',
            'tabwidth': 'int',
            'line-ratio':       'float',
            'value-decimals':   'int',
            'value-width':      'int',
        }

        self.cmds = { 
            # translation from styles to escpos commands
            # some style do not correspond to escpos command are used by
            # the serializer instead
            'align': {
                'left':     TXT_ALIGN_LT,
                'right':    TXT_ALIGN_RT,
                'center':   TXT_ALIGN_CT,
                '_order':   1,
            },
            'underline': {
                'off':      TXT_UNDERL_OFF,
                'on':       TXT_UNDERL_ON,
                'double':   TXT_UNDERL2_ON,
                # must be issued after 'size' command
                # because ESC ! resets ESC -
                '_order':   10,
            },
            'bold': {
                'off':      TXT_BOLD_OFF,
                'on':       TXT_BOLD_ON,
                # must be issued after 'size' command
                # because ESC ! resets ESC -
                '_order':   10,
            },
            'font': {
                'a':        TXT_FONT_A,
                'b':        TXT_FONT_B,
                # must be issued after 'size' command
                # because ESC ! resets ESC -
                '_order':   10,
            },
            'size': {
                'normal':           TXT_NORMAL,
                'double-height':    TXT_2HEIGHT,
                'double-width':     TXT_2WIDTH,
                'double':           TXT_DOUBLE,
                '_order':   1,
            },
            'color': {
                'black':    TXT_COLOR_BLACK,
                'red':      TXT_COLOR_RED,
                '_order':   1,
            },
        }

        self.push(self.defaults) 

    def get(self,style):
        """ what's the value of a style at the current stack level"""
        level = len(self.stack) -1
        while level >= 0:
            if style in self.stack[level]:
                return self.stack[level][style]
            else:
                level = level - 1
        return None

    def enforce_type(self, attr, val):
        """converts a value to the attribute's type"""
        if not attr in self.types:
            return utfstr(val)
        elif self.types[attr] == 'int':
            return int(float(val))
        elif self.types[attr] == 'float':
            return float(val)
        else:
            return utfstr(val)

    def push(self, style={}):
        """push a new level on the stack with a style dictionnary containing style:value pairs"""
        _style = {}
        for attr in style:
            if attr in self.cmds and not style[attr] in self.cmds[attr]:
                print('WARNING: ESC/POS PRINTING: ignoring invalid value: %s for style %s' % (style[attr], utfstr(attr)))
            else:
                _style[attr] = self.enforce_type(attr, style[attr])
        self.stack.append(_style)

    def set(self, style={}):
        """overrides style values at the current stack level"""
        _style = {}
        for attr in style:
            if attr in self.cmds and not style[attr] in self.cmds[attr]:
                print('WARNING: ESC/POS PRINTING: ignoring invalid value: %s for style %s' % (style[attr], attr))
            else:
                self.stack[-1][attr] = self.enforce_type(attr, style[attr])

    def pop(self):
        """ pop a style stack level """
        if len(self.stack) > 1 :
            self.stack = self.stack[:-1]

    def to_escpos(self):
        """ converts the current style to an escpos command string """
        cmd = ''
        ordered_cmds = sorted(self.cmds, key=lambda x: self.cmds[x]['_order'])
        for style in ordered_cmds:
            cmd += self.cmds[style][self.get(style)]
        return cmd

class XmlSerializer:
    """ 
    Converts the xml inline / block tree structure to a string,
    keeping track of newlines and spacings.
    The string is outputted asap to the provided escpos driver.
    """
    def __init__(self,escpos):
        self.escpos = escpos
        self.stack = ['block']
        self.dirty = False

    def start_inline(self,stylestack=None):
        """ starts an inline entity with an optional style definition """
        self.stack.append('inline')
        if self.dirty:
            self.escpos._raw(' ')
        if stylestack:
            self.style(stylestack)

    def start_block(self,stylestack=None):
        """ starts a block entity with an optional style definition """
        if self.dirty:
            self.escpos._raw('\n')
            self.dirty = False
        self.stack.append('block')
        if stylestack:
            self.style(stylestack)

    def end_entity(self):
        """ ends the entity definition. (but does not cancel the active style!) """
        if self.stack[-1] == 'block' and self.dirty:
            self.escpos._raw('\n')
            self.dirty = False
        if len(self.stack) > 1:
            self.stack = self.stack[:-1]

    def pre(self,text):
        """ puts a string of text in the entity keeping the whitespace intact """
        if text:
            self.escpos.text(text)
            self.dirty = True

    def text(self,text):
        """ puts text in the entity. Whitespace and newlines are stripped to single spaces. """
        if text:
            text = utfstr(text)
            text = text.strip()
            text = re.sub('\s+',' ',text)
            if text:
                self.dirty = True
                self.escpos.text(text)

    def linebreak(self):
        """ inserts a linebreak in the entity """
        self.dirty = False
        self.escpos._raw('\n')

    def style(self,stylestack):
        """ apply a style to the entity (only applies to content added after the definition) """
        self.raw(stylestack.to_escpos())

    def raw(self,raw):
        """ puts raw text or escpos command in the entity without affecting the state of the serializer """
        self.escpos._raw(raw)

class XmlLineSerializer:
    """ 
    This is used to convert a xml tree into a single line, with a left and a right part.
    The content is not output to escpos directly, and is intended to be fedback to the
    XmlSerializer as the content of a block entity.
    """
    def __init__(self, indent=0, tabwidth=2, width=48, ratio=0.5):
        self.tabwidth = tabwidth
        self.indent = indent
        self.width  = max(0, width - int(tabwidth*indent))
        self.lwidth = int(self.width*ratio)
        self.rwidth = max(0, self.width - self.lwidth)
        self.clwidth = 0
        self.crwidth = 0
        self.lbuffer  = ''
        self.rbuffer  = ''
        self.left    = True

    def _txt(self,txt):
        if self.left:
            if self.clwidth < self.lwidth:
                txt = txt[:max(0, self.lwidth - self.clwidth)]
                self.lbuffer += txt
                self.clwidth += len(txt)
        else:
            if self.crwidth < self.rwidth:
                txt = txt[:max(0, self.rwidth - self.crwidth)]
                self.rbuffer += txt
                self.crwidth  += len(txt)

    def start_inline(self,stylestack=None):
        if (self.left and self.clwidth) or (not self.left and self.crwidth):
            self._txt(' ')

    def start_block(self,stylestack=None):
        self.start_inline(stylestack)

    def end_entity(self):
        pass

    def pre(self,text):
        if text:
            self._txt(text)
    def text(self,text):
        if text:
            text = utfstr(text)
            text = text.strip()
            text = re.sub('\s+',' ',text)
            if text:
                self._txt(text)

    def linebreak(self):
        pass
    def style(self,stylestack):
        pass
    def raw(self,raw):
        pass

    def start_right(self):
        self.left = False

    def get_line(self):
        return ' ' * self.indent * self.tabwidth + self.lbuffer + ' ' * (self.width - self.clwidth - self.crwidth) + self.rbuffer
    

class Escpos:
    """ ESC/POS Printer object """
    device    = None
    encoding  = None
    img_cache = {}

    def _check_image_size(self, size):
        """ Check and fix the size of the image to 32 bits """
        if size % 32 == 0:
            return (0, 0)
        else:
            image_border = 32 - (size % 32)
            if (image_border % 2) == 0:
                return (int(image_border / 2), int(image_border / 2))
            else:
                return (int(image_border / 2), int((image_border / 2) + 1))

    def _print_image(self, line, size):
        """ Print formatted image """
        i = 0
        cont = 0
        buffer = ""

       
        self._raw(S_RASTER_N)
        buffer = b"%02X%02X%02X%02X" % (int((size[0]/size[1])/8), 0, size[1], 0)
        self._raw(codecs.decode(buffer, 'hex'))
        buffer = ""

        while i < len(line):
            hex_string = int(line[i:i+8],2)
            buffer += "%02X" % hex_string
            i += 8
            cont += 1
            if cont % 4 == 0:
                self._raw(codecs.decode(buffer, "hex"))
                buffer = ""
                cont = 0

    def _raw_print_image(self, line, size, output=None ):
        """ Print formatted image """
        i = 0
        cont = 0
        buffer = ""
        raw = b""

        def __raw(string):
            if output:
                output(string)
            else:
                self._raw(string)
       
        raw += S_RASTER_N.encode('utf-8')
        buffer = "%02X%02X%02X%02X" % (int((size[0]/size[1])/8), 0, size[1], 0)
        raw += codecs.decode(buffer, 'hex')
        buffer = ""

        while i < len(line):
            hex_string = int(line[i:i+8],2)
            buffer += "%02X" % hex_string
            i += 8
            cont += 1
            if cont % 4 == 0:
                raw += codecs.decode(buffer, 'hex')
                buffer = ""
                cont = 0

        return raw

    def _convert_image(self, im):
        """ Parse image and prepare it to a printable format """
        pixels   = []
        pix_line = ""
        im_left  = ""
        im_right = ""
        switch   = 0
        img_size = [ 0, 0 ]


        if im.size[0] > 512:
            print("WARNING: Image is wider than 512 and could be truncated at print time ")
        if im.size[1] > 255:
            raise ImageSizeError()

        im_border = self._check_image_size(im.size[0])
        for i in range(im_border[0]):
            im_left += "0"
        for i in range(im_border[1]):
            im_right += "0"

        for y in range(im.size[1]):
            img_size[1] += 1
            pix_line += im_left
            img_size[0] += im_border[0]
            for x in range(im.size[0]):
                img_size[0] += 1
                RGB = im.getpixel((x, y))
                im_color = (RGB[0] + RGB[1] + RGB[2])
                im_pattern = "1X0"
                pattern_len = len(im_pattern)
                switch = (switch - 1 ) * (-1)
                for x in range(pattern_len):
                    if im_color <= (255 * 3 / pattern_len * (x+1)):
                        if im_pattern[x] == "X":
                            pix_line += "%d" % switch
                        else:
                            pix_line += im_pattern[x]
                        break
                    elif im_color > (255 * 3 / pattern_len * pattern_len) and im_color <= (255 * 3):
                        pix_line += im_pattern[-1]
                        break 
            pix_line += im_right
            img_size[0] += im_border[1]

        return (pix_line, img_size)

    def image(self,path_img):
        """ Open image file """
        im_open = Image.open(path_img)
        im = im_open.convert("RGB")
        # Convert the RGB image in printable image
        pix_line, img_size = self._convert_image(im)
        self._print_image(pix_line, img_size)

    def print_base64_image(self,img):

        print('print_b64_img')

        id = md5(img).digest()

        if id not in self.img_cache:
            print('not in cache')

            img = img[img.find(b',')+1:]
            f = io.BytesIO(b'img')
            f.write(base64.decodebytes(img))
            f.seek(0)
            img_rgba = Image.open(f)
            img = Image.new('RGB', img_rgba.size, (255,255,255))
            channels = img_rgba.split()
            if len(channels) > 3:
                # use alpha channel as mask
                img.paste(img_rgba, mask=channels[3])
            else:
                img.paste(img_rgba)

            print('convert image')
        
            pix_line, img_size = self._convert_image(img)

            print('print image')

            buffer = self._raw_print_image(pix_line, img_size)
            self.img_cache[id] = buffer

        print('raw image')

        self._raw(self.img_cache[id])

    def qr(self,text):
        """ Print QR Code for the provided string """
        qr_code = qrcode.QRCode(version=4, box_size=4, border=1)
        qr_code.add_data(text)
        qr_code.make(fit=True)
        qr_img = qr_code.make_image()
        im = qr_img._img.convert("RGB")
        # Convert the RGB image in printable image
        self._convert_image(im)

    def barcode(self, code, bc, width=255, height=2, pos='below', font='a'):
        """ Print Barcode """
        # Align Bar Code()
        self._raw(TXT_ALIGN_CT)
        # Height
        if height >=2 or height <=6:
            self._raw(BARCODE_HEIGHT)
        else:
            raise BarcodeSizeError()
        # Width
        if width >= 1 or width <=255:
            self._raw(BARCODE_WIDTH)
        else:
            raise BarcodeSizeError()
        # Font
        if font.upper() == "B":
            self._raw(BARCODE_FONT_B)
        else: # DEFAULT FONT: A
            self._raw(BARCODE_FONT_A)
        # Position
        if pos.upper() == "OFF":
            self._raw(BARCODE_TXT_OFF)
        elif pos.upper() == "BOTH":
            self._raw(BARCODE_TXT_BTH)
        elif pos.upper() == "ABOVE":
            self._raw(BARCODE_TXT_ABV)
        else:  # DEFAULT POSITION: BELOW 
            self._raw(BARCODE_TXT_BLW)
        # Type 
        if bc.upper() == "UPC-A":
            self._raw(BARCODE_UPC_A)
        elif bc.upper() == "UPC-E":
            self._raw(BARCODE_UPC_E)
        elif bc.upper() == "EAN13":
            self._raw(BARCODE_EAN13)
        elif bc.upper() == "EAN8":
            self._raw(BARCODE_EAN8)
        elif bc.upper() == "CODE39":
            self._raw(BARCODE_CODE39)
        elif bc.upper() == "ITF":
            self._raw(BARCODE_ITF)
        elif bc.upper() == "NW7":
            self._raw(BARCODE_NW7)
        else:
            raise BarcodeTypeError()
        # Print Code
        if code:
            self._raw(code)
            # We are using type A commands
            # So we need to add the 'NULL' character
            # https://github.com/python-escpos/python-escpos/pull/98/files#diff-a0b1df12c7c67e38915adbe469051e2dR444
            self._raw('\x00')
        else:
            raise BarcodeCodeError()

    def receipt(self,xml):
        """
        Prints an xml based receipt definition
        """

        def strclean(string):
            if not string:
                string = ''
            string = string.strip()
            string = re.sub('\s+',' ',string)
            return string

        def format_value(value, decimals=3, width=0, decimals_separator='.', thousands_separator=',', autoint=False, symbol='', position='after'):
            decimals = max(0,int(decimals))
            width    = max(0,int(width))
            value    = float(value)

            if autoint and math.floor(value) == value:
                decimals = 0
            if width == 0:
                width = ''

            if thousands_separator:
                formatstr = "{:"+str(width)+",."+str(decimals)+"f}"
            else:
                formatstr = "{:"+str(width)+"."+str(decimals)+"f}"


            ret = formatstr.format(value)
            ret = ret.replace(',','COMMA')
            ret = ret.replace('.','DOT')
            ret = ret.replace('COMMA',thousands_separator)
            ret = ret.replace('DOT',decimals_separator)

            if symbol:
                if position == 'after':
                    ret = ret + symbol
                else:
                    ret = symbol + ret
            return ret

        def print_elem(stylestack, serializer, elem, indent=0):

            elem_styles = {
                'h1': {'bold': 'on', 'size':'double'},
                'h2': {'size':'double'},
                'h3': {'bold': 'on', 'size':'double-height'},
                'h4': {'size': 'double-height'},
                'h5': {'bold': 'on'},
                'em': {'font': 'b'},
                'b':  {'bold': 'on'},
            }

            stylestack.push()
            if elem.tag in elem_styles:
                stylestack.set(elem_styles[elem.tag])
            stylestack.set(elem.attrib)

            if elem.tag in ('p','div','section','article','receipt','header','footer','li','h1','h2','h3','h4','h5'):
                serializer.start_block(stylestack)
                serializer.text(elem.text)
                for child in elem:
                    print_elem(stylestack,serializer,child)
                    serializer.start_inline(stylestack)
                    serializer.text(child.tail)
                    serializer.end_entity()
                serializer.end_entity()

            elif elem.tag in ('span','em','b','left','right'):
                serializer.start_inline(stylestack)
                serializer.text(elem.text)
                for child in elem:
                    print_elem(stylestack,serializer,child)
                    serializer.start_inline(stylestack)
                    serializer.text(child.tail)
                    serializer.end_entity()
                serializer.end_entity()

            elif elem.tag == 'value':
                serializer.start_inline(stylestack)
                serializer.pre(format_value( 
                                              elem.text,
                                              decimals=stylestack.get('value-decimals'),
                                              width=stylestack.get('value-width'),
                                              decimals_separator=stylestack.get('value-decimals-separator'),
                                              thousands_separator=stylestack.get('value-thousands-separator'),
                                              autoint=(stylestack.get('value-autoint') == 'on'),
                                              symbol=stylestack.get('value-symbol'),
                                              position=stylestack.get('value-symbol-position') 
                                            ))
                serializer.end_entity()

            elif elem.tag == 'line':
                width = stylestack.get('width')
                if stylestack.get('size') in ('double', 'double-width'):
                    width = width / 2

                lineserializer = XmlLineSerializer(stylestack.get('indent')+indent,stylestack.get('tabwidth'),width,stylestack.get('line-ratio'))
                serializer.start_block(stylestack)
                for child in elem:
                    if child.tag == 'left':
                        print_elem(stylestack,lineserializer,child,indent=indent)
                    elif child.tag == 'right':
                        lineserializer.start_right()
                        print_elem(stylestack,lineserializer,child,indent=indent)
                serializer.pre(lineserializer.get_line())
                serializer.end_entity()

            elif elem.tag == 'ul':
                serializer.start_block(stylestack)
                bullet = stylestack.get('bullet')
                for child in elem:
                    if child.tag == 'li':
                        serializer.style(stylestack)
                        serializer.raw(' ' * indent * stylestack.get('tabwidth') + bullet)
                    print_elem(stylestack,serializer,child,indent=indent+1)
                serializer.end_entity()

            elif elem.tag == 'ol':
                cwidth = len(str(len(elem))) + 2
                i = 1
                serializer.start_block(stylestack)
                for child in elem:
                    if child.tag == 'li':
                        serializer.style(stylestack)
                        serializer.raw(' ' * indent * stylestack.get('tabwidth') + ' ' + (str(i)+')').ljust(cwidth))
                        i = i + 1
                    print_elem(stylestack,serializer,child,indent=indent+1)
                serializer.end_entity()

            elif elem.tag == 'pre':
                serializer.start_block(stylestack)
                serializer.pre(elem.text)
                serializer.end_entity()

            elif elem.tag == 'hr':
                width = stylestack.get('width')
                if stylestack.get('size') in ('double', 'double-width'):
                    width = width / 2
                serializer.start_block(stylestack)
                serializer.text('-'*width)
                serializer.end_entity()

            elif elem.tag == 'br':
                serializer.linebreak()

            elif elem.tag == 'img':
                if 'src' in elem.attrib and 'data:' in elem.attrib['src']:
                    self.print_base64_image(bytes(elem.attrib['src'], 'utf-8'))

            elif elem.tag == 'barcode' and 'encoding' in elem.attrib:
                serializer.start_block(stylestack)
                self.barcode(strclean(elem.text),elem.attrib['encoding'])
                serializer.end_entity()

            elif elem.tag == 'cut':
                self.cut()
            elif elem.tag == 'partialcut':
                self.cut(mode='part')
            elif elem.tag == 'cashdraw':
                self.cashdraw(2)
                self.cashdraw(5)

            stylestack.pop()

        try:
            stylestack      = StyleStack() 
            serializer      = XmlSerializer(self)
            root            = ET.fromstring(xml.encode('utf-8'))

            self._raw(stylestack.to_escpos())

            print_elem(stylestack,serializer,root)

            if 'open-cashdrawer' in root.attrib and root.attrib['open-cashdrawer'] == 'true':
                self.cashdraw(2)
                self.cashdraw(5)
            if not 'cut' in root.attrib or root.attrib['cut'] == 'true' :
                self.cut()

        except Exception as e:
            errmsg = str(e)+'\n'+'-'*48+'\n'+traceback.format_exc() + '-'*48+'\n'
            self.text(errmsg)
            self.cut()

            raise e

    def text(self,txt):
        """ Print Utf8 encoded alpha-numeric text """
        if not txt:
            return
        try:
            txt = txt.decode('utf-8')
        except:
            try:
                txt = txt.decode('utf-16')
            except:
                pass

        self.extra_chars = 0
        
        def encode_char(char):  
            """ 
            Encodes a single utf-8 character into a sequence of 
            esc-pos code page change instructions and character declarations 
            """ 
            char_utf8 = char.encode('utf-8')
            encoded  = ''
            encoding = self.encoding # we reuse the last encoding to prevent code page switches at every character
            encodings = {
                    # TODO use ordering to prevent useless switches
                    # TODO Support other encodings not natively supported by python ( Thai, Khazakh, Kanjis )
                    'cp437': TXT_ENC_PC437,
                    'cp850': TXT_ENC_PC850,
                    'cp852': TXT_ENC_PC852,
                    'cp857': TXT_ENC_PC857,
                    'cp858': TXT_ENC_PC858,
                    'cp860': TXT_ENC_PC860,
                    'cp863': TXT_ENC_PC863,
                    'cp865': TXT_ENC_PC865,
                    'cp1251': TXT_ENC_WPC1251,    # win-1251 covers more cyrillic symbols than cp866
                    'cp866': TXT_ENC_PC866,
                    'cp862': TXT_ENC_PC862,
                    'cp720': TXT_ENC_PC720,
                    'cp936': TXT_ENC_PC936,
                    'iso8859_2': TXT_ENC_8859_2,
                    'iso8859_7': TXT_ENC_8859_7,
                    'iso8859_9': TXT_ENC_8859_9,
                    'cp1254'   : TXT_ENC_WPC1254,
                    'cp1255'   : TXT_ENC_WPC1255,
                    'cp1256'   : TXT_ENC_WPC1256,
                    'cp1257'   : TXT_ENC_WPC1257,
                    'cp1258'   : TXT_ENC_WPC1258,
                    'katakana' : TXT_ENC_KATAKANA,
            }
            remaining = copy.copy(encodings)

            if not encoding :
                encoding = 'cp437'

            while True: # Trying all encoding until one succeeds
                try:
                    if encoding == 'katakana': # Japanese characters
                        if jcconv:
                            # try to convert japanese text to a half-katakanas 
                            kata = jcconv.kata2half(jcconv.hira2kata(char_utf8))
                            if kata != char_utf8:
                                self.extra_chars += len(kata.decode('utf-8')) - 1
                                # the conversion may result in multiple characters
                                return encode_str(kata.decode('utf-8')) 
                        else:
                             kata = char_utf8
                        
                        if kata in TXT_ENC_KATAKANA_MAP:
                            encoded = TXT_ENC_KATAKANA_MAP[kata]
                            break
                        else: 
                            raise ValueError()
                    else:
                        # First 127 symbols are covered by cp437.
                        # Extended range is covered by different encodings.
                        encoded = char.encode(encoding)
                        if ord(encoded) <= 127:
                            encoding = 'cp437'
                        break

                except (UnicodeEncodeError, UnicodeWarning, TypeError, ValueError):
                    #the encoding failed, select another one and retry
                    if encoding in remaining:
                        del remaining[encoding]
                    if len(remaining) >= 1:
                        (encoding, _) = remaining.popitem()
                    else:
                        encoding = 'cp437'
                        encoded  = b'\xb1'    # could not encode, output error character
                        break;

            if encoding != self.encoding:
                # if the encoding changed, remember it and prefix the character with
                # the esc-pos encoding change sequence
                self.encoding = encoding
                encoded = bytes(encodings[encoding], 'utf-8') + encoded

            return encoded
        
        def encode_str(txt):
            buffer = b''
            for c in txt:
                buffer += encode_char(c)
            return buffer

        txt = encode_str(txt)

        # if the utf-8 -> codepage conversion inserted extra characters, 
        # remove double spaces to try to restore the original string length
        # and prevent printing alignment issues
        while self.extra_chars > 0: 
            dspace = txt.find('  ')
            if dspace > 0:
                txt = txt[:dspace] + txt[dspace+1:]
                self.extra_chars -= 1
            else:
                break

        self._raw(txt)
        
    def set(self, align='left', font='a', type='normal', width=1, height=1):
        """ Set text properties """
        # Align
        if align.upper() == "CENTER":
            self._raw(TXT_ALIGN_CT)
        elif align.upper() == "RIGHT":
            self._raw(TXT_ALIGN_RT)
        elif align.upper() == "LEFT":
            self._raw(TXT_ALIGN_LT)
        # Font
        if font.upper() == "B":
            self._raw(TXT_FONT_B)
        else:  # DEFAULT FONT: A
            self._raw(TXT_FONT_A)
        # Type
        if type.upper() == "B":
            self._raw(TXT_BOLD_ON)
            self._raw(TXT_UNDERL_OFF)
        elif type.upper() == "U":
            self._raw(TXT_BOLD_OFF)
            self._raw(TXT_UNDERL_ON)
        elif type.upper() == "U2":
            self._raw(TXT_BOLD_OFF)
            self._raw(TXT_UNDERL2_ON)
        elif type.upper() == "BU":
            self._raw(TXT_BOLD_ON)
            self._raw(TXT_UNDERL_ON)
        elif type.upper() == "BU2":
            self._raw(TXT_BOLD_ON)
            self._raw(TXT_UNDERL2_ON)
        elif type.upper == "NORMAL":
            self._raw(TXT_BOLD_OFF)
            self._raw(TXT_UNDERL_OFF)
        # Width
        if width == 2 and height != 2:
            self._raw(TXT_NORMAL)
            self._raw(TXT_2WIDTH)
        elif height == 2 and width != 2:
            self._raw(TXT_NORMAL)
            self._raw(TXT_2HEIGHT)
        elif height == 2 and width == 2:
            self._raw(TXT_2WIDTH)
            self._raw(TXT_2HEIGHT)
        else: # DEFAULT SIZE: NORMAL
            self._raw(TXT_NORMAL)


    def cut(self, mode=''):
        """ Cut paper """
        # Fix the size between last line and cut
        # TODO: handle this with a line feed
        self._raw("\n\n\n\n\n\n")
        if mode.upper() == "PART":
            self._raw(PAPER_PART_CUT)
        else: # DEFAULT MODE: FULL CUT
            self._raw(PAPER_FULL_CUT)


    def cashdraw(self, pin):
        """ Send pulse to kick the cash drawer

        For some reason, with some printers (ex: Epson TM-m30), the cash drawer
        only opens 50% of the time if you just send the pulse. But if you read
        the status afterwards, it opens all the time.
        """
        if pin == 2:
            self._raw(CD_KICK_2)
        elif pin == 5:
            self._raw(CD_KICK_5)
        else:
            raise CashDrawerError()

        self.get_printer_status()

    def hw(self, hw):
        """ Hardware operations """
        if hw.upper() == "INIT":
            self._raw(HW_INIT)
        elif hw.upper() == "SELECT":
            self._raw(HW_SELECT)
        elif hw.upper() == "RESET":
            self._raw(HW_RESET)
        else: # DEFAULT: DOES NOTHING
            pass


    def control(self, ctl):
        """ Feed control sequences """
        if ctl.upper() == "LF":
            self._raw(CTL_LF)
        elif ctl.upper() == "FF":
            self._raw(CTL_FF)
        elif ctl.upper() == "CR":
            self._raw(CTL_CR)
        elif ctl.upper() == "HT":
            self._raw(CTL_HT)
        elif ctl.upper() == "VT":
            self._raw(CTL_VT)

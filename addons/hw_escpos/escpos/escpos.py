#!/usr/bin/python
'''
@author: Manuel F Martinez <manpaz@bashlinux.com>
@organization: Bashlinux
@copyright: Copyright (c) 2012 Bashlinux
@license: GPL
'''

try: 
    import qrcode
except ImportError:
    qrcode = None

import time
import copy
import io
import base64
import math
import md5

from PIL import Image

try:
    import jcconv
except ImportError:
    jcconv = None
    print 'ESC/POS: please install jcconv for improved Japanese receipt printing:'
    print ' # pip install jcconv'

from constants import *
from exceptions import *

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
                return (image_border / 2, image_border / 2)
            else:
                return (image_border / 2, (image_border / 2) + 1)


    def _print_image(self, line, size):
        """ Print formatted image """
        i = 0
        cont = 0
        buffer = ""

       
        self._raw(S_RASTER_N)
        buffer = "%02X%02X%02X%02X" % (((size[0]/size[1])/8), 0, size[1], 0)
        self._raw(buffer.decode('hex'))
        buffer = ""

        while i < len(line):
            hex_string = int(line[i:i+8],2)
            buffer += "%02X" % hex_string
            i += 8
            cont += 1
            if cont % 4 == 0:
                self._raw(buffer.decode("hex"))
                buffer = ""
                cont = 0

    def _raw_print_image(self, line, size, output=None ):
        """ Print formatted image """
        i = 0
        cont = 0
        buffer = ""
        raw = ""

        def __raw(string):
            if output:
                output(string)
            else:
                self._raw(string)
       
        raw += S_RASTER_N
        buffer = "%02X%02X%02X%02X" % (((size[0]/size[1])/8), 0, size[1], 0)
        raw += buffer.decode('hex')
        buffer = ""

        while i < len(line):
            hex_string = int(line[i:i+8],2)
            buffer += "%02X" % hex_string
            i += 8
            cont += 1
            if cont % 4 == 0:
                raw += buffer.decode("hex")
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
            print  "WARNING: Image is wider than 512 and could be truncated at print time "
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

        print 'print_b64_img'

        id = md5.new(img).digest()

        if id not in self.img_cache:
            print 'not in cache'

            img = img[img.find(',')+1:]
            f = io.BytesIO('img')
            f.write(base64.decodestring(img))
            f.seek(0)
            img_rgba = Image.open(f)
            img = Image.new('RGB', img_rgba.size, (255,255,255))
            img.paste(img_rgba, mask=img_rgba.split()[3]) 

            print 'convert image'
        
            pix_line, img_size = self._convert_image(img)

            print 'print image'

            buffer = self._raw_print_image(pix_line, img_size)
            self.img_cache[id] = buffer

        print 'raw image'

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


    def barcode(self, code, bc, width, height, pos, font):
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
        else:
            raise exception.BarcodeCodeError()

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
                    'cp866': TXT_ENC_PC866,
                    'cp862': TXT_ENC_PC862,
                    'cp720': TXT_ENC_PC720,
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
                        encoded = char.encode(encoding)
                        break

                except ValueError: #the encoding failed, select another one and retry
                    if encoding in remaining:
                        del remaining[encoding]
                    if len(remaining) >= 1:
                        encoding = remaining.items()[0][0]
                    else:
                        encoding = 'cp437'
                        encoded  = '\xb1'    # could not encode, output error character
                        break;

            if encoding != self.encoding:
                # if the encoding changed, remember it and prefix the character with
                # the esc-pos encoding change sequence
                self.encoding = encoding
                encoded = encodings[encoding] + encoded

            return encoded
        
        def encode_str(txt):
            buffer = ''
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
        """ Send pulse to kick the cash drawer """
        if pin == 2:
            self._raw(CD_KICK_2)
        elif pin == 5:
            self._raw(CD_KICK_5)
        else:
            raise CashDrawerError()


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

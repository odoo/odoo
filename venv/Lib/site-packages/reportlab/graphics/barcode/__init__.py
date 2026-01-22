#
# Copyright (c) 1996-2000 Tyler C. Sarna <tsarna@sarna.org>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. All advertising materials mentioning features or use of this software
#    must display the following acknowledgement:
#      This product includes software developed by Tyler C. Sarna.
# 4. Neither the name of the author nor the names of contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS
# BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
__all__ = tuple('''registerWidget getCodes getCodeNames createBarcodeDrawing createBarcodeImageInMemory'''.split())
__version__ = '0.9'
__doc__='''Popular barcodes available as reusable widgets'''

_widgets = []
def registerWidget(widget):
    _widgets.append(widget)

def _reset():
    _widgets[:] = []
    from reportlab.graphics.barcode.widgets import BarcodeI2of5, BarcodeCode128, BarcodeStandard93,\
                        BarcodeExtended93, BarcodeStandard39, BarcodeExtended39,\
                        BarcodeMSI, BarcodeCodabar, BarcodeCode11, BarcodeFIM,\
                        BarcodePOSTNET, BarcodeUSPS_4State, BarcodeCode128Auto, BarcodeECC200DataMatrix

    #newer codes will typically get their own module
    from reportlab.graphics.barcode.eanbc import Ean13BarcodeWidget, Ean8BarcodeWidget, UPCA, Ean5BarcodeWidget, ISBNBarcodeWidget
    from reportlab.graphics.barcode.qr import QrCodeWidget
    for widget in (BarcodeI2of5,
                BarcodeCode128,
                BarcodeCode128Auto,
                BarcodeStandard93,
                BarcodeExtended93,
                BarcodeStandard39,
                BarcodeExtended39,
                BarcodeMSI,
                BarcodeCodabar,
                BarcodeCode11,
                BarcodeFIM,
                BarcodePOSTNET,
                BarcodeUSPS_4State,
                Ean13BarcodeWidget,
                Ean8BarcodeWidget,
                UPCA,
                Ean5BarcodeWidget,
                ISBNBarcodeWidget,
                QrCodeWidget,
                BarcodeECC200DataMatrix,
                ):
        registerWidget(widget)
        from reportlab.graphics.barcode import dmtx
        if dmtx.pylibdmtx:
            registerWidget(dmtx.DataMatrixWidget)

_reset()
from reportlab.rl_config import register_reset
register_reset(_reset)

def getCodes():
    """Returns a dict mapping code names to widgets"""
    #the module exports a dictionary of names to widgets, to make it easy for
    #apps and doc tools to display information about them.
    codes = {}
    for widget in _widgets:
        codeName = widget.codeName
        codes[codeName] = widget

    return codes

def getCodeNames():
    """Returns sorted list of supported bar code names"""
    return sorted(getCodes().keys())

def createBarcodeDrawing(codeName, **options):
    """This creates and returns a drawing with a barcode.
    """    
    from reportlab.graphics.shapes import Drawing

    codes = getCodes()
    bcc = codes[codeName]
    width = options.pop('width',None)
    height = options.pop('height',None)
    isoScale = options.pop('isoScale',0)
    kw = {}
    for k,v in options.items():
        if k.startswith('_') or k in bcc._attrMap: kw[k] = v
    bc = bcc(**kw)


    #Robin's new ones validate when setting the value property.
    #Ty Sarna's old ones do not.  We need to test.
    if hasattr(bc, 'validate'):
        bc.validate()   #raise exception if bad value
        if not bc.valid:
            raise ValueError("Illegal barcode with value '%s' in code '%s'" % (options.get('value',None), codeName))

    #size it after setting the data    
    x1, y1, x2, y2 = bc.getBounds()
    w = float(x2 - x1)
    h = float(y2 - y1)
    sx = width not in ('auto',None)
    sy = height not in ('auto',None)
    if sx or sy:
        sx = sx and width/w or 1.0
        sy = sy and height/h or 1.0
        if isoScale:
            if sx<1.0 and sy<1.0:
                sx = sy = max(sx,sy)
            else:
                sx = sy = min(sx,sy)

        w *= sx
        h *= sy
    else:
        sx = sy = 1

    #bc.x = -sx*x1
    #bc.y = -sy*y1
    d = Drawing(width=w,height=h,transform=[sx,0,0,sy,-sx*x1,-sy*y1])
    d.add(bc, "_bc")
    return d

def createBarcodeImageInMemory(codeName,**options):
    """This creates and returns barcode as an image in memory.
    Takes same arguments as createBarcodeDrawing and also an
    optional format keyword which can be anything acceptable
    to Drawing.asString eg gif, pdf, tiff, py ......
    """
    format = options.pop('format','png')
    d = createBarcodeDrawing(codeName, **options)
    return d.asString(format)

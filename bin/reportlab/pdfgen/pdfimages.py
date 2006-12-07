#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/pdfgen/pdfimages.py
__version__=''' $Id$ '''
__doc__="""
Image functionality sliced out of canvas.py for generalization
"""

import os
import string
from types import StringType
import reportlab
from reportlab.pdfbase import pdfutils
from reportlab.pdfbase import pdfdoc
from reportlab.lib.utils import fp_str, getStringIO
from reportlab.lib.utils import import_zlib, haveImages


class PDFImage:
    """Wrapper around different "image sources".  You can make images
    from a PIL Image object, a filename (in which case it uses PIL),
    an image we previously cached (optimisation, hardly used these
    days) or a JPEG (which PDF supports natively)."""

    def __init__(self, image, x,y, width=None, height=None, caching=0):
        self.image = image
        self.point = (x,y)
        self.dimensions = (width, height)
        self.filename = None
        self.imageCaching = caching
        # the following facts need to be determined,
        # whatever the source. Declare what they are
        # here for clarity.
        self.colorSpace = 'DeviceRGB'
        self.bitsPerComponent = 8
        self.filters = []
        self.source = None # JPEG or PIL, set later
        self.getImageData()

    def jpg_imagedata(self):
        #directly process JPEG files
        #open file, needs some error handling!!
        fp = open(self.image, 'rb')
        result = self._jpg_imagedata(fp)
        fp.close()
        return result

    def _jpg_imagedata(self,imageFile):
        self.source = 'JPEG'
        info = pdfutils.readJPEGInfo(imageFile)
        imgwidth, imgheight = info[0], info[1]
        if info[2] == 1:
            colorSpace = 'DeviceGray'
        elif info[2] == 3:
            colorSpace = 'DeviceRGB'
        else: #maybe should generate an error, is this right for CMYK?
            colorSpace = 'DeviceCMYK'
        imageFile.seek(0) #reset file pointer
        imagedata = []
        #imagedata.append('BI /Width %d /Height /BitsPerComponent 8 /ColorSpace /%s /Filter [/Filter [ /ASCII85Decode /DCTDecode] ID' % (info[0], info[1], colorSpace))
        imagedata.append('BI /W %d /H %d /BPC 8 /CS /%s /F [/A85 /DCT] ID' % (imgwidth, imgheight, colorSpace))
        #write in blocks of (??) 60 characters per line to a list
        compressed = imageFile.read()
        encoded = pdfutils._AsciiBase85Encode(compressed)
        pdfutils._chunker(encoded,imagedata)
        imagedata.append('EI')
        return (imagedata, imgwidth, imgheight)

    def cache_imagedata(self):
        image = self.image
        if not pdfutils.cachedImageExists(image):
            zlib = import_zlib()
            if not zlib: return
            if not haveImages: return
            pdfutils.cacheImageFile(image)

        #now we have one cached, slurp it in
        cachedname = os.path.splitext(image)[0] + '.a85'
        imagedata = open(cachedname,'rb').readlines()
        #trim off newlines...
        imagedata = map(string.strip, imagedata)
        return imagedata

    def PIL_imagedata(self):
        image = self.image
        if image.format=='JPEG':
            fp=image.fp
            fp.seek(0)
            return self._jpg_imagedata(fp)
        self.source = 'PIL'
        zlib = import_zlib()
        if not zlib: return
        myimage = image.convert('RGB')
        imgwidth, imgheight = myimage.size

        # this describes what is in the image itself
        # *NB* according to the spec you can only use the short form in inline images
        #imagedata=['BI /Width %d /Height /BitsPerComponent 8 /ColorSpace /%s /Filter [/Filter [ /ASCII85Decode /FlateDecode] ID]' % (imgwidth, imgheight,'RGB')]
        imagedata=['BI /W %d /H %d /BPC 8 /CS /RGB /F [/A85 /Fl] ID' % (imgwidth, imgheight)]

        #use a flate filter and Ascii Base 85 to compress
        raw = myimage.tostring()
        assert(len(raw) == imgwidth * imgheight, "Wrong amount of data for image")
        compressed = zlib.compress(raw)   #this bit is very fast...
        encoded = pdfutils._AsciiBase85Encode(compressed) #...sadly this may not be
        #append in blocks of 60 characters
        pdfutils._chunker(encoded,imagedata)
        imagedata.append('EI')
        return (imagedata, imgwidth, imgheight)

    def getImageData(self):
        "Gets data, height, width - whatever type of image"
        image = self.image
        (width, height) = self.dimensions

        if type(image) == StringType:
            self.filename = image
            if os.path.splitext(image)[1] in ['.jpg', '.JPG', '.jpeg', '.JPEG']:
                (imagedata, imgwidth, imgheight) = self.jpg_imagedata()
            else:
                if not self.imageCaching:
                    imagedata = pdfutils.cacheImageFile(image,returnInMemory=1)
                else:
                    imagedata = self.cache_imagedata()
                #parse line two for width, height
                words = string.split(imagedata[1])
                imgwidth = string.atoi(words[1])
                imgheight = string.atoi(words[3])
        else:
            import sys
            if sys.platform[0:4] == 'java':
                #jython, PIL not available
                (imagedata, imgwidth, imgheight) = self.JAVA_imagedata()
            else:
                (imagedata, imgwidth, imgheight) = self.PIL_imagedata()
        #now build the PDF for the image.
        if not width:
            width = imgwidth
        if not height:
            height = imgheight
        self.width = width
        self.height = height
        self.imageData = imagedata

    def drawInlineImage(self, canvas): #, image, x,y, width=None,height=None):
        """Draw an Image into the specified rectangle.  If width and
        height are omitted, they are calculated from the image size.
        Also allow file names as well as images.  This allows a
        caching mechanism"""
        (x,y) = self.point
        # this says where and how big to draw it
        if not canvas.bottomup: y = y+self.height
        canvas._code.append('q %s 0 0 %s cm' % (fp_str(self.width), fp_str(self.height, x, y)))
        # self._code.extend(imagedata) if >=python-1.5.2
        for line in self.imageData:
            canvas._code.append(line)
        canvas._code.append('Q')

    def format(self, document):
        """Allow it to be used within pdfdoc framework.  This only
        defines how it is stored, not how it is drawn later."""

        dict = pdfdoc.PDFDictionary()
        dict['Type'] = '/XObject'
        dict['Subtype'] = '/Image'
        dict['Width'] = self.width
        dict['Height'] = self.height
        dict['BitsPerComponent'] = 8
        dict['ColorSpace'] = pdfdoc.PDFName(self.colorSpace)
        content = string.join(self.imageData[3:-1], '\n') + '\n'
        strm = pdfdoc.PDFStream(dictionary=dict, content=content)
        return strm.format(document)

if __name__=='__main__':
    srcfile = os.path.join(
                os.path.dirname(reportlab.__file__),
                'test',
                'pythonpowered.gif'
                )
    assert os.path.isfile(srcfile), 'image not found'
    pdfdoc.LongFormat = 1
    img = PDFImage(srcfile, 100, 100)
    import pprint
    doc = pdfdoc.PDFDocument()
    print 'source=',img.source
    print img.format(doc)

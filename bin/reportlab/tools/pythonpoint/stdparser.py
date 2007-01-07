"""
Parser for PythonPoint using the xmllib.py in the standard Python
distribution.  Slow, but always present.  We intend to add new parsers
as Python 2.x and the XML package spread in popularity and stabilise.

The parser has a getPresentation method; it is called from
pythonpoint.py.
"""

import string, imp, sys, os, copy
from reportlab.lib.utils import SeqTypes
from reportlab.lib import xmllib
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER, TA_JUSTIFY
from reportlab.lib.utils import recursiveImport
from reportlab.tools.pythonpoint import pythonpoint
from reportlab.platypus import figures


def getModule(modulename,fromPath='reportlab.tools.pythonpoint.styles'):
    """Get a module containing style declarations.

    Search order is:
        reportlab/tools/pythonpoint/
        reportlab/tools/pythonpoint/styles/
        ./
    """

    try:
        exec 'from reportlab.tools.pythonpoint import '+modulename
        return eval(modulename)
    except ImportError:
        try:
            exec 'from reportlab.tools.pythonpoint.styles import '+modulename
            return eval(modulename)
        except ImportError:
            exec 'import '+modulename
            return eval(modulename)


class PPMLParser(xmllib.XMLParser):
    attributes = {
        #this defines the available attributes for all objects,
        #and their default values.  Although these don't have to
        #be strings, the ones parsed from the XML do, so
        #everything is a quoted string and the parser has to
        #convert these to numbers where appropriate.
        'stylesheet': {
            'path':'None',
            'module':'None',
            'function':'getParagraphStyles'
            },
        'frame': {
            'x':'0',
            'y':'0',
            'width':'0',
            'height':'0',
            'border':'false',
            'leftmargin':'0',    #this is ignored
            'topmargin':'0',     #this is ignored
            'rightmargin':'0',   #this is ignored
            'bottommargin':'0',  #this is ignored
            },
        'slide': {
            'id':'None',
            'title':'None',
            'effectname':'None',     # Split, Blinds, Box, Wipe, Dissolve, Glitter
            'effectdirection':'0',   # 0,90,180,270
            'effectdimension':'H',   # H or V - horizontal or vertical
            'effectmotion':'I',      # Inwards or Outwards
            'effectduration':'1',    #seconds,
            'outlineentry':'None',
            'outlinelevel':'0'       # 1 is a child, 2 is a grandchild etc.
            },
        'para': {
            'style':'Normal',
            'bullettext':'',
            'effectname':'None',
            'effectdirection':'0',
            'effectdimension':'H',
            'effectmotion':'I',
            'effectduration':'1'
            },
        'image': {
            'filename':'',
            'width':'None',
            'height':'None',
            'effectname':'None',
            'effectdirection':'0',
            'effectdimension':'H',
            'effectmotion':'I',
            'effectduration':'1'
            },
        'table': {
            'widths':'None',
            'heights':'None',
            'fieldDelim':',',
            'rowDelim':'\n',
            'style':'None',
            'effectname':'None',
            'effectdirection':'0',
            'effectdimension':'H',
            'effectmotion':'I',
            'effectduration':'1'
            },
        'rectangle': {
            'x':'0',
            'y':'0',
            'width':'100',
            'height':'100',
            'fill':'None',
            'stroke':'(0,0,0)',
            'linewidth':'0',
            'effectname':'None',
            'effectdirection':'0',
            'effectdimension':'H',
            'effectmotion':'I',
            'effectduration':'1'
            },
        'roundrect': {
            'x':'0',
            'y':'0',
            'width':'100',
            'height':'100',
            'radius':'6',
            'fill':'None',
            'stroke':'(0,0,0)',
            'linewidth':'0',
            'effectname':'None',
            'effectdirection':'0',
            'effectdimension':'H',
            'effectmotion':'I',
            'effectduration':'1'
            },
        'line': {
            'x1':'0',
            'y1':'0',
            'x2':'100',
            'y2':'100',
            'stroke':'(0,0,0)',
            'width':'0',
            'effectname':'None',
            'effectdirection':'0',
            'effectdimension':'H',
            'effectmotion':'I',
            'effectduration':'1'
            },
        'ellipse': {
            'x1':'0',
            'y1':'0',
            'x2':'100',
            'y2':'100',
            'stroke':'(0,0,0)',
            'fill':'None',
            'linewidth':'0',
            'effectname':'None',
            'effectdirection':'0',
            'effectdimension':'H',
            'effectmotion':'I',
            'effectduration':'1'
            },
        'polygon': {
            'points':'(0,0),(50,0),(25,25)',
            'stroke':'(0,0,0)',
            'linewidth':'0',
            'stroke':'(0,0,0)',
            'fill':'None',
            'effectname':'None',
            'effectdirection':'0',
            'effectdimension':'H',
            'effectmotion':'I',
            'effectduration':'1'
            },
        'string':{
            'x':'0',
            'y':'0',
            'color':'(0,0,0)',
            'font':'Times-Roman',
            'size':'12',
            'align':'left',
            'effectname':'None',
            'effectdirection':'0',
            'effectdimension':'H',
            'effectmotion':'I',
            'effectduration':'1'
            },
        'customshape':{
            'path':'None',
            'module':'None',
            'class':'None',
            'initargs':'None'
            }
        }

    def __init__(self):
        self.presentations = []
        #yes, I know a generic stack would be easier...
        #still, testing if we are 'in' something gives
        #a degree of validation.
        self._curPres = None
        self._curSection = None
        self._curSlide = None
        self._curFrame = None
        self._curPara = None    #the only places we are interested in
        self._curPrefmt = None
        self._curPyCode = None
        self._curString = None
        self._curTable = None
        self._curTitle = None
        self._curAuthor = None
        self._curSubject = None
        self.fx = 1
        xmllib.XMLParser.__init__(self)

    def _arg(self,tag,args,name):
        "What's this for???"
        if args.has_key(name):
            v = args[name]
        else:
            if self.attributes.has_key(tag):
                v = self.attributes[tag][name]
            else:
                v = None
        return v

    def ceval(self,tag,args,name):
        if args.has_key(name):
            v = args[name]
        else:
            if self.attributes.has_key(tag):
                v = self.attributes[tag][name]
            else:
                return None

        # handle named colors (names from reportlab.lib.colors)
        if name in ('color', 'stroke', 'fill'):
            v = str(pythonpoint.checkColor(v))

        return eval(v)

    def getPresentation(self):
        return self._curPres


    def handle_data(self, data):
        #the only data should be paragraph text, preformatted para
        #text, 'string text' for a fixed string on the page,
        #or table data

        if self._curPara:
            self._curPara.rawtext = self._curPara.rawtext + data
        elif self._curPrefmt:
            self._curPrefmt.rawtext = self._curPrefmt.rawtext + data
        elif self._curPyCode:
            self._curPyCode.rawtext = self._curPyCode.rawtext + data
        elif  self._curString:
            self._curString.text = self._curString.text + data
        elif self._curTable:
            self._curTable.rawBlocks.append(data)
        elif self._curTitle <> None:  # need to allow empty strings,
            # hence explicitly testing for None
            self._curTitle = self._curTitle + data
        elif self._curAuthor <> None:
            self._curAuthor = self._curAuthor + data
        elif self._curSubject <> None:
            self._curSubject = self._curSubject + data

    def handle_cdata(self, data):
        #just append to current paragraph text, so we can quote XML
        if self._curPara:
            self._curPara.rawtext = self._curPara.rawtext + data
        elif self._curPrefmt:
            self._curPrefmt.rawtext = self._curPrefmt.rawtext + data
        elif self._curPyCode:
            self._curPyCode.rawtext = self._curPyCode.rawtext + data
        elif  self._curString:
            self._curString.text = self._curString.text + data
        elif self._curTable:
            self._curTable.rawBlocks.append(data)
        elif self._curAuthor <> None:
            self._curAuthor = self._curAuthor + data
        elif self._curSubject <> None:
            self._curSubject = self._curSubject + data

    def start_presentation(self, args):
        self._curPres = pythonpoint.PPPresentation()
        self._curPres.filename = self._arg('presentation',args,'filename')
        self._curPres.effectName = self._arg('presentation',args,'effect')
        self._curPres.pageDuration = self._arg('presentation',args,'pageDuration')

        h = self._arg('presentation',args,'pageHeight')
        if h:
            self._curPres.pageHeight = h
        w = self._arg('presentation',args,'pageWidth')
        if w:
            self._curPres.pageWidth = w
        #print 'page size =', self._curPres.pageSize

    def end_presentation(self):
        pass
##        print 'Fully parsed presentation',self._curPres.filename

    def start_title(self, args):
        self._curTitle = ''


    def end_title(self):
        self._curPres.title = self._curTitle
        self._curTitle = None

    def start_author(self, args):
        self._curAuthor = ''

    def end_author(self):
        self._curPres.author = self._curAuthor
        self._curAuthor = None

    def start_subject(self, args):
        self._curSubject = ''

    def end_subject(self):
        self._curPres.subject = self._curSubject
        self._curSubject = None

    def start_stylesheet(self, args):
        #makes it the current style sheet.
        path = self._arg('stylesheet',args,'path')
        if path=='None': path = []
        if type(path) not in SeqTypes: path = [path]
        path.append('styles')
        path.append(os.getcwd())
        modulename = self._arg('stylesheet', args, 'module')
        funcname = self._arg('stylesheet', args, 'function')
        try:
            found = imp.find_module(modulename, path)
            (file, pathname, description) = found
            mod = imp.load_module(modulename, file, pathname, description)
        except ImportError:
            #last gasp
            mod = getModule(modulename)

        #now get the function
        func = getattr(mod, funcname)
        pythonpoint.setStyles(func())
##        print 'set global stylesheet to %s.%s()' % (modulename, funcname)

    def end_stylesheet(self):
        pass

    def start_section(self, args):
        name = self._arg('section',args,'name')
        self._curSection = pythonpoint.PPSection(name)

    def end_section(self):
        self._curSection = None


    def start_slide(self, args):
        s = pythonpoint.PPSlide()
        s.id = self._arg('slide',args,'id')
        s.title = self._arg('slide',args,'title')
        a = self._arg('slide',args,'effectname')
        if a <> 'None':
            s.effectName = a
        s.effectDirection = self.ceval('slide',args,'effectdirection')
        s.effectDimension = self._arg('slide',args,'effectdimension')
        s.effectDuration = self.ceval('slide',args,'effectduration')
        s.effectMotion = self._arg('slide',args,'effectmotion')

        #HACK - may not belong here in the long run...
        #by default, use the slide title for the outline entry,
        #unless it is specified as an arg.
        a = self._arg('slide',args,'outlineentry')
        if a == "Hide":
            s.outlineEntry = None
        elif a <> 'None':
            s.outlineEntry = a
        else:
            s.outlineEntry = s.title

        s.outlineLevel = self.ceval('slide',args,'outlinelevel')

        #let it know its section, which may be none
        s.section = self._curSection
        self._curSlide = s

    def end_slide(self):
        self._curPres.slides.append(self._curSlide)
        self._curSlide = None

    def start_frame(self, args):
        self._curFrame = pythonpoint.PPFrame(
            self.ceval('frame',args,'x'),
            self.ceval('frame',args,'y'),
            self.ceval('frame',args,'width'),
            self.ceval('frame',args,'height')
            )
        if self._arg('frame',args,'border')=='true':
            self._curFrame.showBoundary = 1

    def end_frame(self):
        self._curSlide.frames.append(self._curFrame)
        self._curFrame = None

    def start_notes(self, args):
        name = self._arg('notes',args,'name')
        self._curNotes = pythonpoint.PPNotes()

    def end_notes(self):
        self._curSlide.notes.append(self._curNotes)
        self._curNotes = None

    def start_registerFont(self, args):
        name = self._arg('font',args,'name')
        path = self._arg('font',args,'path')
        pythonpoint.registerFont0(self.sourceFilename, name, path)


    def end_registerFont(self):
        pass


    def pack_slide(self, element, args):
        if self.fx:
            effectName = self._arg(element,args,'effectname')
            if effectName <> 'None':
                curSlide = copy.deepcopy(self._curSlide)
                if self._curFrame:
                    curFrame = copy.deepcopy(self._curFrame)
                    curSlide.frames.append(curFrame)
                self._curPres.slides.append(curSlide)
                self._curSlide.effectName = effectName
                self._curSlide.effectDirection = self.ceval(element,args,'effectdirection')
                self._curSlide.effectDimension = self._arg(element,args,'effectdimension')
                self._curSlide.effectDuration = self.ceval(element,args,'effectduration')
                self._curSlide.effectMotion = self._arg(element,args,'effectmotion')
                self._curSlide.outlineEntry = None

    def start_para(self, args):
        self.pack_slide('para', args)
        self._curPara = pythonpoint.PPPara()
        self._curPara.style = self._arg('para',args,'style')

        # hack - bullet character if bullet style
        bt = self._arg('para',args,'bullettext')
        if bt == '':
            if self._curPara.style == 'Bullet':
                bt = '\xc2\xb7'  # Symbol Font bullet character, reasonable default
            elif self._curPara.style == 'Bullet2':
                bt = '\xc2\xb7'  # second-level bullet
            else:
                bt = None

        self._curPara.bulletText = bt

    def end_para(self):
        if self._curFrame:
            self._curFrame.content.append(self._curPara)
            self._curPara = None
        elif self._curNotes:
            self._curNotes.content.append(self._curPara)
            self._curPara = None


    def start_prefmt(self, args):
        self._curPrefmt = pythonpoint.PPPreformattedText()
        self._curPrefmt.style = self._arg('prefmt',args,'style')


    def end_prefmt(self):
        self._curFrame.content.append(self._curPrefmt)
        self._curPrefmt = None


    def start_pycode(self, args):
        self._curPyCode = pythonpoint.PPPythonCode()
        self._curPyCode.style = self._arg('pycode',args,'style')


    def end_pycode(self):
        self._curFrame.content.append(self._curPyCode)
        self._curPyCode = None


    def start_image(self, args):
        self.pack_slide('image',args)
        sourceFilename = self.sourceFilename # XXX
        filename = self._arg('image',args,'filename')
        filename = os.path.join(os.path.dirname(sourceFilename), filename)
        self._curImage = pythonpoint.PPImage()
        self._curImage.filename = filename
        self._curImage.width = self.ceval('image',args,'width')
        self._curImage.height = self.ceval('image',args,'height')


    def end_image(self):
        self._curFrame.content.append(self._curImage)
        self._curImage = None


    def start_table(self, args):
        self.pack_slide('table',args)
        self._curTable = pythonpoint.PPTable()
        self._curTable.widths = self.ceval('table',args,'widths')
        self._curTable.heights = self.ceval('table',args,'heights')
        #these may contain escapes like tabs - handle with
        #a bit more care.
        if args.has_key('fieldDelim'):
            self._curTable.fieldDelim = eval('"' + args['fieldDelim'] + '"')
        if args.has_key('rowDelim'):
            self._curTable.rowDelim = eval('"' + args['rowDelim'] + '"')
        if args.has_key('style'):
            self._curTable.style = args['style']


    def end_table(self):
        self._curFrame.content.append(self._curTable)
        self._curTable = None


    def start_spacer(self, args):
        """No contents so deal with it here."""
        sp = pythonpoint.PPSpacer()
        sp.height = eval(args['height'])
        self._curFrame.content.append(sp)


    def end_spacer(self):
        pass


    ## the graphics objects - go into either the current section
    ## or the current slide.
    def start_fixedimage(self, args):
        sourceFilename = self.sourceFilename
        filename = self._arg('image',args,'filename')
        filename = os.path.join(os.path.dirname(sourceFilename), filename)
        img = pythonpoint.PPFixedImage()
        img.filename = filename
        img.x = self.ceval('fixedimage',args,'x')
        img.y = self.ceval('fixedimage',args,'y')
        img.width = self.ceval('fixedimage',args,'width')
        img.height = self.ceval('fixedimage',args,'height')
        self._curFixedImage = img


    def end_fixedimage(self):
        if self._curSlide:
            self._curSlide.graphics.append(self._curFixedImage)
        elif self._curSection:
            self._curSection.graphics.append(self._curFixedImage)
        self._curFixedImage = None


    def start_rectangle(self, args):
        self.pack_slide('rectangle', args)
        rect = pythonpoint.PPRectangle(
                    self.ceval('rectangle',args,'x'),
                    self.ceval('rectangle',args,'y'),
                    self.ceval('rectangle',args,'width'),
                    self.ceval('rectangle',args,'height')
                    )
        rect.fillColor = self.ceval('rectangle',args,'fill')
        rect.strokeColor = self.ceval('rectangle',args,'stroke')
        self._curRectangle = rect


    def end_rectangle(self):
        if self._curSlide:
            self._curSlide.graphics.append(self._curRectangle)
        elif self._curSection:
            self._curSection.graphics.append(self._curRectangle)
        self._curRectangle = None


    def start_roundrect(self, args):
        self.pack_slide('roundrect', args)
        rrect = pythonpoint.PPRoundRect(
                    self.ceval('roundrect',args,'x'),
                    self.ceval('roundrect',args,'y'),
                    self.ceval('roundrect',args,'width'),
                    self.ceval('roundrect',args,'height'),
                    self.ceval('roundrect',args,'radius')
                    )
        rrect.fillColor = self.ceval('roundrect',args,'fill')
        rrect.strokeColor = self.ceval('roundrect',args,'stroke')
        self._curRoundRect = rrect


    def end_roundrect(self):
        if self._curSlide:
            self._curSlide.graphics.append(self._curRoundRect)
        elif self._curSection:
            self._curSection.graphics.append(self._curRoundRect)
        self._curRoundRect = None


    def start_line(self, args):
        self.pack_slide('line', args)
        self._curLine = pythonpoint.PPLine(
                    self.ceval('line',args,'x1'),
                    self.ceval('line',args,'y1'),
                    self.ceval('line',args,'x2'),
                    self.ceval('line',args,'y2')
                    )
        self._curLine.strokeColor = self.ceval('line',args,'stroke')


    def end_line(self):
        if self._curSlide:
            self._curSlide.graphics.append(self._curLine)
        elif self._curSection:
            self._curSection.graphics.append(self._curLine)
        self._curLine = None


    def start_ellipse(self, args):
        self.pack_slide('ellipse', args)
        self._curEllipse = pythonpoint.PPEllipse(
                    self.ceval('ellipse',args,'x1'),
                    self.ceval('ellipse',args,'y1'),
                    self.ceval('ellipse',args,'x2'),
                    self.ceval('ellipse',args,'y2')
                    )
        self._curEllipse.strokeColor = self.ceval('ellipse',args,'stroke')
        self._curEllipse.fillColor = self.ceval('ellipse',args,'fill')


    def end_ellipse(self):
        if self._curSlide:
            self._curSlide.graphics.append(self._curEllipse)
        elif self._curSection:
            self._curSection.graphics.append(self._curEllipse)
        self._curEllipse = None


    def start_polygon(self, args):
        self.pack_slide('polygon', args)
        self._curPolygon = pythonpoint.PPPolygon(self.ceval('polygon',args,'points'))
        self._curPolygon.strokeColor = self.ceval('polygon',args,'stroke')
        self._curPolygon.fillColor = self.ceval('polygon',args,'fill')


    def end_polygon(self):
        if self._curSlide:
            self._curSlide.graphics.append(self._curPolygon)
        elif self._curSection:
            self._curSection.graphics.append(self._curPolygon)
        self._curEllipse = None


    def start_string(self, args):
        self.pack_slide('string', args)
        self._curString = pythonpoint.PPString(
                            self.ceval('string',args,'x'),
                            self.ceval('string',args,'y')
                            )
        self._curString.color = self.ceval('string',args,'color')
        self._curString.font = self._arg('string',args,'font')
        self._curString.size = self.ceval('string',args,'size')
        if args['align'] == 'left':
            self._curString.align = TA_LEFT
        elif args['align'] == 'center':
            self._curString.align = TA_CENTER
        elif args['align'] == 'right':
            self._curString.align = TA_RIGHT
        elif args['align'] == 'justify':
            self._curString.align = TA_JUSTIFY
        #text comes later within the tag


    def end_string(self):
        #controller should have set the text
        if self._curSlide:
            self._curSlide.graphics.append(self._curString)
        elif self._curSection:
            self._curSection.graphics.append(self._curString)
        self._curString = None


    def start_infostring(self, args):
        # like a string, but lets them embed page no, author etc.
        self.start_string(args)
        self._curString.hasInfo = 1


    def end_infostring(self):
        self.end_string()


    def start_customshape(self, args):
        #loads one
        path = self._arg('customshape',args,'path')
        if path=='None':
            path = []
        else:
            path=[path]

        # add package root folder and input file's folder to path
        path.append(os.path.dirname(self.sourceFilename))
        path.append(os.path.dirname(pythonpoint.__file__))

        modulename = self._arg('customshape',args,'module')
        funcname = self._arg('customshape',args,'class')
        try:
            found = imp.find_module(modulename, path)
            (file, pathname, description) = found
            mod = imp.load_module(modulename, file, pathname, description)
        except ImportError:
            mod = getModule(modulename)

        #now get the function

        func = getattr(mod, funcname)
        initargs = self.ceval('customshape',args,'initargs')
        self._curCustomShape = apply(func, initargs)

    def end_customshape(self):
        if self._curSlide:
            self._curSlide.graphics.append(self._curCustomShape)
        elif self._curSection:
            self._curSection.graphics.append(self._curCustomShape)
        self._curCustomShape = None

    def start_drawing(self, args):
        #loads one
        moduleName = args["module"]
        funcName = args["constructor"]
        showBoundary = int(args.get("showBoundary", "0"))
        hAlign = args.get("hAlign", "CENTER")


        # the path for the imports should include:
        # 1. document directory
        # 2. python path if baseDir not given, or
        # 3. baseDir if given
        try:
            dirName = sdict["baseDir"]
        except:
            dirName = None
        importPath = [os.getcwd()]
        if dirName is None:
            importPath.extend(sys.path)
        else:
            importPath.insert(0, dirName)

        modul = recursiveImport(moduleName, baseDir=importPath)
        func = getattr(modul, funcName)
        drawing = func()

        drawing.hAlign = hAlign
        if showBoundary:
            drawing._showBoundary = 1

        self._curDrawing = pythonpoint.PPDrawing()
        self._curDrawing.drawing = drawing

    def end_drawing(self):
        self._curFrame.content.append(self._curDrawing)
        self._curDrawing = None

    def start_pageCatcherFigure(self, args):
        filename = args["filename"]
        pageNo = int(args["pageNo"])
        width = float(args.get("width", "595"))
        height = float(args.get("height", "842"))
        

        fig = figures.PageCatcherFigureNonA4(filename, pageNo, args.get("caption", ""), width, height)
        sf = args.get('scaleFactor', None)
        if sf: sf = float(sf)
        border = not (args.get('border', None) in ['0','no'])
        
        fig.scaleFactor = sf
        fig.border = border

        #self.ceval('pageCatcherFigure',args,'scaleFactor'),
        #initargs = self.ceval('customshape',args,'initargs')
        self._curFigure = pythonpoint.PPFigure()
        self._curFigure.figure = fig

    def end_pageCatcherFigure(self):
        self._curFrame.content.append(self._curFigure)
        self._curFigure = None

    ## intra-paragraph XML should be allowed through into PLATYPUS
    def unknown_starttag(self, tag, attrs):
        if  self._curPara:
            echo = '<%s' % tag
            for (key, value) in attrs.items():
                echo = echo + ' %s="%s"' % (key, value)
            echo = echo + '>'
            self._curPara.rawtext = self._curPara.rawtext + echo
        else:
            print 'Unknown start tag %s' % tag


    def unknown_endtag(self, tag):
        if  self._curPara:
            self._curPara.rawtext = self._curPara.rawtext + '</%s>'% tag
        else:
            print 'Unknown end tag %s' % tag

    def handle_charref(self, name):
        try:
            if name[0]=='x':
                n = int(name[1:],16)
            else:
                n = int(name)
        except ValueError:
            self.unknown_charref(name)
            return
        self.handle_data(unichr(n).encode('utf8'))

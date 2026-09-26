"""new experimental paragraph implementation

Intended to allow support for paragraphs in paragraphs, hotlinks,
embedded flowables, and underlining.  The main entry point is the
function

def Paragraph(text, style, bulletText=None, frags=None)

Which is intended to be plug compatible with the "usual" platypus
paragraph except that it supports more functionality.

In this implementation you may embed paragraphs inside paragraphs
to create hierarchically organized documents.

This implementation adds the following paragraph-like tags (which
support the same attributes as paragraphs, for font specification, etc).

- Unnumberred lists (ala html)::

    <ul>
        <li>first one</li>
        <li>second one</li>
    </ul>


Also <ul type="disc"> (default) or <ul type="circle">, <ul type="square">.

- Numberred lists (ala html)::

    <ol>
        <li>first one</li>
        <li>second one</li>
    </ol>

Also <ul type="1"> (default) or <ul type="a">, <ul type="A">.

- Display lists (ala HTML):

For example

<dl bulletFontName="Helvetica-BoldOblique" spaceBefore="10" spaceAfter="10">
<dt>frogs</dt> <dd>Little green slimy things. Delicious with <b>garlic</b></dd>
<dt>kittens</dt> <dd>cute, furry, not edible</dd>
<dt>bunnies</dt> <dd>cute, furry,. Delicious with <b>garlic</b></dd>
</dl>

ALSO the following additional internal paragraph markup tags are supported

<u>underlined text</u>

<a href="http://www.reportlab.com">hyperlinked text</a>
<a href="http://www.reportlab.com" color="blue">hyperlinked text</a>

<link destination="end" >Go to the end (go to document internal destination)</link>
<link destination="start" color="cyan">Go to the beginning</link>

<setLink destination="start" color="magenta">This is the document start
  (define document destination inside paragraph, color is optional)</setLink>

"""
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.rl_accel import fp_str
from reportlab.platypus.flowables import Flowable
from reportlab.lib import colors
from reportlab.lib.styles import _baseFontName

# SET THIS TO CAUSE A VIEWING BUG WITH ACROREAD 3 (for at least one input)
# CAUSEERROR = 0

debug = 0

DUMPPROGRAM = 0

TOOSMALLSPACE = 1e-5

from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY

# indent changes effect the next line
# align changes effect the current line

# need to fix spacing questions... if ends with space then space may be inserted

# NEGATIVE SPACE SHOULD NEVER BE EXPANDED (IN JUSTIFICATION, EG)

class paragraphEngine:
    # text origin of 0,0 is upper left corner
    def __init__(self, program = None):
        from reportlab.lib.colors import black
        if program is None:
            program = []
        self.lineOpHandlers = [] # for handling underlining and hyperlinking, etc
        self.program = program
        self.indent = self.rightIndent = 0.0
        self.baseindent = 0.0 # adjust this to add more indentation for bullets, eg
        self.fontName = "Helvetica"
        self.fontSize = 10
        self.leading = 12
        self.fontColor = black
        self.x = self.y = self.rise = 0.0
        from reportlab.lib.enums import TA_LEFT
        self.alignment = TA_LEFT
        self.textStateStack = []

    TEXT_STATE_VARIABLES = ("indent", "rightIndent", "fontName", "fontSize",
                            "leading", "fontColor", "lineOpHandlers", "rise",
                            "alignment")
                            #"textStateStack")

    def pushTextState(self):
        state = []
        for var in self.TEXT_STATE_VARIABLES:
            val = getattr(self, var)
            state.append(val)
        #self.textStateStack.append(state)
        self.textStateStack = self.textStateStack+[state] # fresh copy
        #print "push", self.textStateStack
        #print "push", len(self.textStateStack), state
        return state

    def popTextState(self):
        state = self.textStateStack[-1]
        self.textStateStack = self.textStateStack[:-1]
        #print "pop", self.textStateStack
        state = state[:] # copy for destruction
        #print "pop", len(self.textStateStack), state
        #print "handlers before", self.lineOpHandlers
        for var in self.TEXT_STATE_VARIABLES:
            val = state[0]
            del state[0]
            setattr(self, var, val)

    def format(self, maxwidth, maxheight, program, leading=0):
        "return program with line operations added if at least one line fits"
        # note: a generated formatted segment should not be formatted again
        startstate = self.__dict__.copy()
        #remainder = self.cleanProgram(program)
        remainder = program[:]
        #program1 = remainder[:] # debug only
        lineprogram = []
        #if maxheight<TOOSMALLSPACE:
        #    raise ValueError, "attempt to format inside too small a height! "+repr(maxheight)
        heightremaining = maxheight
        if leading: self.leading = leading
        room = 1
        cursorcount = 0 # debug
        while remainder and room: #heightremaining>=self.leading and remainder:
            #print "getting line with statestack", len(self.textStateStack)
            #heightremaining = heightremaining - self.leading
            indent = self.indent
            rightIndent = self.rightIndent
            linewidth = maxwidth - indent - rightIndent
            beforelinestate = self.__dict__.copy()
            if linewidth<TOOSMALLSPACE:
                raise ValueError("indents %s %s too wide for space %s" % (self.indent, self.rightIndent, \
                                                                           maxwidth))
            try:
                (lineIsFull, line, cursor, currentLength, \
                 usedIndent, maxLength, justStrings) = self.fitLine(remainder, maxwidth)
            except:
##                print "failed to fit line near", cursorcount # debug
##                for i in program1[max(0,cursorcount-10): cursorcount]:
##                    print
##                    print i,
##                print "***" *8
##                for i in program1[cursorcount:cursorcount+20]:
##                    print i
                raise
            cursorcount = cursorcount+cursor # debug
            leading = self.leading
            if heightremaining>leading:
                heightremaining = heightremaining-leading
            else:
                room = 0
                #self.resetState(beforelinestate)
                self.__dict__.update(beforelinestate)
                break # no room for this line
##            if debug:
##                print "line", line
##                if lineIsFull: print "is full"
##                else: print "is partially full"
##                print "consumes", cursor, "elements"
##                print "covers", currentLength, "of", maxwidth
            alignment = self.alignment # last declared alignment for this line used
            # recompute linewidth using the used indent
            #linewidth = maxwidth - usedIndent - rightIndent
            remainder = remainder[cursor:]
            if not remainder:
                # trim off the extra end of line
                del line[-1]
            # do justification if any
            #line = self.shrinkWrap(line
            if alignment==TA_LEFT:
                #if debug:
                #    print "ALIGN LEFT"
                if justStrings:
                    line = stringLine(line, currentLength)
                else:
                    line = self.shrinkWrap(line)
                pass
            elif alignment==TA_CENTER:
                #if debug:
                #    print "ALIGN CENTER"
                if justStrings:
                    line = stringLine(line, currentLength)
                else:
                    line = self.shrinkWrap(line)
                line = self.centerAlign(line, currentLength, maxLength)
            elif alignment==TA_RIGHT:
                #if debug:
                #    print "ALIGN RIGHT"
                if justStrings:
                    line = stringLine(line, currentLength)
                else:
                    line = self.shrinkWrap(line)
                line = self.rightAlign(line, currentLength, maxLength)
            elif alignment==TA_JUSTIFY:
                #if debug:
                #    print "JUSTIFY"
                if remainder and lineIsFull:
                    if justStrings:
                        line = simpleJustifyAlign(line, currentLength, maxLength)
                    else:
                        line = self.justifyAlign(line, currentLength, maxLength)
                else:
                    if justStrings:
                        line = stringLine(line, currentLength)
                    else:
                        line = self.shrinkWrap(line)
                    if debug:
                        print("no justify because line is not full or end of para")
            else:
                raise ValueError("bad alignment "+repr(alignment))
            if not justStrings:
                line = self.cleanProgram(line)
            lineprogram.extend(line)
        laststate = self.__dict__.copy()
        #self.resetState(startstate)
        self.__dict__.update(startstate)
        heightused = maxheight - heightremaining
        return (lineprogram, remainder, laststate, heightused)

    def getState(self):
        # inlined
        return self.__dict__.copy()

    def resetState(self, state):
        # primarily inlined
        self.__dict__.update(state)

##    def sizeOfWord(self, word):
##        inlineThisFunctionForEfficiency
##        return float(stringWidth(word, self.fontName, self.fontSize))

    def fitLine(self, program, totalLength):
        "fit words (and other things) onto a line"
        # assuming word lengths and spaces have not been yet added
        # fit words onto a line up to maxlength, adding spaces and respecting extra space
        from reportlab.pdfbase.pdfmetrics import stringWidth
        usedIndent = self.indent
        maxLength = totalLength - usedIndent - self.rightIndent
        done = 0
        line = []
        cursor = 0
        lineIsFull = 0
        currentLength = 0
        maxcursor = len(program)
        needspace = 0
        first = 1
        terminated = None
        fontName = self.fontName
        fontSize = self.fontSize
        spacewidth = stringWidth(" ", fontName, fontSize) #self.sizeOfWord(" ")
        justStrings = 1
        while not done and cursor<maxcursor:
            opcode = program[cursor]
            #if debug: print "opcode", cursor, opcode
            if isinstance(opcode,str) or hasattr(opcode,'width'):
                lastneedspace = needspace
                needspace = 0
                if hasattr(opcode,'width'):
                    justStrings = 0
                    width = opcode.width(self)
                    needspace = 0
                else:
                    saveopcode = opcode
                    opcode = opcode.strip()
                    if opcode:
                        width = stringWidth(opcode, fontName, fontSize)
                    else:
                        width = 0
                    if saveopcode and (width or currentLength):
                        # ignore white space at margin
                        needspace = (saveopcode[-1]==" ")
                    else:
                        needspace = 0
                fullwidth = width
                if lastneedspace:
                    #spacewidth = stringWidth(" ", fontName, fontSize) #self.sizeOfWord(" ")
                    fullwidth = width + spacewidth
                newlength = currentLength+fullwidth
                if newlength>maxLength and not first: # always do at least one thing
                    # this word won't fit
                    #if debug:
                    #    print "WORD", opcode, "wont fit, width", width, "fullwidth", fullwidth
                    #    print "   currentLength", currentLength, "newlength", newlength, "maxLength", maxLength
                    done = 1
                    lineIsFull = 1
                else:
                    # fit the word: add a space then the word
                    if lastneedspace:
                        line.append( spacewidth ) # expandable space: positive
                    if opcode:
                        line.append( opcode )
                    if abs(width)>TOOSMALLSPACE:
                        line.append( -width ) # non expanding space: negative
                        currentLength = newlength
                    #print line
                    #stop
                first = 0
            elif isinstance(opcode,float):
                justStrings = 0
                aopcode = abs(opcode) # negative means non expanding
                if aopcode>TOOSMALLSPACE:
                    nextLength = currentLength+aopcode
                    if nextLength>maxLength and not first: # always do at least one thing
                        #if debug: print "EXPLICIT spacer won't fit", maxLength, nextLength, opcode
                        done = 1
                    else:
                        if aopcode>TOOSMALLSPACE:
                            currentLength = nextLength
                            line.append(opcode)
                    first = 0
            elif isinstance(opcode,tuple):
                justStrings = 0
                indicator = opcode[0]
                #line.append(opcode)
                if indicator=="nextLine":
                    # advance to nextLine
                    #(i, endallmarks) = opcode
                    line.append(opcode)
                    cursor += 1 # consume this element
                    terminated = done = 1
                    #if debug:
                    #    print "nextLine encountered"
                elif indicator=="color":
                    # change fill color
                    oldcolor = self.fontColor
                    (i, colorname) = opcode
                    #print "opcode", opcode
                    if isinstance(colorname,str):
                        color = self.fontColor = getattr(colors, colorname)
                    else:
                        color = self.fontColor = colorname # assume its something sensible :)
                    line.append(opcode)
                elif indicator=="face":
                    # change font face
                    (i, fontname) = opcode
                    fontName = self.fontName = fontname
                    spacewidth = stringWidth(" ", fontName, fontSize) #self.sizeOfWord(" ")
                    line.append(opcode)
                elif indicator=="size":
                    # change font size
                    (i, fontsize) = opcode
                    size = abs(float(fontsize))
                    if isinstance(fontsize,str):
                        if fontsize[:1]=="+":
                            fontSize = self.fontSize = self.fontSize + size
                        elif fontsize[:1]=="-":
                            fontSize = self.fontSize = self.fontSize - size
                        else:
                            fontSize = self.fontSize = size
                    else:
                        fontSize = self.fontSize = size
                    spacewidth = stringWidth(" ", fontName, fontSize) #self.sizeOfWord(" ")
                    line.append(opcode)
                elif indicator=="leading":
                    # change font leading
                    (i, leading) = opcode
                    self.leading = leading
                    line.append(opcode)
                elif indicator=="indent":
                    # increase the indent
                    (i, increment) = opcode
                    indent = self.indent = self.indent + increment
                    if first:
                        usedIndent = max(indent, usedIndent)
                        maxLength = totalLength - usedIndent - self.rightIndent
                    line.append(opcode)
                elif indicator=="push":
                    self.pushTextState()
                    line.append(opcode)
                elif indicator=="pop":
                    try:
                        self.popTextState()
                    except:
##                        print "stack fault near", cursor
##                        for i in program[max(0, cursor-10):cursor+10]:
##                            if i==cursor:
##                                print "***>>>",
##                            print i
                        raise
                    fontName = self.fontName
                    fontSize = self.fontSize
                    spacewidth = stringWidth(" ", fontName, fontSize) #self.sizeOfWord(" ")
                    line.append(opcode)
                elif indicator=="bullet":
                    (i, bullet, indent, font, size) = opcode
                    # adjust for base indent (only at format time -- only execute once)
                    indent = indent + self.baseindent
                    opcode = (i, bullet, indent, font, size)
                    if not first:
                        raise ValueError("bullet not at beginning of line")
                    bulletwidth = float(stringWidth(bullet, font, size))
                    spacewidth = float(stringWidth(" ", font, size))
                    bulletmin = indent+spacewidth+bulletwidth
                    # decrease the line size to allow bullet
                    usedIndent = max(bulletmin, usedIndent)
                    if first:
                        maxLength = totalLength - usedIndent - self.rightIndent
                    line.append(opcode)
                elif indicator=="rightIndent":
                    # increase the right indent
                    (i, increment) = opcode
                    self.rightIndent = self.rightIndent+increment
                    if first:
                        maxLength = totalLength - usedIndent - self.rightIndent
                    line.append(opcode)
                elif indicator=="rise":
                    (i, rise) = opcode
                    newrise = self.rise = self.rise+rise
                    line.append(opcode)
                elif indicator=="align":
                    (i, alignment) = opcode
                    #if debug:
                    #    print "SETTING ALIGNMENT", alignment
                    self.alignment = alignment
                    line.append(opcode)
                elif indicator=="lineOperation":
                    (i, handler) = opcode
                    line.append(opcode)
                    self.lineOpHandlers = self.lineOpHandlers + [handler] # fresh copy
                elif indicator=="endLineOperation":
                    (i, handler) = opcode
                    h = self.lineOpHandlers[:] # fresh copy
                    h.remove(handler)
                    self.lineOpHandlers = h
                    line.append(opcode)

                else:
                    raise ValueError("at format time don't understand indicator "+repr(indicator))
            else:
                raise ValueError("op must be string, float, instance, or tuple "+repr(opcode))
            if not done:
                cursor += 1
                #first = 0
##            if debug:
##                if done:
##                    print "DONE FLAG IS SET"
##                if cursor>=maxcursor:
##                    print "AT END OF PROGRAM"
        if not terminated:
            line.append( ("nextLine", 0) )
        #print "fitline", line
        return (lineIsFull, line, cursor, currentLength, usedIndent, maxLength, justStrings)

    def centerAlign(self, line, lineLength, maxLength):
        diff = maxLength-lineLength
        shift = diff/2.0
        if shift>TOOSMALLSPACE:
            return self.insertShift(line, shift)
        return line

    def rightAlign(self, line, lineLength, maxLength):
        shift = maxLength-lineLength
        #die
        if shift>TOOSMALLSPACE:
            return self.insertShift(line, shift)
        return line

    def insertShift(self, line, shift):
        # insert shift just before first visible element in line
        result = []
        first = 1
        for e in line:
            if first and (isinstance(e,str) or hasattr(e,'width')):
                result.append(shift)
                first = 0
            result.append(e)
        return result

    def justifyAlign(self, line, lineLength, maxLength):
        diff = maxLength-lineLength
        # count EXPANDABLE SPACES AFTER THE FIRST VISIBLE
        spacecount = 0
        visible = 0
        first = 1
        for e in line:
            if isinstance(e,float) and e>TOOSMALLSPACE and visible:
                spacecount += 1
            elif first and (isinstance(e,str) or hasattr(e,'width')):
                visible = 1
                first = 0
        #if debug: print "diff is", diff, "wordcount", wordcount #; die
        if spacecount<1:
            return line
        shift = diff/float(spacecount)
        if shift<=TOOSMALLSPACE:
            #if debug: print "shift too small", shift
            return line
        first = 1
        visible = 0
        result = []
        cursor = 0
        nline = len(line)
        while cursor<nline:
            e = line[cursor]
            result.append(e)
            if first and (isinstance(e,str) or hasattr(e,'width')):
                visible = 1
            elif isinstance(e,float) and e>TOOSMALLSPACE and visible:
                expanded = e+shift
                result[-1] = expanded
            cursor += 1
        return result

##                if not first:
##                    #if debug: print "shifting", shift, e
##                    #result.append(shift)
##                    # add the shift in result before any start markers before e
##                    insertplace = len(result)-1
##                    done = 0
##                    myshift = shift
##                    while insertplace>0 and not done:
##                        beforeplace = insertplace-1
##                        beforething = result[beforeplace]
##                        if isinstance(beforething,tuple):
##                            indicator = beforething[0]
##                            if indicator=="endLineOperation":
##                                done = 1
##                            elif debug:
##                                print "adding shift before", beforething
##                       elif isinstance(beforething,float):
##                            myshift += beforething
##                            del result[beforeplace]
##                        else:
##                            done = 1
##                        if not done:
##                            insertplace = beforeplace
##                    result.insert(insertplace, myshift)
##                first = 0
##            cursor += 1
##        return result

    def shrinkWrap(self, line):
        # for non justified text, collapse adjacent text/shift's into single operations
        result = []
        index = 0
        maxindex = len(line)
        while index<maxindex:
            e = line[index]
            if isinstance(e,str) and index<maxindex-1:
                # collect strings and floats
                thestrings = [e]
                thefloats = 0.0
                index += 1
                nexte = line[index]
                while index<maxindex and isinstance(nexte,(float,str)):
                    # switch to expandable space if appropriate
                    if isinstance(nexte,float):
                        if thefloats<0 and nexte>0:
                            thefloats = -thefloats
                        if nexte<0 and thefloats>0:
                            nexte = -nexte
                        thefloats += nexte
                    elif isinstance(nexte,str):
                        thestrings.append(nexte)
                    index += 1
                    if index<maxindex:
                        nexte = line[index]
                # wrap up the result
                s = ' '.join(thestrings)
                result.append(s)
                result.append(float(thefloats))
                # back up for unhandled element
                index -= 1
            else:
                result.append(e)
            index += 1

        return result

    def cleanProgram(self, line):
        "collapse adjacent spacings"
        #return line # for debugging
        result = []
        last = 0
        for e in line:
            if isinstance(e,float):
                # switch to expandable space if appropriate
                if last<0 and e>0:
                    last = -last
                if e<0 and last>0:
                    e = -e
                last = float(last)+e
            else:
                if abs(last)>TOOSMALLSPACE:
                    result.append(last)
                result.append(e)
                last = 0
        if last:
            result.append(last)
        # now go backwards and delete all floats occurring after all visible elements
##        count = len(result)-1
##        done = 0
##        while count>0 and not done:
##            e = result[count]
##            if hasattr(e,'width') or isinstance(e,str):
##                done = 1
##            elif isinstance(e,float):
##                del result[count]
##            count = count-1
        # move end operations left and start operations left up to visibles
        change = 1
        rline = list(range(len(result)-1))
        while change:
            #print line
            change = 0
            for index in rline:
                nextindex = index+1
                this = result[index]
                next = result[nextindex]
                doswap = 0
                # don't swap visibles
                if isinstance(this,str) or \
                   isinstance(next,str) or \
                   hasattr(this,'width') or hasattr(next,'width'):
                    doswap = 0
                # only swap two tuples if the second one is an end operation and the first is something else
                elif isinstance(this,tuple):
                    thisindicator = this[0]
                    if isinstance(next,tuple):
                        nextindicator = next[0]
                        doswap = 0
                        if (nextindicator=="endLineOperation" and thisindicator!="endLineOperation"
                            and thisindicator!="lineOperation"):
                            doswap = 1 # swap nonend!=end
                    elif isinstance(next,float):
                        if thisindicator=="lineOperation":
                            doswap = 1 # begin != space
                if doswap:
                    #print "swap", line[index],line[nextindex]
                    result[index] = next
                    result[nextindex] = this
                    change = 1
        return result

    def runOpCodes(self, program, canvas, textobject):
        "render the line(s)"

        escape = canvas._escape
        code = textobject._code
        startstate = self.__dict__.copy()
        font = None
        size = None
        # be sure to set them before using them (done lazily below)
        #textobject.setFont(self.fontName, self.fontSize)
        textobject.setFillColor(self.fontColor)
        xstart = self.x
        thislineindent = self.indent
        thislinerightIndent = self.rightIndent
        indented = 0
        for opcode in program:
            if isinstance(opcode,str)  or hasattr(opcode,'width'):
                if not indented:
                    if abs(thislineindent)>TOOSMALLSPACE:
                        #if debug: print "INDENTING", thislineindent
                        #textobject.moveCursor(thislineindent, 0)
                        code.append('%s Td' % fp_str(thislineindent, 0))
                        self.x += thislineindent
                    for handler in self.lineOpHandlers:
                        #handler.end_at(x, y, self, canvas, textobject) # finish, eg, underlining this line
                        handler.start_at(self.x, self.y, self, canvas, textobject) # start underlining the next
                indented = 1
                # lazily set font (don't do it again if not needed)
                if font!=self.fontName or size!=self.fontSize:
                    font = self.fontName
                    size = self.fontSize
                    textobject.setFont(font, size)
                if isinstance(opcode,str):
                    textobject.textOut(opcode)
                else:
                    # drawable thing
                    opcode.execute(self, textobject, canvas)
            elif isinstance(opcode,float):
                # use abs value (ignore expandable marking)
                opcode = abs(opcode)
                if opcode>TOOSMALLSPACE:
                    #textobject.moveCursor(opcode, 0)
                    code.append('%s Td' % fp_str(opcode, 0))
                    self.x += opcode
            elif isinstance(opcode,tuple):
                indicator = opcode[0]
                if indicator=="nextLine":
                    # advance to nextLine
                    (i, endallmarks) = opcode
                    x = self.x
                    y = self.y
                    newy = self.y = self.y-self.leading
                    newx = self.x = xstart
                    thislineindent = self.indent
                    thislinerightIndent = self.rightIndent
                    indented = 0
                    for handler in self.lineOpHandlers:
                        handler.end_at(x, y, self, canvas, textobject) # finish, eg, underlining this line
                        #handler.start_at(newx, newy, self, canvas, textobject)) # start underlining the next
                    textobject.setTextOrigin(newx, newy)
                elif indicator=="color":
                    # change fill color
                    oldcolor = self.fontColor
                    (i, colorname) = opcode
                    #print "opcode", opcode
                    if isinstance(colorname,str):
                        color = self.fontColor = getattr(colors, colorname)
                    else:
                        color = self.fontColor = colorname # assume its something sensible :)
                    #if debug:
                    #    print color.red, color.green, color.blue
                    #    print dir(color)
                    #print "color is", color
                    #from reportlab.lib.colors import green
                    #if color is green: print "color is green"
                    if color!=oldcolor:
                        textobject.setFillColor(color)
                elif indicator=="face":
                    # change font face
                    (i, fontname) = opcode
                    self.fontName = fontname
                    #textobject.setFont(self.fontName, self.fontSize)
                elif indicator=="size":
                    # change font size
                    (i, fontsize) = opcode
                    size = abs(float(fontsize))
                    if isinstance(fontsize,str):
                        if fontsize[:1]=="+":
                            self.fontSize += size
                        elif fontsize[:1]=="-":
                            self.fontSize -= size
                        else:
                            self.fontSize = size
                    else:
                        self.fontSize = size
                    fontSize = self.fontSize 
                    textobject.setFont(self.fontName, self.fontSize)
                elif indicator=="leading":
                    # change font leading
                    (i, leading) = opcode
                    self.leading = leading
                elif indicator=="indent":
                    # increase the indent
                    (i, increment) = opcode
                    indent = self.indent = self.indent + increment
                    thislineindent = max(thislineindent, indent)
                elif indicator=="push":
                    self.pushTextState()
                elif indicator=="pop":
                    oldcolor = self.fontColor
                    oldfont = self.fontName
                    oldsize = self.fontSize
                    self.popTextState()
                    #if CAUSEERROR or oldfont!=self.fontName or oldsize!=self.fontSize:
                    #    textobject.setFont(self.fontName, self.fontSize)
                    if oldcolor!=self.fontColor:
                        textobject.setFillColor(self.fontColor)
                elif indicator=="wordSpacing":
                    (i, ws) = opcode
                    textobject.setWordSpace(ws)
                elif indicator=="bullet":
                    (i, bullet, indent, font, size) = opcode
                    if abs(self.x-xstart)>TOOSMALLSPACE:
                        raise ValueError("bullet not at beginning of line")
                    bulletwidth = float(stringWidth(bullet, font, size))
                    spacewidth = float(stringWidth(" ", font, size))
                    bulletmin = indent+spacewidth+bulletwidth
                    # decrease the line size to allow bullet as needed
                    if bulletmin > thislineindent:
                        #if debug: print "BULLET IS BIG", bullet, bulletmin, thislineindent
                        thislineindent = bulletmin
                    textobject.moveCursor(indent, 0)
                    textobject.setFont(font, size)
                    textobject.textOut(bullet)
                    textobject.moveCursor(-indent, 0)
                    #textobject.textOut("M")
                    textobject.setFont(self.fontName, self.fontSize)
                elif indicator=="rightIndent":
                    # increase the right indent
                    (i, increment) = opcode
                    self.rightIndent = self.rightIndent+increment
                elif indicator=="rise":
                    (i, rise) = opcode
                    newrise = self.rise = self.rise+rise
                    textobject.setRise(newrise)
                elif indicator=="align":
                    (i, alignment) = opcode
                    self.alignment = alignment
                elif indicator=="lineOperation":
                    (i, handler) = opcode
                    handler.start_at(self.x, self.y, self, canvas, textobject)
                    #self.lineOpHandlers.append(handler)
                    #if debug: print "adding", handler, self.lineOpHandlers
                    self.lineOpHandlers = self.lineOpHandlers + [handler] # fresh copy!
                elif indicator=="endLineOperation":
                    (i, handler) = opcode
                    handler.end_at(self.x, self.y, self, canvas, textobject)
                    newh = self.lineOpHandlers = self.lineOpHandlers[:] # fresh copy
                    #if debug: print "removing", handler, self.lineOpHandlers
                    if handler in newh:
                        self.lineOpHandlers.remove(handler)
                    else:
                        pass
                        #print "WARNING: HANDLER", handler, "NOT IN", newh
                else:
                    raise ValueError("don't understand indicator "+repr(indicator))
            else:
                raise ValueError("op must be string float or tuple "+repr(opcode))
        laststate = self.__dict__.copy()
        #self.resetState(startstate)
        self.__dict__.update(startstate)
        return laststate

def stringLine(line, length):
    "simple case: line with just strings and spacings which can be ignored"

    strings = []
    for x in line:
        if isinstance(x,str):
            strings.append(x)
    text = ' '.join(strings)
    result = [text, float(length)]
    nextlinemark = ("nextLine", 0)
    if line and line[-1]==nextlinemark:
        result.append( nextlinemark )
    return result

def simpleJustifyAlign(line, currentLength, maxLength):
    "simple justification with only strings"

    strings = []
    for x in line[:-1]:
        if isinstance(x,str):
            strings.append(x)
    nspaces = len(strings)-1
    slack = maxLength-currentLength
    text = ' '.join(strings)
    if nspaces>0 and slack>0:
        wordspacing = slack/float(nspaces)
        result = [("wordSpacing", wordspacing), text, maxLength, ("wordSpacing", 0)]
    else:
        result = [text, currentLength, ("nextLine", 0)]
    nextlinemark = ("nextLine", 0)
    if line and line[-1]==nextlinemark:
        result.append( nextlinemark )
    return result

from reportlab.lib.colors import black

def readBool(text):
    if text.upper() in ("Y", "YES", "TRUE", "1"):
        return 1
    elif text.upper() in ("N", "NO", "FALSE", "0"):
        return 0
    else:
        raise ValueError("true/false attribute has illegal value '%s'" % text)

def readAlignment(text):
    up = text.upper()
    if up == 'LEFT':
        return TA_LEFT
    elif up == 'RIGHT':
        return TA_RIGHT
    elif up in ['CENTER', 'CENTRE']:
        return TA_CENTER
    elif up == 'JUSTIFY':
        return TA_JUSTIFY

def readLength(text):
    """Read a dimension measurement: accept "3in", "5cm",
    "72 pt" and so on."""
    text = text.strip()
    try:
        return float(text)
    except ValueError:
        text = text.lower()
        numberText, units = text[:-2],text[-2:]
        numberText = numberText.strip()
        try:
            number = float(numberText)
        except ValueError:
            raise ValueError("invalid length attribute '%s'" % text)
        try:
            multiplier = {
                'in':72,
                'cm':28.3464566929,  #72/2.54; is this accurate?
                'mm':2.83464566929,
                'pt':1
                }[units]
        except KeyError:
            raise ValueError("invalid length attribute '%s'" % text)

        return number * multiplier

def lengthSequence(s, converter=readLength):
    """from "(2, 1)" or "2,1" return [2,1], for example"""
    s = s.strip()
    if s[:1]=="(" and s[-1:]==")":
        s = s[1:-1]
    sl = s.split(',')
    sl = [s.strip() for s in sl]
    sl = [converter(s) for s in sl]
    return sl


def readColor(text):
    """Read color names or tuples, RGB or CMYK, and return a Color object."""
    if not text:
        return None
    from reportlab.lib import colors
    from string import letters
    if text[0] in letters:
        return colors.__dict__[text]
    tup = lengthSequence(text)

    msg = "Color tuple must have 3 (or 4) elements for RGB (or CMYC)."
    assert 3 <= len(tup) <= 4, msg
    msg = "Color tuple must have all elements <= 1.0."
    for i in range(len(tup)):
        assert tup[i] <= 1.0, msg

    if len(tup) == 3:
        colClass = colors.Color
    elif len(tup) == 4:
        colClass = colors.CMYKColor
    return colClass(*tup)

class StyleAttributeConverters:
    fontSize=[readLength]
    leading=[readLength]
    leftIndent=[readLength]
    rightIndent=[readLength]
    firstLineIndent=[readLength]
    alignment=[readAlignment]
    spaceBefore=[readLength]
    spaceAfter=[readLength]
    bulletFontSize=[readLength]
    bulletIndent=[readLength]
    textColor=[readColor]
    backColor=[readColor]

class SimpleStyle:
    "simplified paragraph style without all the fancy stuff"
    name = "basic"
    fontName=_baseFontName
    fontSize=10
    leading=12
    leftIndent=0
    rightIndent=0
    firstLineIndent=0
    alignment=TA_LEFT
    spaceBefore=0
    spaceAfter=0
    bulletFontName=_baseFontName
    bulletFontSize=10
    bulletIndent=0
    textColor=black
    backColor=None

    def __init__(self, name, parent=None, **kw):
        mydict = self.__dict__
        if parent:
            for a,b in parent.__dict__.items():
                mydict[a]=b
        for a,b in kw.items():
            mydict[a] =  b

    def addAttributes(self, dictionary):
        for key in dictionary.keys():
            value = dictionary[key]
            if value is not None:
                if hasattr(StyleAttributeConverters, key):
                    converter = getattr(StyleAttributeConverters, key)[0]
                    value = converter(value)
                setattr(self, key, value)


DEFAULT_ALIASES = {
    "h1.defaultStyle": "Heading1",
    "h2.defaultStyle": "Heading2",
    "h3.defaultStyle": "Heading3",
    "h4.defaultStyle": "Heading4",
    "h5.defaultStyle": "Heading5",
    "h6.defaultStyle": "Heading6",
    "title.defaultStyle": "Title",
    "subtitle.defaultStyle": "SubTitle",
    "para.defaultStyle": "Normal",
    "pre.defaultStyle": "Code",
    "ul.defaultStyle": "UnorderedList",
    "ol.defaultStyle": "OrderedList",
    "li.defaultStyle": "Definition",
    }

class FastPara(Flowable):
    "paragraph with no special features (not even a single ampersand!)"

    def __init__(self, style, simpletext):
        #if debug:
        #    print "FAST", id(self)
        if "&" in simpletext:
            raise ValueError("no ampersands please!")
        self.style = style
        self.simpletext = simpletext
        self.lines = None

    def wrap(self, availableWidth, availableHeight):
        simpletext = self.simpletext
        self.availableWidth = availableWidth
        style = self.style
        text = self.simpletext
        rightIndent = style.rightIndent
        leftIndent = style.leftIndent
        leading = style.leading
        font = style.fontName
        size = style.fontSize
        firstindent = style.firstLineIndent
        #textcolor = style.textColor
        words = simpletext.split()
        lines = []
        from reportlab.pdfbase.pdfmetrics import stringWidth
        spacewidth = stringWidth(" ", font, size)
        currentline = []
        currentlength = 0
        firstmaxlength = availableWidth - rightIndent - firstindent
        maxlength = availableWidth - rightIndent - leftIndent
        if maxlength<spacewidth:
            return (spacewidth+rightIndent+firstindent, availableHeight) # need something wider than this!
        if availableHeight<leading:
            return (availableWidth, leading) # need something longer
        if self.lines is None:
            heightused = 0
            cursor = 0
            nwords = len(words)
            done = 0
            #heightused = leading # ???
            while cursor<nwords and not done:
                thismaxlength = maxlength
                if not lines:
                    thismaxlength = firstmaxlength
                thisword = words[cursor]
                thiswordsize = stringWidth(thisword, font, size)
                if currentlength:
                    thiswordsize = thiswordsize+spacewidth
                nextlength = currentlength + thiswordsize
                if not currentlength or nextlength<maxlength:
                    # add the word
                    cursor += 1
                    currentlength = nextlength
                    currentline.append(thisword)
                    #print "currentline", currentline
                else:
                    # emit the line
                    lines.append( (' '.join(currentline), currentlength, len(currentline)) )
                    currentline = []
                    currentlength = 0
                    heightused = heightused+leading
                    if heightused+leading>availableHeight:
                        done = 1
            if currentlength and not done:
                lines.append( (' '.join(currentline), currentlength, len(currentline) ))
                heightused = heightused+leading
            self.lines = lines
            self.height = heightused
            remainder = self.remainder = ' '.join(words[cursor:])
            #print "lines", lines
            #print "remainder is", remainder
        else:
            remainder = None
            heightused = self.height
            lines = self.lines
        if remainder:
            result = (availableWidth, availableHeight+leading) # need to split
        else:
            result = (availableWidth, heightused)
        #if debug: print "wrap is", (availableWidth, availableHeight), result, len(lines)
        return result

    def split(self, availableWidth, availableHeight):
        style = self.style
        leading = style.leading
        if availableHeight<leading:
            return [] # not enough space for split
        lines = self.lines
        if lines is None:
            raise ValueError("must wrap before split")
        remainder = self.remainder
        if remainder:
            next = FastPara(style, remainder)
            return [self,next]
        else:
            return [self]

    def draw(self):
        style = self.style
        lines = self.lines
        rightIndent = style.rightIndent
        leftIndent = style.leftIndent
        leading = style.leading
        font = style.fontName
        size = style.fontSize
        alignment = style.alignment
        firstindent = style.firstLineIndent
        c = self.canv
        escape = c._escape
        #if debug:
        #    print "FAST", id(self), "page number", c.getPageNumber()
        height = self.height
        #if debug:
        #    c.rect(0,0,-1, height-size, fill=1, stroke=1)
        c.translate(0, height-size)
        textobject = c.beginText()
        code = textobject._code
        #textobject.setTextOrigin(0,firstindent)
        textobject.setFont(font, size)
        if style.textColor:
            textobject.setFillColor(style.textColor)
        first = 1
        y = 0
        basicWidth = self.availableWidth - rightIndent
        count = 0
        nlines = len(lines)
        while count<nlines:
            (text, length, nwords) = lines[count]
            count += 1
            thisindent = leftIndent
            if first:
                thisindent = firstindent
            if alignment==TA_LEFT:
                x = thisindent
            elif alignment==TA_CENTER:
                extra = basicWidth - length
                x = thisindent + extra/2.0
            elif alignment==TA_RIGHT:
                extra = basicWidth - length
                x = thisindent + extra
            elif alignment==TA_JUSTIFY:
                x = thisindent
                if count<nlines and nwords>1:
                    # patch from doug@pennatus.com, 9 Nov 2002, no extraspace on last line
                    textobject.setWordSpace((basicWidth-length)/(nwords-1.0))
                else:
                    textobject.setWordSpace(0.0)
            textobject.setTextOrigin(x,y)
            textobject.textOut(text)
            y = y-leading
        c.drawText(textobject)

    def getSpaceBefore(self):
        #if debug:
        #    print "got space before", self.spaceBefore
        return self.style.spaceBefore

    def getSpaceAfter(self):
        #print "got space after", self.spaceAfter
        return self.style.spaceAfter

def defaultContext():
    result = {}
    from reportlab.lib.styles import getSampleStyleSheet
    styles = getSampleStyleSheet()
    for stylenamekey, stylenamevalue in DEFAULT_ALIASES.items():
        result[stylenamekey] = styles[stylenamevalue]
    return result

def buildContext(stylesheet=None):
    result = {}
    from reportlab.lib.styles import getSampleStyleSheet
    if stylesheet is not None:
        # Copy styles with the same name as aliases
        for stylenamekey, stylenamevalue in DEFAULT_ALIASES.items():
            if stylenamekey in stylesheet:
                result[stylenamekey] = stylesheet[stylenamekey]
        # Then make aliases
        for stylenamekey, stylenamevalue in DEFAULT_ALIASES.items():
            if stylenamevalue in stylesheet:
                result[stylenamekey] = stylesheet[stylenamevalue]

    styles = getSampleStyleSheet()
    # Then, fill in defaults if they were not filled yet.
    for stylenamekey, stylenamevalue in DEFAULT_ALIASES.items():
        if stylenamekey not in result and stylenamevalue in styles:
            result[stylenamekey] = styles[stylenamevalue]
    return result

class Para(Flowable):

    spaceBefore = 0
    spaceAfter = 0

    def __init__(self, style, parsedText=None, bulletText=None, state=None, context=None, baseindent=0):
        #print id(self), "para", parsedText
        self.baseindent = baseindent
        self.context = buildContext(context)
        self.parsedText = parsedText
        self.bulletText = bulletText
        self.style1 = style # make sure Flowable doesn't use this unless wanted! call it style1 NOT style
        #self.spaceBefore = self.spaceAfter = 0
        self.program = [] # program before layout
        self.formattedProgram = [] # after layout
        self.remainder = None # follow on paragraph if any
        self.state = state # initial formatting state (for completions)
        if not state:
            self.spaceBefore = style.spaceBefore
            self.spaceAfter = style.spaceAfter
            #self.spaceBefore = "invalid value"
        #if hasattr(self, "spaceBefore") and debug:
        #    print "spaceBefore is", self.spaceBefore, self.parsedText
        self.bold = 0
        self.italic = 0
        self.face = style.fontName
        self.size = style.fontSize

    def getSpaceBefore(self):
        #if debug:
        #    print "got space before", self.spaceBefore
        return self.spaceBefore

    def getSpaceAfter(self):
        #print "got space after", self.spaceAfter
        return self.spaceAfter

    def wrap(self, availableWidth, availableHeight):
        if debug:
            print("WRAPPING", id(self), availableWidth, availableHeight)
            print("   ", self.formattedProgram)
            print("   ", self.program)
        self.availableHeight = availableHeight
        self.myengine = p = paragraphEngine()
        p.baseindent = self.baseindent # for shifting bullets as needed
        parsedText = self.parsedText
        formattedProgram = self.formattedProgram
        state = self.state
        if state:
            leading = state["leading"]
        else:
            leading = self.style1.leading
        program = self.program
        self.cansplit = 1 # until proven otherwise
        if state:
            p.resetState(state)
            p.x = 0
            p.y = 0
            needatleast = state["leading"]
        else:
            needatleast = self.style1.leading
        if availableHeight<=needatleast:
            self.cansplit = 0
            #if debug:
            #    print "CANNOT COMPILE, NEED AT LEAST", needatleast, 'AVAILABLE', availableHeight
            return (availableHeight+1, availableWidth) # cannot split
        if parsedText is None and program is None:
            raise ValueError("need parsedText for formatting")
        if not program:
            self.program = program = self.compileProgram(parsedText)
        if not self.formattedProgram:
            (formattedProgram, remainder, \
             laststate, heightused) = p.format(availableWidth, availableHeight, program, leading)
            self.formattedProgram = formattedProgram
            self.height = heightused
            self.laststate = laststate
            self.remainderProgram = remainder
        else:
            heightused = self.height
            remainder = None
        # too big if there is a remainder
        if remainder:
            # lie about the height: it must be split anyway
            #if debug:
            #    print "I need to split", self.formattedProgram
            #    print "heightused", heightused, "available", availableHeight, "remainder", len(remainder)
            height = availableHeight + 1
            #print "laststate is", laststate
            #print "saving remainder", remainder
            self.remainder = Para(self.style1, parsedText=None, bulletText=None, \
                                  state=laststate, context=self.context)
            self.remainder.program = remainder
            self.remainder.spaceAfter = self.spaceAfter
            self.spaceAfter = 0
        else:
            self.remainder = None # no extra
            height = heightused
            if height>availableHeight:
                height = availableHeight-0.1
            #if debug:
            #    print "giving height", height, "of", availableHeight, self.parsedText
        result = (availableWidth, height)
        if debug:
            (w, h) = result
            if abs(availableHeight-h)<0.2:
                print("exact match???" + repr(availableHeight, h))
            print("wrap is", (availableWidth, availableHeight), result)
        return result

    def split(self, availableWidth, availableHeight):
        #if debug:
        #    print "SPLITTING", id(self), availableWidth, availableHeight
        if availableHeight<=0 or not self.cansplit:
            #if debug:
            #    print "cannot split", availableWidth, "too small"
            return [] # wrap failed to find a split
        self.availableHeight = availableHeight
        formattedProgram = self.formattedProgram
        #print "formattedProgram is", formattedProgram
        if formattedProgram is None:
            raise ValueError("must call wrap before split")
        elif not formattedProgram:
            # no first line in self: fail to split
            return []
        remainder = self.remainder
        if remainder:
            #print "SPLITTING"
            result= [self, remainder]
        else:
            result= [self]
        #if debug: print "split is", result
        return result

    def draw(self):
        p = self.myengine #paragraphEngine()
        formattedProgram = self.formattedProgram
        if formattedProgram is None:
            raise ValueError("must call wrap before draw")
        state = self.state
        laststate = self.laststate
        if state:
            p.resetState(state)
            p.x = 0
            p.y = 0
        c = self.canv
        #if debug:
        #    print id(self), "page number", c.getPageNumber()
        height = self.height
        if state:
            leading = state["leading"]
        else:
            leading = self.style1.leading
        #if debug:
        #    c.rect(0,0,-1, height-self.size, fill=1, stroke=1)
        c.translate(0, height-self.size)
        t = c.beginText()
        #t.setTextOrigin(0,0)
        if DUMPPROGRAM or debug:
            print("="*44, "now running program")
            for x in formattedProgram:
                print(x)
            print("-"*44)
        laststate = p.runOpCodes(formattedProgram, c, t)
        #print laststate["x"], laststate["y"]
        c.drawText(t)

    def compileProgram(self, parsedText, program=None):
        style = self.style1
        # standard parameters
        #program = self.program
        if program is None:
            program = []
        a = program.append
        fn = style.fontName
        # add style information if there was no initial state
        a( ("face", fn ) )
        from reportlab.lib.fonts import ps2tt
        (self.face, self.bold, self.italic) = ps2tt(fn)
        a( ("size", style.fontSize ) )
        self.size = style.fontSize
        a( ("align", style.alignment ) )
        a( ("indent", style.leftIndent ) )
        if style.firstLineIndent:
            a( ("indent", style.firstLineIndent ) ) # must be undone later
        a( ("rightIndent", style.rightIndent ) )
        a( ("leading", style.leading) )
        if style.textColor:
            a( ("color", style.textColor) )
        #a( ("nextLine", 0) ) # clear for next line
        if self.bulletText:
            self.do_bullet(self.bulletText, program)
        self.compileComponent(parsedText, program)
        # now look for a place where to insert the unindent after the first line
        if style.firstLineIndent:
            count = 0
            for x in program:
                count += 1
                if isinstance(x,str) or hasattr(x,'width'):
                    break
            program.insert( count, ("indent", -style.firstLineIndent ) ) # defaults to end if no visibles
        #print "="*8, id(self), "program is"
        #for x in program:
        #    print x
##        print "="*11
##        # check pushes and pops
##        stackcount = 0
##        dump = 0
##        for x in program:
##            if dump:
##                print "dump:", x
##            if isinstance(x,tuple):
##                i = x[0]
##                if i=="push":
##                    stackcount += 1
##                    print " "*stackcount, "push", stackcount
##                if i=="pop":
##                    stackcount = stackcount-1
##                    print " "*stackcount, "pop", stackcount
##                if stackcount<0:
##                    dump=1
##                    print "STACK UNDERFLOW!"
##        if dump: stop
        return program

    def linearize(self, program = None, parsedText=None):
        #print "LINEARIZING", self
        #program = self.program = []
        if parsedText is None:
            parsedText = self.parsedText
        style = self.style1
        if program is None:
            program = []
        program.append( ("push",) )
        if style.spaceBefore:
            program.append( ("leading", style.spaceBefore+style.leading) )
        else:
            program.append( ("leading", style.leading) )
        program.append( ("nextLine", 0) )
        program = self.compileProgram(parsedText, program=program)
        program.append( ("pop",) )
        # go to old margin
        program.append( ("push",) )
        if style.spaceAfter:
            program.append( ("leading", style.spaceAfter) )
        else:
            program.append( ("leading", 0) )
        program.append( ("nextLine", 0) )
        program.append( ("pop",) )

    def compileComponent(self, parsedText, program):
        #program = self.program
        if isinstance(parsedText,str):
            # handle special characters here...
            # short cut
            if parsedText:
                stext = parsedText.strip()
                if not stext:
                    program.append(" ") # contract whitespace to single space
                else:
                    handleSpecialCharacters(self, parsedText, program)
        elif isinstance(parsedText,list):
            for e in parsedText:
                self.compileComponent(e, program)
        elif isinstance(parsedText,tuple):
            (tagname, attdict, content, extra) = parsedText
            if not attdict:
                attdict = {}
            compilername = "compile_"+tagname
            compiler = getattr(self, compilername, None)
            if compiler is not None:
                compiler(attdict, content, extra, program)
            else:
                # just pass the tag through
                if debug:
                    L = [ "<" + tagname ]
                    a = L.append
                    if not attdict: attdict = {}
                    for k, v in attdict.items():
                        a(" %s=%s" % (k,v))
                    if content:
                        a(">")
                        a(str(content))
                        a("</%s>" % tagname)
                    else:
                        a("/>")
                    t = ''.join(L)
                    handleSpecialCharacters(self, t, program)
                else:
                    raise ValueError("don't know how to handle tag " + repr(tagname))

    def shiftfont(self, program, face=None, bold=None, italic=None):
        oldface = self.face
        oldbold = self.bold
        olditalic = self.italic
        oldfontinfo = (oldface, oldbold, olditalic)
        if face is None: face = oldface
        if bold is None: bold = oldbold
        if italic is None: italic = olditalic
        self.face = face
        self.bold = bold
        self.italic = italic
        from reportlab.lib.fonts import tt2ps
        font = tt2ps(face,bold,italic)
        oldfont = tt2ps(oldface,oldbold,olditalic)
        if font!=oldfont:
            program.append( ("face", font ) )
        return oldfontinfo

    def compile_(self, attdict, content, extra, program):
        # "anonymous" tag: just do the content
        for e in content:
            self.compileComponent(e, program)
    #compile_para = compile_ # at least for now...

    def compile_pageNumber(self, attdict, content, extra, program):
        program.append(PageNumberObject())

    def compile_b(self, attdict, content, extra, program):
        (f,b,i) = self.shiftfont(program, bold=1)
        for e in content:
            self.compileComponent(e, program)
        self.shiftfont(program, bold=b)

    def compile_i(self, attdict, content, extra, program):
        (f,b,i) = self.shiftfont(program, italic=1)
        for e in content:
            self.compileComponent(e, program)
        self.shiftfont(program, italic=i)

    def compile_u(self, attdict, content, extra, program):
        # XXXX must eventually add things like alternative colors
        #program = self.program
        program.append( ('lineOperation', UNDERLINE) )
        for e in content:
            self.compileComponent(e, program)
        program.append( ('endLineOperation', UNDERLINE) )

    def compile_sub(self, attdict, content, extra, program):
        size = self.size
        self.size = newsize = size * 0.7
        rise = size*0.5
        #program = self.program
        program.append( ('size', newsize) )
        self.size = size
        program.append( ('rise', -rise) )
        for e in content:
            self.compileComponent(e, program)
        program.append( ('size', size) )
        program.append( ('rise', rise) )

    def compile_ul(self, attdict, content, extra, program, tagname="ul"):
        # by transformation
        #print "compile", tagname, attdict
        atts = attdict.copy()
        bulletmaker = bulletMaker(tagname, atts, self.context)
        # now do each element as a separate paragraph
        for e in content:
            if isinstance(e,str):
                if e.strip():
                    raise ValueError("don't expect CDATA between list elements")
            elif isinstance(e,tuple):
                (tagname, attdict1, content1, extra) = e
                if tagname!="li":
                    raise ValueError("don't expect %s inside list" % repr(tagname))
                newatts = atts.copy()
                if attdict1:
                    newatts.update(attdict1)
                bulletmaker.makeBullet(newatts)
                self.compile_para(newatts, content1, extra, program)

    def compile_ol(self, attdict, content, extra, program):
        return self.compile_ul(attdict, content, extra, program, tagname="ol")

    def compile_dl(self, attdict, content, extra, program):
        # by transformation
        #print "compile", tagname, attdict
        atts = attdict.copy()
        # by transformation
        #print "compile", tagname, attdict
        atts = attdict.copy()
        bulletmaker = bulletMaker("dl", atts, self.context)
        # now do each element as a separate paragraph
        contentcopy = list(content) # copy for destruction
        bullet = ""
        while contentcopy:
            e = contentcopy[0]
            del contentcopy[0]
            if isinstance(e,str):
                if e.strip():
                    raise ValueError("don't expect CDATA between list elements")
                elif not contentcopy:
                    break # done at ending whitespace
                else:
                    continue # ignore intermediate whitespace
            elif isinstance(e,tuple):
                (tagname, attdict1, content1, extra) = e
                if tagname!="dd" and tagname!="dt":
                    raise ValueError("don't expect %s here inside list, expect 'dd' or 'dt'" % \
                          repr(tagname))
                if tagname=="dt":
                    if bullet:
                        raise ValueError("dt will not be displayed unless followed by a dd: "+repr(bullet))
                    if content1:
                        self.compile_para(attdict1, content1, extra, program)
                        # raise ValueError, \
                        # "only simple strings supported in dd content currently: "+repr(content1)
                elif tagname=="dd":
                    newatts = atts.copy()
                    if attdict1:
                        newatts.update(attdict1)
                    bulletmaker.makeBullet(newatts, bl=bullet)
                    self.compile_para(newatts, content1, extra, program)
                    bullet = "" # don't use this bullet again
        if bullet:
            raise ValueError("dt will not be displayed unless followed by a dd"+repr(bullet))

    def compile_super(self, attdict, content, extra, program):
        size = self.size
        self.size = newsize = size * 0.7
        rise = size*0.5
        #program = self.program
        program.append( ('size', newsize) )
        program.append( ('rise', rise) )
        for e in content:
            self.compileComponent(e, program)
        program.append( ('size', size) )
        self.size = size
        program.append( ('rise', -rise) )

    def compile_font(self, attdict, content, extra, program):
        #program = self.program
        program.append( ("push",) ) # store current data
        if "face" in attdict:
            face = attdict["face"]
            from reportlab.lib.fonts import tt2ps
            try:
                font = tt2ps(face,self.bold,self.italic)
            except:
                font = face # better work!
            program.append( ("face", font ) )
        if "color" in attdict:
            colorname = attdict["color"]
            program.append( ("color", colorname) )
        if "size" in attdict:
            #size = float(attdict["size"]) # really should convert int, cm etc here!
            size = attdict["size"]
            program.append( ("size", size) )
        for e in content:
            self.compileComponent(e, program)
        program.append( ("pop",) ) # restore as before

    def compile_a(self, attdict, content, extra, program):
        url = attdict["href"]
        colorname = attdict.get("color", "blue")
        #program = self.program
        Link = HotLink(url)
        program.append( ("push",) ) # store current data
        program.append( ("color", colorname) )
        program.append( ('lineOperation', Link) )
        program.append( ('lineOperation', UNDERLINE) )
        for e in content:
            self.compileComponent(e, program)
        program.append( ('endLineOperation', UNDERLINE) )
        program.append( ('endLineOperation', Link) )
        program.append( ("pop",) ) # restore as before

    def compile_link(self, attdict, content, extra, program):
        dest = attdict["destination"]
        colorname = attdict.get("color", None)
        #program = self.program
        Link = InternalLink(dest)
        program.append( ("push",) ) # store current data
        if colorname:
            program.append( ("color", colorname) )
        program.append( ('lineOperation', Link) )
        program.append( ('lineOperation', UNDERLINE) )
        for e in content:
            self.compileComponent(e, program)
        program.append( ('endLineOperation', UNDERLINE) )
        program.append( ('endLineOperation', Link) )
        program.append( ("pop",) ) # restore as before

    def compile_setLink(self, attdict, content, extra, program):
        dest = attdict["destination"]
        colorname = attdict.get("color", "blue")
        #program = self.program
        Link = DefDestination(dest)
        program.append( ("push",) ) # store current data
        if colorname:
            program.append( ("color", colorname) )
        program.append( ('lineOperation', Link) )
        if colorname:
            program.append( ('lineOperation', UNDERLINE) )
        for e in content:
            self.compileComponent(e, program)
        if colorname:
            program.append( ('endLineOperation', UNDERLINE) )
        program.append( ('endLineOperation', Link) )
        program.append( ("pop",) ) # restore as before

    #def compile_p(self, attdict, content, extra, program):
    #    # have to be careful about base indent here!
    #    not finished

    def compile_bullet(self, attdict, content, extra, program):
        ### eventually should allow things like images and graphics in bullets too XXXX
        if len(content)!=1 or not isinstance(content[0],str):
            raise ValueError("content for bullet must be a single string")
        text = content[0]
        self.do_bullet(text, program)

    def do_bullet(self, text, program):
        style = self.style1
        #program = self.program
        indent = style.bulletIndent + self.baseindent
        font = style.bulletFontName
        size = style.bulletFontSize
        program.append( ("bullet", text, indent, font, size) )

    def compile_tt(self, attdict, content, extra, program):
        (f,b,i) = self.shiftfont(program, face="Courier")
        for e in content:
            self.compileComponent(e, program)
        self.shiftfont(program, face=f)

    def compile_greek(self, attdict, content, extra, program):
        self.compile_font({"face": "symbol"}, content, extra, program)

    def compile_evalString(self, attdict, content, extra, program):
        program.append( EvalStringObject(attdict, content, extra, self.context) )

    def compile_name(self, attdict, content, extra, program):
        program.append( NameObject(attdict, content, extra, self.context) )

    def compile_getName(self, attdict, content, extra, program):
        program.append( GetNameObject(attdict, content, extra, self.context) )

    def compile_seq(self, attdict, content, extra, program):
        program.append( SeqObject(attdict, content, extra, self.context) )

    def compile_seqReset(self, attdict, content, extra, program):
        program.append( SeqResetObject(attdict, content, extra, self.context) )

    def compile_seqDefault(self, attdict, content, extra, program):
        program.append( SeqDefaultObject(attdict, content, extra, self.context) )

    def compile_para(self, attdict, content, extra, program, stylename = "para.defaultStyle"):
        if attdict is None:
            attdict = {}
        context = self.context
        stylename = attdict.get("style", stylename)
        style = context[stylename]
        newstyle = SimpleStyle(name="rml2pdf internal embedded style", parent=style)
        newstyle.addAttributes(attdict)
        bulletText = attdict.get("bulletText", None)
        mystyle = self.style1
        thepara = Para(newstyle, content, context=context, bulletText=bulletText)
        # possible ref loop on context, break later
        # now compile it and add it to the program
        mybaseindent = self.baseindent
        self.baseindent = thepara.baseindent = mystyle.leftIndent + self.baseindent
        thepara.linearize(program=program)
        program.append( ("nextLine", 0) )
        self.baseindent = mybaseindent

class bulletMaker:
    def __init__(self, tagname, atts, context):
        self.tagname = tagname
        #print "context is", context
        style = "li.defaultStyle"
        self.style = style = atts.get("style", style)
        typ = {"ul": "disc", "ol": "1", "dl": None}[tagname]
        #print tagname, "bulletmaker type is", typ
        self.typ =typ = atts.get("type", typ)
        #print tagname, "bulletmaker type is", typ
        if "leftIndent" not in atts:
            # get the style so you can choose an indent length
            thestyle = context[style]
            from reportlab.pdfbase.pdfmetrics import stringWidth
            size = thestyle.fontSize
            indent = stringWidth("XXX", "Courier", size)
            atts["leftIndent"] = str(indent)
        self.count = 0
        self._first = 1

    def makeBullet(self, atts, bl=None):
        if not self._first:
            # forget space before for non-first elements
            atts["spaceBefore"] = "0"
        else:
            self._first = 0
        typ = self.typ
        tagname = self.tagname
        if bl is None:
            if tagname=="ul":
                if typ=="disc": bl = chr(109)
                elif typ=="circle": bl = chr(108)
                elif typ=="square": bl = chr(110)
                else:
                    raise ValueError("unordered list type %s not implemented" % repr(typ))
                if "bulletFontName" not in atts:
                    atts["bulletFontName"] = "ZapfDingbats"
            elif tagname=="ol":
                if 'value' in atts:
                    self.count = int(atts['value'])
                else:
                    self.count += 1
                if typ=="1": bl = str(self.count)
                elif typ=="a":
                    theord = ord("a")+self.count-1
                    bl = chr(theord)
                elif typ=="A":
                    theord = ord("A")+self.count-1
                    bl = chr(theord)
                else:
                    raise ValueError("ordered bullet type %s not implemented" % repr(typ))
            else:
                raise ValueError("bad tagname "+repr(tagname))
        if "bulletText" not in atts:
            atts["bulletText"] = bl
        if "style" not in atts:
            atts["style"] = self.style

class EvalStringObject:
    "this will only work if rml2pdf is present"

    tagname = "evalString"

    def __init__(self, attdict, content, extra, context):
        if not attdict:
            attdict = {}
        self.attdict = attdict
        self.content = content
        self.context = context
        self.extra = extra

    def getOp(self, tuple, engine):
        from rlextra.rml2pdf.rml2pdf import Controller
        #print "tuple", tuple
        op = self.op = Controller.processTuple(tuple, self.context, {})
        return op

    def width(self, engine):
        from reportlab.pdfbase.pdfmetrics import stringWidth
        content = self.content
        if not content:
            content = []
        tuple = (self.tagname, self.attdict, content, self.extra)
        op = self.op = self.getOp(tuple, engine)
        #print op.__class__
        #print op.pcontent
        #print self
        s = str(op)
        return stringWidth(s, engine.fontName, engine.fontSize)

    def execute(self, engine, textobject, canvas):
        textobject.textOut(str(self.op))

class SeqObject(EvalStringObject):

    def getOp(self, tuple, engine):
        from reportlab.lib.sequencer import getSequencer
        globalsequencer = getSequencer()
        attr = self.attdict
        #if it has a template, use that; otherwise try for id;
        #otherwise take default sequence
        if 'template' in attr:
            templ = attr['template']
            op = self.op = templ % globalsequencer
            return op
        elif 'id' in attr:
            id = attr['id']
        else:
            id = None
        op = self.op = globalsequencer.nextf(id)
        return op

class NameObject(EvalStringObject):
    tagname = "name"
    def execute(self, engine, textobject, canvas):
        pass # name doesn't produce any output

class SeqDefaultObject(NameObject):

    def getOp(self, tuple, engine):
        from reportlab.lib.sequencer import getSequencer
        globalsequencer = getSequencer()
        attr = self.attdict
        try:
            default = attr['id']
        except KeyError:
            default = None
        globalsequencer.setDefaultCounter(default)
        self.op = ""
        return ""

class SeqResetObject(NameObject):

    def getOp(self, tuple, engine):
        from reportlab.lib.sequencer import getSequencer
        globalsequencer = getSequencer()
        attr = self.attdict
        try:
            id = attr['id']
        except KeyError:
            id = None
        try:
            base = int(attr['base'])
        except:
            base=0
        globalsequencer.reset(id, base)
        self.op = ""
        return ""

class GetNameObject(EvalStringObject):
    tagname = "getName"

class PageNumberObject:

    def __init__(self, example="XXX"):
        self.example = example # XXX SHOULD ADD THE ABILITY TO PASS IN EXAMPLES

    def width(self, engine):
        from reportlab.pdfbase.pdfmetrics import stringWidth
        return stringWidth(self.example, engine.fontName, engine.fontSize)

    def execute(self, engine, textobject, canvas):
        n = canvas.getPageNumber()
        textobject.textOut(str(n))

### this should be moved into rml2pdf
def EmbedInRml2pdf():
    "make the para the default para implementation in rml2pdf"
    from rlextra.rml2pdf.rml2pdf import MapNode, Controller # may not need to use superclass?
    global paraMapper, theParaMapper, ulMapper

    class paraMapper(MapNode):
        #stylename = "para.defaultStyle"
        def translate(self, nodetuple, controller, context, overrides):
            (tagname, attdict, content, extra) = nodetuple
            stylename = tagname+".defaultStyle"
            stylename = attdict.get("style", stylename)
            style = context[stylename]
            mystyle = SimpleStyle(name="rml2pdf internal style", parent=style)
            mystyle.addAttributes(attdict)
            bulletText = attdict.get("bulletText", None)
            # can we use the fast implementation?
            result = None
            if not bulletText and len(content)==1:
                text = content[0]
                if isinstance(text,str) and "&" not in text:
                    result = FastPara(mystyle, text)
            if result is None:
                result = Para(mystyle, content, context=context, bulletText=bulletText) # possible ref loop on context, break later
            return result

    theParaMapper = paraMapper()

    class ulMapper(MapNode):
        # wrap in a default para and let the para do it
        def translate(self, nodetuple, controller, context, overrides):
            thepara = ("para", {}, [nodetuple], None)
            return theParaMapper.translate(thepara, controller, context, overrides)

    # override rml2pdf interpreters (should be moved to rml2pdf)
    theListMapper = ulMapper()
    Controller["ul"] = theListMapper
    Controller["ol"] = theListMapper
    Controller["dl"] = theListMapper
    Controller["para"] = theParaMapper
    Controller["h1"] = theParaMapper
    Controller["h2"] = theParaMapper
    Controller["h3"] = theParaMapper
    Controller["title"] = theParaMapper

def handleSpecialCharacters(engine, text, program=None):
    from reportlab.platypus.paraparser import greeks
    from string import whitespace
    standard={'lt':'<', 'gt':'>', 'amp':'&'}
    # add space prefix if space here
    if text[0:1] in whitespace:
        program.append(" ")
    #print "handling", repr(text)
    # shortcut
    if 0 and "&" not in text:
        result = []
        for x in text.split():
            result.append(x+" ")
        if result:
            last = result[-1]
            if text[-1:] not in whitespace:
                result[-1] = last.strip()
        program.extend(result)
        return program
    if program is None:
        program = []
    amptext = text.split("&")
    first = 1
    lastfrag = amptext[-1]
    for fragment in amptext:
        if not first:
            # check for special chars
            semi = fragment.find(";")
            if semi>0:
                name = fragment[:semi]
                if name[0]=='#':
                    try:
                        if name[1] == 'x':
                            n = int(name[2:], 16)
                        else:
                            n = int(name[1:])
                    except ValueError:
                        n = -1
                    if n>=0:
                        fragment = chr(n)+fragment[semi+1:]
                    else:
                        fragment = "&"+fragment
                elif name in standard:
                    s = standard[name]
                    if isinstance(fragment,bytes):
                        s = s.decode('utf8')
                    fragment = s+fragment[semi+1:]
                elif name in greeks:
                    s = greeks[name]
                    if isinstance(fragment,bytes):
                        s = s.decode('utf8')
                    fragment = s+fragment[semi+1:]
                else:
                    # add back the &
                    fragment = "&"+fragment
            else:
                # add back the &
                fragment = "&"+fragment
        # add white separated components of fragment followed by space
        sfragment = fragment.split()
        for w in sfragment[:-1]:
            program.append(w+" ")
        # does the last one need a space?
        if sfragment and fragment:
            # reader 3 used to go nuts if you don't special case the last frag, but it's fixed?
            if fragment[-1] in whitespace: # or fragment==lastfrag:
                program.append( sfragment[-1]+" " )
            else:
                last = sfragment[-1].strip()
                if last:
                    #print "last is", repr(last)
                    program.append( last )
        first = 0
    #print "HANDLED", program
    return program

def Paragraph(text, style, bulletText=None, frags=None, context=None):
    """ Paragraph(text, style, bulletText=None)
    intended to be like a platypus Paragraph but better.
    """
    # if there is no & or < in text then use the fast paragraph
    if "&" not in text and "<" not in text:
        return FastPara(style, simpletext=text)
    else:
        # use the fully featured one.
        from reportlab.lib import rparsexml
        parsedpara = rparsexml.parsexmlSimple(text,entityReplacer=None)
        return Para(style, parsedText=parsedpara, bulletText=bulletText, state=None, context=context)

class UnderLineHandler:
    def __init__(self, color=None):
        self.color = color
    def start_at(self, x,y, para, canvas, textobject):
        self.xStart = x
        self.yStart = y
    def end_at(self, x, y, para, canvas, textobject):
        offset = para.fontSize/8.0
        canvas.saveState()
        color = self.color
        if self.color is None:
            color = para.fontColor
        canvas.setStrokeColor(color)
        canvas.line(self.xStart, self.yStart-offset, x,y-offset)
        canvas.restoreState()

UNDERLINE = UnderLineHandler()

class HotLink(UnderLineHandler):

    def __init__(self, url):
        self.url = url

    def end_at(self, x, y, para, canvas, textobject):
        fontsize = para.fontSize
        rect = [self.xStart, self.yStart, x,y+fontsize]
        if debug:
            print("LINKING RECTANGLE", rect)
            #canvas.rect(self.xStart, self.yStart, x-self.xStart,y+fontsize-self.yStart, stroke=1)
        self.link(rect, canvas)

    def link(self, rect, canvas):
        canvas.linkURL(self.url, rect, relative=1)

class InternalLink(HotLink):

    def link(self, rect, canvas):
        destinationname = self.url
        contents = ""
        canvas.linkRect(contents, destinationname, rect, Border="[0 0 0]")

class DefDestination(HotLink):

    defined = 0

    def link(self, rect, canvas):
        destinationname = self.url
        if not self.defined:
            [x, y, x1, y1] = rect
            canvas.bookmarkHorizontal(destinationname, x, y1) # use the upper y
            self.defined = 1

def splitspace(text):
    # split on spacing but include spaces at element ends
    stext = text.split()
    result = []
    for e in stext:
        result.append(e+" ")
    return result


testparagraph = """
This is Text.
<b>This is bold text.</b>
This is Text.
<i>This is italic text.</i>

<ul>
    <li> this is an element at 1
more text and even more text &amp; on and on and so forth
more text and even more text and on &amp; on and so forth
more text and even more text and on and on &amp; so forth
more text and even more text and on and on and so forth
more text and even more text and on and on and so forth --&gt;
more text <tt>monospaced</tt> and back to normal

    <ul>
        <li> this is an element at 2

more text and even more text and on and on and so forth
more text and even more text and on and on and so forth

        <ul>
            <li> this is an element at 3

more text and even more text and on and on and so forth


                <dl bulletFontName="Helvetica-BoldOblique" spaceBefore="10" spaceAfter="10">
                <dt>frogs</dt> <dd>Little green slimy things. Delicious with <b>garlic</b></dd>
                <dt>kittens</dt> <dd>cute, furry, not edible</dd>
                <dt>bunnies</dt> <dd>cute, furry,. Delicious with <b>garlic</b></dd>
                </dl>

more text and even more text and on and on and so forth

            <ul>
                <li> this is an element at  4
more text and even more text and on and on and so forth
                </li>
                <li> this is an element at4
more text and even more text and on and on and so forth
                </li>
            </ul>
more text and even more text and on and on and so forth
more text and even more text and on and on and so forth

            </li>
        </ul>
more text and even more text and on and on and so forth
more text and even more text and on and on and so forth
        </li>
    </ul>
<u><b>UNDERLINED</b> more text and even more text and on and on and so forth
more text and even more text and on and on and so forth</u>

<ol type="a">
    <li value="3">first element of the alpha list

     <ul type="square">
        <li>first element of the square unnumberred list</li>

        <li>second element of the unnumberred list</li>

        <li>third element of the unnumberred list
        third element of the unnumberred list
        third element of the unnumberred list
        third element of the unnumberred list
        third element of the unnumberred list
        third element of the unnumberred list
        third element of the unnumberred list
        </li>

        <li>fourth element of the unnumberred list</li>

      </ul>

    </li>

    <li>second element of the alpha list</li>

    <li>third element of the alpha list
    third element of the unnumberred list &amp;#33; --> &#33;
    third element of the unnumberred list &amp;#8704; --> &#8704;
    third element of the unnumberred list &amp;exist; --> &exist;
    third element of the unnumberred list
    third element of the unnumberred list
    third element of the unnumberred list
    </li>

    <li>fourth element of the alpha list</li>

  </ol>


    </li>
</ul>
"""

testparagraph1 = """
<a href="http://www.reportlab.com">goto www.reportlab.com</a>.


<para alignment="justify">
<font color="red" size="15">R</font>ed letter. thisisareallylongword andsoisthis andthisislonger
justified text paragraph example with a pound sign \xc2\xa3
justified text paragraph example
justified text paragraph example
</para>

<para alignment="center">
<font color="green" size="15">G</font>reen letter.
centered text paragraph example
centered text paragraph example
centered text paragraph example
</para>
<para alignment="right">
<font color="blue" size="15">B</font>lue letter.
right justified text paragraph example
right justified text paragraph example
right justified text paragraph example
</para>
<para alignment="left">
<font color="yellow" size="15">Y</font>ellow letter.
left justified text paragraph example
left justified text paragraph example
left justified text paragraph example
</para>

"""

def test2(canv,testpara):
    #print test_program; return
    from reportlab.lib.units import inch
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib import rparsexml
    parsedpara = rparsexml.parsexmlSimple(testpara,entityReplacer=None)
    S = ParagraphStyle("Normal", None)
    P = Para(S, parsedpara)
    (w, h) = P.wrap(5*inch, 10*inch)
    print("wrapped as", (h,w))
    canv.saveState()
    canv.translate(1*inch, 1*inch)
    canv.rect(0,0,5*inch,10*inch, fill=0, stroke=1)
    P.canv = canv
    canv.saveState()
    P.draw()
    canv.restoreState()
    canv.setStrokeColorRGB(1, 0, 0)
    #canv.translate(0, 3*inch)
    canv.rect(0,0,w,h, fill=0, stroke=1)
    canv.restoreState()
    canv.showPage()

testlink = HotLink("http://www.reportlab.com")

test_program = [
    ('push',),
    ('indent', 100),
                    ('rightIndent', 200),
                    ('bullet', 'very long bullet', 50, 'Courier', 14),
                    ('align', TA_CENTER),
                    ('face', _baseFontName),
                    ('size', 12),
                    ('leading', 14),
                    ] + splitspace("This is the first segment of the first paragraph.") + [
                    ('lineOperation', testlink),
                    ]+splitspace("HOTLINK This is the first segment of the first paragraph. This is the first segment of the first paragraph. This is the first segment of the first paragraph. This is the first segment of the first paragraph. ") + [
                    ('endLineOperation', testlink),
                    ('nextLine', 0),
                    ('align', TA_LEFT),
                    ('bullet', 'Bullet', 10, 'Courier', 8),
                    ('face', _baseFontName),
                    ('size', 12),
                    ('leading', 14),
                    ] + splitspace("This is the SECOND!!! segment of the first paragraph. This is the first segment of the first paragraph. This is the first segment of the first paragraph. This is the first segment of the first paragraph. This is the first segment of the first paragraph. ") + [
                    ('nextLine', 0),
                    ('align', TA_JUSTIFY),
                    ('bullet', 'Bullet not quite as long this time', 50, 'Courier', 8),
                    ('face', "Helvetica-Oblique"),
                    ('size', 12),
                    ('leading', 14),
                    ('push',),
                    ('color', 'red'),
                    ] + splitspace("This is the THIRD!!! segment of the first paragraph."
                                     ) + [
                    ('lineOperation', UNDERLINE),
                    ] + splitspace("This is the first segment of the first paragraph. This is the first segment of the first paragraph. This is the first segment of the first paragraph. This is the first segment of the first paragraph. ") + [
                    ('endLineOperation', UNDERLINE),
                    ('rise', 5),
                    "raised ", "text ",
                    ('rise', -10),
                    "lowered ", "text ",
                    ('rise', 5),
                    "normal ", "text ",
                    ('pop',),
                    ('indent', 100),
                    ('rightIndent', 50),
                    ('nextLine', 0),
                    ('align', TA_RIGHT),
                    ('bullet', 'O', 50, 'Courier', 14),
                    ('face', "Helvetica"),
                    ('size', 12),
                    ('leading', 14),
                    ] + splitspace("And this is the remainder of the paragraph indented further. a a a a a a a a And this is the remainder of the paragraph indented further. a a a a a a a a And this is the remainder of the paragraph indented further. a a a a a a a a And this is the remainder of the paragraph indented further. a a a a a a a a And this is the remainder of the paragraph indented further. a a a a a a a a And this is the remainder of the paragraph indented further. a a a a a a a a And this is the remainder of the paragraph indented further. a a a a a a a a ") + [
            ('pop',),
            ('nextLine', 0),]

def test():
    from pprint import pprint
    #print test_program; return
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import inch
    fn = "paratest0.pdf"
    c = canvas.Canvas(fn)
    test2(c,testparagraph)
    test2(c,testparagraph1)
    if 1:
        remainder = test_program + test_program + test_program
        laststate = {}
        while remainder:
            print("NEW PAGE")
            c.translate(inch, 8*inch)
            t = c.beginText()
            t.setTextOrigin(0,0)
            p = paragraphEngine()
            p.resetState(laststate)
            p.x = 0
            p.y = 0
            maxwidth = 7*inch
            maxheight = 500
            (formattedprogram, remainder, laststate, height) = p.format(maxwidth, maxheight, remainder)
            if debug:
                pprint( formattedprogram )#; return
            laststate = p.runOpCodes(formattedprogram, c, t)
            c.drawText(t)
            c.showPage()
            print("="*30, "x=", laststate["x"], "y=", laststate["y"])
    c.save()
    print(fn)

if __name__=="__main__":
    test()

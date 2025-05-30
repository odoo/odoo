"""Very simple and fast XML parser, used for intra-paragraph text.

Devised by Aaron Watters in the bad old days before Python had fast
parsers available.  Constructs the lightest possible in-memory
representation; parses most files we have seen in pure python very
quickly.

The output structure is the same as the one produced by pyRXP,
our validating C-based parser, which was written later.  It will
use pyRXP if available.

This is used to parse intra-paragraph markup.

Example parse::

    <this type="xml">text <b>in</b> xml</this>

    ( "this",
      {"type": "xml"},
      [ "text ",
        ("b", None, ["in"], None),
        " xml"
        ]
       None )

    { 0: "this"
      "type": "xml"
      1: ["text ",
          {0: "b", 1:["in"]},
          " xml"]
    }

Ie, xml tag translates to a tuple:
 (name, dictofattributes, contentlist, miscellaneousinfo)

where miscellaneousinfo can be anything, (but defaults to None)
(with the intention of adding, eg, line number information)

special cases: name of "" means "top level, no containing tag".
Top level parse always looks like this::

    ("", list, None, None)

 contained text of None means <simple_tag/>

In order to support stuff like::

    <this></this><one></one>

AT THE MOMENT &amp; ETCETERA ARE IGNORED. THEY MUST BE PROCESSED
IN A POST-PROCESSING STEP.

PROLOGUES ARE NOT UNDERSTOOD.  OTHER STUFF IS PROBABLY MISSING.
"""

RequirePyRXP = 0        # set this to 1 to disable the nonvalidating fallback parser.

try:
    #raise ImportError, "dummy error"
    simpleparse = 0
    import pyRXPU
    def warnCB(s):
        print(s)
    pyRXP_parser = pyRXPU.Parser(
                        ErrorOnValidityErrors=1,
                        NoNoDTDWarning=1,
                        ExpandCharacterEntities=1,
                        ExpandGeneralEntities=1,
                        warnCB = warnCB,
                        srcName='string input',
                        ReturnUTF8 = 0,
                        )
    def parsexml(xmlText, oneOutermostTag=0,eoCB=None,entityReplacer=None,parseOpts={}):
        pyRXP_parser.eoCB = eoCB
        p = pyRXP_parser.parse(xmlText,**parseOpts)
        return oneOutermostTag and p or ('',None,[p],None)
except ImportError:
    simpleparse = 1

class smartDecode:
    @staticmethod
    def __call__(s):
        print('initial')
        import chardet
        def __call__(s):
            if isinstance(s,str): return s
            cdd = chardet.detect(s)
            print('final')
            return s.decode(cdd["encoding"])
        smartDecode.__class__.__call__ = staticmethod(__call__)
        return  __call__(s)
smartDecode = smartDecode()

NONAME = ""
NAMEKEY = 0
CONTENTSKEY = 1
CDATAMARKER = "<![CDATA["
LENCDATAMARKER = len(CDATAMARKER)
CDATAENDMARKER = "]]>"
replacelist = [("&lt;", "<"), ("&gt;", ">"), ("&amp;", "&")] # amp must be last
#replacelist = []
def unEscapeContentList(contentList):
    result = []
    for e in contentList:
        if "&" in e:
            for (old, new) in replacelist:
                e = e.replace(old, new)
        result.append(e)
    return result

def parsexmlSimple(xmltext, oneOutermostTag=0,eoCB=None,entityReplacer=unEscapeContentList):
    """official interface: discard unused cursor info"""
    if RequirePyRXP:
        raise ImportError("pyRXP not found, fallback parser disabled")
    (result, cursor) = parsexml0(xmltext,entityReplacer=entityReplacer)
    if oneOutermostTag:
        return result[2][0]
    else:
        return result

if simpleparse:
    parsexml = parsexmlSimple

def parseFile(filename):
    raw = open(filename, 'r').read()
    return parsexml(raw)

verbose = 0

def skip_prologue(text, cursor):
    """skip any prologue found after cursor, return index of rest of text"""
    ### NOT AT ALL COMPLETE!!! definitely can be confused!!!
    prologue_elements = ("!DOCTYPE", "?xml", "!--")
    done = None
    while done is None:
        #print "trying to skip:", repr(text[cursor:cursor+20])
        openbracket = text.find("<", cursor)
        if openbracket<0: break
        past = openbracket+1
        found = None
        for e in prologue_elements:
            le = len(e)
            if text[past:past+le]==e:
                found = 1
                cursor = text.find(">", past)
                if cursor<0:
                    raise ValueError("can't close prologue %r" % e)
                cursor = cursor+1
        if found is None:
            done=1
    #print "done skipping"
    return cursor

def parsexml0(xmltext, startingat=0, toplevel=1,
        # snarf in some globals
        entityReplacer=unEscapeContentList,
        #len=len, None=None
        #LENCDATAMARKER=LENCDATAMARKER, CDATAMARKER=CDATAMARKER
        ):
    """simple recursive descent xml parser...
       return (dictionary, endcharacter)
       special case: comment returns (None, endcharacter)"""
    xmltext = smartDecode(xmltext)
    #print "parsexml0", repr(xmltext[startingat: startingat+10])
    # DEFAULTS
    NameString = NONAME
    ContentList = AttDict = ExtraStuff = None
    if toplevel is not None:
        #if verbose: print "at top level"
        #if startingat!=0:
        #    raise ValueError, "have to start at 0 for top level!"
        xmltext = xmltext.strip()
    cursor = startingat
    #look for interesting starting points
    firstbracket = xmltext.find("<", cursor)
    afterbracket2char = xmltext[firstbracket+1:firstbracket+3]
    #print "a", repr(afterbracket2char)
    #firstampersand = xmltext.find("&", cursor)
    #if firstampersand>0 and firstampersand<firstbracket:
    #    raise ValueError, "I don't handle ampersands yet!!!"
    docontents = 1
    if firstbracket<0:
            # no tags
            #if verbose: print "no tags"
            if toplevel is not None:
                #D = {NAMEKEY: NONAME, CONTENTSKEY: [xmltext[cursor:]]}
                ContentList = [xmltext[cursor:]]
                if entityReplacer: ContentList = entityReplacer(ContentList)
                return (NameString, AttDict, ContentList, ExtraStuff), len(xmltext)
            else:
                raise ValueError("no tags at non-toplevel %s" % repr(xmltext[cursor:cursor+20]))
    #D = {}
    L = []
    # look for start tag
    # NEED to force always outer level is unnamed!!!
    #if toplevel and firstbracket>0:
    #afterbracket2char = xmltext[firstbracket:firstbracket+2]
    if toplevel is not None:
            #print "toplevel with no outer tag"
            NameString = name = NONAME
            cursor = skip_prologue(xmltext, cursor)
            #break
    elif firstbracket<0:
            raise ValueError("non top level entry should be at start tag: %s" % repr(xmltext[:10]))
    # special case: CDATA
    elif afterbracket2char=="![" and xmltext[firstbracket:firstbracket+9]=="<![CDATA[":
            #print "in CDATA", cursor
            # skip straight to the close marker
            startcdata = firstbracket+9
            endcdata = xmltext.find(CDATAENDMARKER, startcdata)
            if endcdata<0:
                raise ValueError("unclosed CDATA %s" % repr(xmltext[cursor:cursor+20]))
            NameString = CDATAMARKER
            ContentList = [xmltext[startcdata: endcdata]]
            cursor = endcdata+len(CDATAENDMARKER)
            docontents = None
    # special case COMMENT
    elif afterbracket2char=="!-" and xmltext[firstbracket:firstbracket+4]=="<!--":
            #print "in COMMENT"
            endcommentdashes = xmltext.find("--", firstbracket+4)
            if endcommentdashes<firstbracket:
                raise ValueError("unterminated comment %s" % repr(xmltext[cursor:cursor+20]))
            endcomment = endcommentdashes+2
            if xmltext[endcomment]!=">":
                raise ValueError("invalid comment: contains double dashes %s" % repr(xmltext[cursor:cursor+20]))
            return (None, endcomment+1) # shortcut exit
    else:
            # get the rest of the tag
            #if verbose: print "parsing start tag"
            # make sure the tag isn't in doublequote pairs
            closebracket = xmltext.find(">", firstbracket)
            noclose = closebracket<0
            startsearch = closebracket+1
            pastfirstbracket = firstbracket+1
            tagcontent = xmltext[pastfirstbracket:closebracket]
            # shortcut, no equal means nothing but name in the tag content
            if '=' not in tagcontent:
                if tagcontent[-1]=="/":
                    # simple case
                    #print "simple case", tagcontent
                    tagcontent = tagcontent[:-1]
                    docontents = None
                name = tagcontent.strip()
                NameString = name
                cursor = startsearch
            else:
                if '"' in tagcontent:
                    # check double quotes
                    stop = None
                    # not inside double quotes! (the split should have odd length)
                    if noclose or len((tagcontent+".").split('"'))% 2:
                        stop=1
                    while stop is None:
                        closebracket = xmltext.find(">", startsearch)
                        startsearch = closebracket+1
                        noclose = closebracket<0
                        tagcontent = xmltext[pastfirstbracket:closebracket]
                        # not inside double quotes! (the split should have odd length)
                        if noclose or len((tagcontent+".").split('"'))% 2:
                            stop=1
                if noclose:
                    raise ValueError("unclosed start tag %s" % repr(xmltext[firstbracket:firstbracket+20]))
                cursor = startsearch
                #cursor = closebracket+1
                # handle simple tag /> syntax
                if xmltext[closebracket-1]=="/":
                    #if verbose: print "it's a simple tag"
                    closebracket = closebracket-1
                    tagcontent = tagcontent[:-1]
                    docontents = None
                #tagcontent = xmltext[firstbracket+1:closebracket]
                tagcontent = tagcontent.strip()
                taglist = tagcontent.split("=")
                #if not taglist:
                #    raise ValueError, "tag with no name %s" % repr(xmltext[firstbracket:firstbracket+20])
                taglist0 = taglist[0]
                taglist0list = taglist0.split()
                #if len(taglist0list)>2:
                #    raise ValueError, "bad tag head %s" % repr(taglist0)
                name = taglist0list[0]
                #print "tag name is", name
                NameString = name
                # now parse the attributes
                attributename = taglist0list[-1]
                # put a fake att name at end of last taglist entry for consistent parsing
                taglist[-1] = taglist[-1]+" f"
                AttDict = D = {}
                taglistindex = 1
                lasttaglistindex = len(taglist)
                #for attentry in taglist[1:]:
                while taglistindex<lasttaglistindex:
                    #print "looking for attribute named", attributename
                    attentry = taglist[taglistindex]
                    taglistindex = taglistindex+1
                    attentry = attentry.strip()
                    if attentry[0]!='"':
                        raise ValueError("attribute value must start with double quotes" + repr(attentry))
                    while '"' not in attentry[1:]:
                        # must have an = inside the attribute value...
                        if taglistindex>lasttaglistindex:
                            raise ValueError("unclosed value " + repr(attentry))
                        nextattentry = taglist[taglistindex]
                        taglistindex = taglistindex+1
                        attentry = "%s=%s" % (attentry, nextattentry)
                    attentry = attentry.strip() # only needed for while loop...
                    attlist = attentry.split()
                    nextattname = attlist[-1]
                    attvalue = attentry[:-len(nextattname)]
                    attvalue = attvalue.strip()
                    try:
                        first = attvalue[0]; last=attvalue[-1]
                    except:
                        raise ValueError("attvalue,attentry,attlist="+repr((attvalue, attentry,attlist)))
                    if first==last=='"' or first==last=="'":
                        attvalue = attvalue[1:-1]
                    #print attributename, "=", attvalue
                    D[attributename] = attvalue
                    attributename = nextattname
    # pass over other tags and content looking for end tag
    if docontents is not None:
        #print "now looking for end tag"
        ContentList = L
    while docontents is not None:
            nextopenbracket = xmltext.find("<", cursor)
            if nextopenbracket<cursor:
                #if verbose: print "no next open bracket found"
                if name==NONAME:
                    #print "no more tags for noname", repr(xmltext[cursor:cursor+10])
                    docontents=None # done
                    remainder = xmltext[cursor:]
                    cursor = len(xmltext)
                    if remainder:
                        L.append(remainder)
                else:
                    raise ValueError("no close bracket for %s found after %s" % (name,repr(xmltext[cursor: cursor+20])))
            # is it a close bracket?
            elif xmltext[nextopenbracket+1]=="/":
                #print "found close bracket", repr(xmltext[nextopenbracket:nextopenbracket+20])
                nextclosebracket = xmltext.find(">", nextopenbracket)
                if nextclosebracket<nextopenbracket:
                    raise ValueError("unclosed close tag %s" % repr(xmltext[nextopenbracket: nextopenbracket+20]))
                closetagcontents = xmltext[nextopenbracket+2: nextclosebracket]
                closetaglist = closetagcontents.split()
                #if len(closetaglist)!=1:
                    #print closetagcontents
                    #raise ValueError, "bad close tag format %s" % repr(xmltext[nextopenbracket: nextopenbracket+20])
                # name should match
                closename = closetaglist[0]
                #if verbose: print "closetag name is", closename
                if name!=closename:
                    prefix = xmltext[:cursor]
                    endlinenum = len(prefix.split("\n"))
                    prefix = xmltext[:startingat]
                    linenum = len(prefix.split("\n"))
                    raise ValueError("at lines %s...%s close tag name doesn't match %s...%s %s" %(
                       linenum, endlinenum, repr(name), repr(closename), repr(xmltext[cursor: cursor+100])))
                remainder = xmltext[cursor:nextopenbracket]
                if remainder:
                    #if verbose: print "remainder", repr(remainder)
                    L.append(remainder)
                cursor = nextclosebracket+1
                #print "for", name, "found close tag"
                docontents = None # done
            # otherwise we are looking at a new tag, recursively parse it...
            # first record any intervening content
            else:
                remainder = xmltext[cursor:nextopenbracket]
                if remainder:
                    L.append(remainder)
                #if verbose:
                #    #print "skipping", repr(remainder)
                #    #print "--- recursively parsing starting at", xmltext[nextopenbracket:nextopenbracket+20]
                (parsetree, cursor) = parsexml0(xmltext, startingat=nextopenbracket, toplevel=None, entityReplacer=entityReplacer)
                if parsetree:
                    L.append(parsetree)
        # maybe should check for trailing garbage?
        # toplevel:
        #    remainder = xmltext[cursor:].strip()
        #    if remainder:
        #        raise ValueError, "trailing garbage at top level %s" % repr(remainder[:20])
    if ContentList:
        if entityReplacer: ContentList = entityReplacer(ContentList)
    t = (NameString, AttDict, ContentList, ExtraStuff)
    return (t, cursor)

def pprettyprint(parsedxml):
    """pretty printer mainly for testing"""
    if isinstance(parsedxml,(str,bytes)):
        return parsedxml
    (name, attdict, textlist, extra) = parsedxml
    if not attdict: attdict={}
    attlist = []
    for k in attdict.keys():
        v = attdict[k]
        attlist.append("%s=%s" % (k, repr(v)))
    attributes = " ".join(attlist)
    if not name and attributes:
        raise ValueError("name missing with attributes???")
    if textlist is not None:
        # with content
        textlistpprint = list(map(pprettyprint, textlist))
        textpprint = "\n".join(textlistpprint)
        if not name:
            return textpprint # no outer tag
        # indent it
        nllist = textpprint.split("\n")
        textpprint = "   "+ ("\n   ".join(nllist))
        return "<%s %s>\n%s\n</%s>" % (name, attributes, textpprint, name)
    # otherwise must be a simple tag
    return "<%s %s/>" % (name, attributes)

def testparse(s,dump=0):
    from time import time
    from pprint import pprint
    now = time()
    breakpoint()
    D = parsexmlSimple(s,oneOutermostTag=1)
    print("DONE", time()-now)
    if dump&4:
        pprint(D)
    #pprint(D)
    if dump&1:
        print("============== reformatting")
        p = pprettyprint(D)
        print(p)

def test(dump=0):
    testparse("""<this type="xml">text &lt;&gt;<b>in</b> <funnytag foo="bar"/> xml</this>
                 <!-- comment -->
                 <![CDATA[
                 <this type="xml">text <b>in</b> xml</this> ]]>
                 <tag with="<brackets in values>">just testing brackets feature</tag>
                 """,dump=dump)

if __name__=="__main__":
    test(dump=1)
    import sys, os
    from time import time
    import reportlab
    now = time()
    seen = 0
    for f in sys.argv[1:]:
        if not os.path.isfile(f):
            print("!!!!! no file at {f!r}")
        else:
            with open(f) as _f:
                t = _f.read()
            print(f"parsing {f!r} |t|={len(t)}")
            testparse(t,dump=1)
            seen += 1
    if seen:
        print(f"timed at {time()-now:.2f} secs.")

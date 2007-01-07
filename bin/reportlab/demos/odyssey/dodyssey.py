#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/demos/odyssey/dodyssey.py
__version__=''' $Id: dodyssey.py 2856 2006-05-11 09:48:13Z rgbecker $ '''
__doc__=''

#REPORTLAB_TEST_SCRIPT
import sys, copy, string, os
from reportlab.platypus import *
_NEW_PARA=os.environ.get('NEW_PARA','0')[0] in ('y','Y','1')
_REDCAP=int(os.environ.get('REDCAP','0'))
_CALLBACK=os.environ.get('CALLBACK','0')[0] in ('y','Y','1')
if _NEW_PARA:
    def Paragraph(s,style):
        from rlextra.radxml.para import Paragraph as PPPP
        return PPPP(s,style)

from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER, TA_JUSTIFY

import reportlab.rl_config
reportlab.rl_config.invariant = 1

styles = getSampleStyleSheet()

Title = "The Odyssey"
Author = "Homer"

def myTitlePage(canvas, doc):
    canvas.saveState()
    canvas.restoreState()

def myLaterPages(canvas, doc):
    canvas.saveState()
    canvas.setFont('Times-Roman',9)
    canvas.drawString(inch, 0.75 * inch, "Page %d" % doc.page)
    canvas.restoreState()

def go():
    def myCanvasMaker(fn,**kw):
        from reportlab.pdfgen.canvas import Canvas
        canv = apply(Canvas,(fn,),kw)
        # attach our callback to the canvas
        canv.myOnDrawCB = myOnDrawCB
        return canv

    doc = BaseDocTemplate('dodyssey.pdf',showBoundary=0)

    #normal frame as for SimpleFlowDocument
    frameT = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='normal')

    #Two Columns
    frame1 = Frame(doc.leftMargin, doc.bottomMargin, doc.width/2-6, doc.height, id='col1')
    frame2 = Frame(doc.leftMargin+doc.width/2+6, doc.bottomMargin, doc.width/2-6,
                        doc.height, id='col2')
    doc.addPageTemplates([PageTemplate(id='First',frames=frameT, onPage=myTitlePage),
                        PageTemplate(id='OneCol',frames=frameT, onPage=myLaterPages),
                        PageTemplate(id='TwoCol',frames=[frame1,frame2], onPage=myLaterPages),
                        ])
    doc.build(Elements,canvasmaker=myCanvasMaker)

Elements = []

ChapterStyle = copy.deepcopy(styles["Heading1"])
ChapterStyle.alignment = TA_CENTER
ChapterStyle.fontsize = 14
InitialStyle = copy.deepcopy(ChapterStyle)
InitialStyle.fontsize = 16
InitialStyle.leading = 20
PreStyle = styles["Code"]

def newPage():
    Elements.append(PageBreak())

chNum = 0
def myOnDrawCB(canv,kind,label):
    print 'myOnDrawCB(%s)'%kind, 'Page number=', canv.getPageNumber(), 'label value=', label

def chapter(txt, style=ChapterStyle):
    global chNum
    Elements.append(NextPageTemplate('OneCol'))
    newPage()
    chNum = chNum + 1
    if _NEW_PARA or not _CALLBACK:
        Elements.append(Paragraph(('chap %d'%chNum)+txt, style))
    else:
        Elements.append(Paragraph(('foo<onDraw name="myOnDrawCB" label="chap %d"/> '%chNum)+txt, style))
    Elements.append(Spacer(0.2*inch, 0.3*inch))
    if useTwoCol:
        Elements.append(NextPageTemplate('TwoCol'))

def fTitle(txt,style=InitialStyle):
    Elements.append(Paragraph(txt, style))

ParaStyle = copy.deepcopy(styles["Normal"])
ParaStyle.spaceBefore = 0.1*inch
if 'right' in sys.argv:
    ParaStyle.alignment = TA_RIGHT
elif 'left' in sys.argv:
    ParaStyle.alignment = TA_LEFT
elif 'justify' in sys.argv:
    ParaStyle.alignment = TA_JUSTIFY
elif 'center' in sys.argv or 'centre' in sys.argv:
    ParaStyle.alignment = TA_CENTER
else:
    ParaStyle.alignment = TA_JUSTIFY

useTwoCol = 'notwocol' not in sys.argv

def spacer(inches):
    Elements.append(Spacer(0.1*inch, inches*inch))

def p(txt, style=ParaStyle):
    if _REDCAP:
        fs, fe = '<font color="red" size="+2">', '</font>'
        n = len(txt)
        for i in xrange(n):
            if 'a'<=txt[i]<='z' or 'A'<=txt[i]<='Z':
                txt = (txt[:i]+(fs+txt[i]+fe))+txt[i+1:]
                break
        if _REDCAP>=2 and n>20:
            j = i+len(fs)+len(fe)+1+int((n-1)/2)
            while not ('a'<=txt[j]<='z' or 'A'<=txt[j]<='Z'): j += 1
            txt = (txt[:j]+('<b><i><font size="+2" color="blue">'+txt[j]+'</font></i></b>'))+txt[j+1:]

        if _REDCAP==3 and n>20:
            n = len(txt)
            fs = '<font color="green" size="+1">'
            for i in xrange(n-1,-1,-1):
                if 'a'<=txt[i]<='z' or 'A'<=txt[i]<='Z':
                    txt = txt[:i]+((fs+txt[i]+fe)+txt[i+1:])
                    break

    Elements.append(Paragraph(txt, style))

firstPre = 1
def pre(txt, style=PreStyle):
    global firstPre
    if firstPre:
        Elements.append(NextPageTemplate('OneCol'))
        newPage()
        firstPre = 0

    spacer(0.1)
    p = Preformatted(txt, style)
    Elements.append(p)

def parseOdyssey(fn):
    from time import time
    E = []
    t0=time()
    L = open(fn,'r').readlines()
    t1 = time()
    print "open(%s,'r').readlines() took %.4f seconds" %(fn,t1-t0)
    for i in xrange(len(L)):
        if L[i][-1]=='\012':
            L[i] = L[i][:-1]
    t2 = time()
    print "Removing all linefeeds took %.4f seconds" %(t2-t1)
    L.append('')
    L.append('-----')

    def findNext(L, i):
        while 1:
            if string.strip(L[i])=='':
                del L[i]
                kind = 1
                if i<len(L):
                    while string.strip(L[i])=='':
                        del L[i]

                    if i<len(L):
                        kind = L[i][-1]=='-' and L[i][0]=='-'
                        if kind:
                            del L[i]
                            if i<len(L):
                                while string.strip(L[i])=='':
                                    del L[i]
                break
            else:
                i = i + 1

        return i, kind

    f = s = 0
    while 1:
        f, k = findNext(L,0)
        if k: break

    E.append([spacer,2])
    E.append([fTitle,'<font color="red">%s</font>' % Title, InitialStyle])
    E.append([fTitle,'<font size="-4">by</font> <font color="green">%s</font>' % Author, InitialStyle])

    while 1:
        if f>=len(L): break

        if string.upper(L[f][0:5])=='BOOK ':
            E.append([chapter,L[f]])
            f=f+1
            while string.strip(L[f])=='': del L[f]
            style = ParaStyle
            func = p
        else:
            style = PreStyle
            func = pre

        while 1:
            s=f
            f, k=findNext(L,s)
            sep= (func is pre) and '\012' or ' '
            E.append([func,string.join(L[s:f],sep),style])
            if k: break
    t3 = time()
    print "Parsing into memory took %.4f seconds" %(t3-t2)
    del L
    t4 = time()
    print "Deleting list of lines took %.4f seconds" %(t4-t3)
    for i in xrange(len(E)):
        apply(E[i][0],E[i][1:])
    t5 = time()
    print "Moving into platypus took %.4f seconds" %(t5-t4)
    del E
    t6 = time()
    print "Deleting list of actions took %.4f seconds" %(t6-t5)
    go()
    t7 = time()
    print "saving to PDF took %.4f seconds" %(t7-t6)
    print "Total run took %.4f seconds"%(t7-t0)

    import md5
    print 'file digest: %s' % md5.md5(open('dodyssey.pdf','rb').read()).hexdigest()

def run():
    for fn in ('odyssey.full.txt','odyssey.txt'):
        if os.path.isfile(fn):
            parseOdyssey(fn)
            break

def doProf(profname,func,*args,**kwd):
        import hotshot, hotshot.stats
        prof = hotshot.Profile(profname)
        prof.runcall(func)
        prof.close()
        stats = hotshot.stats.load(profname)
        stats.strip_dirs()
        stats.sort_stats('time', 'calls')
        stats.print_stats(20)

if __name__=='__main__':
    if '--prof' in sys.argv:
        doProf('dodyssey.prof',run)
    else:
        run()

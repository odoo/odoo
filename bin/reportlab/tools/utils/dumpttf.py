__all__=('dumpttf',)
def dumpttf(fn,fontName=None, verbose=0):
    '''dump out known glyphs from a ttf file'''
    import os
    if not os.path.isfile(fn):
        raise IOError('No such file "%s"' % fn)
    from reportlab.pdfbase.pdfmetrics import registerFont, stringWidth
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen.canvas import Canvas
    if fontName is None:
        fontName = os.path.splitext(os.path.basename(fn))[0]
    dmpfn = '%s-ttf-dump.pdf' % fontName
    ttf = TTFont(fontName, fn)
    K = ttf.face.charToGlyph.keys()
    registerFont(ttf)
    c = Canvas(dmpfn)
    W,H = c._pagesize
    titleFontSize = 30  # title font size
    titleFontName = 'Helvetica'
    labelFontName = 'Courier'
    fontSize = 10
    border = 36
    dx0 = stringWidth('12345: ', fontName, fontSize)
    dx = dx0+20
    dy = 20
    K.sort()
    y = 0
    page = 0
    for i, k in enumerate(K):
        if y<border:
            if page: c.showPage()
            page += 1
            y = H - border - titleFontSize
            c.setFont(titleFontName, titleFontSize)
            c.drawCentredString(W/2.0,y, 'TrueType Font %s Page %d' %(fontName,page))
            y -= 0.2*titleFontSize + dy
            x = border
        c.setFont(labelFontName, 10)
        c.drawString(x,y,'%5.5x:' % k )
        c.setFont(fontName, 10)
        c.drawString(x+dx0,y,unichr(k).encode('utf8'))
        x += dx
        if x+dx>W-border:
            x = border
            y -= dy
    c.showPage()
    c.save()
    if verbose:
        print 'Font %s("%s") has %d glyphs\ndumped to "%s"' % (fontName,fn,len(K),dmpfn)

if __name__=='__main__':
    import sys, glob
    if '--verbose' in sys.argv:
        sys.argv.remove('--verbose')
        verbose = 1
    else:
        verbose = 0
    for a in sys.argv[1:]:
        for fn in glob.glob(a):
            dumpttf(fn, verbose=verbose)

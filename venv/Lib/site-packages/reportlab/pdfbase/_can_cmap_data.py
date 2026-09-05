#
"""
This is a utility to 'can' the widths data for certain CID fonts.
Now we're using Unicode, we don't need 20 CMAP files for each Asian
language, nor the widths of the non-normal characters encoded in each
font.  we just want a dictionary of the character widths in a given
font which are NOT 1000 ems wide, keyed on Unicode character (not CID).

Running off CMAP files we get the following widths...::

    >>> font = UnicodeCIDFont('HeiseiMin-W3')
    >>> font.stringWidth(unicode(','), 10)
    2.5
    >>> font.stringWidth(unicode('m'), 10)
    7.7800000000000002
    >>> font.stringWidth(u'\u6771\u4EAC', 10)
    20.0
    >>> 

"""

from reportlab.pdfbase._cidfontdata import defaultUnicodeEncodings
from reportlab.pdfbase.cidfonts import UnicodeCIDFont


def run():

    buf = []
    buf.append('widthsByUnichar = {}')
    for fontName, (language, encName) in defaultUnicodeEncodings.items():
        print('handling %s : %s : %s' % (fontName, language, encName))

        #this does just about all of it for us, as all the info
        #we need is present.
        font = UnicodeCIDFont(fontName)

        widthsByCID = font.face._explicitWidths
        cmap = font.encoding._cmap
        nonStandardWidthsByUnichar = {}
        for codePoint, cid in cmap.items():
            width = widthsByCID.get(cid, 1000)
            if width != 1000:
                nonStandardWidthsByUnichar[chr(codePoint)] = width
        

        
        print('created font width map (%d items).  ' % len(nonStandardWidthsByUnichar))

        buf.append('widthsByUnichar["%s"] = %s' % (fontName, repr(nonStandardWidthsByUnichar)))
        
        
    src = '\n'.join(buf) + '\n'
    open('canned_widths.py','w').write(src)
    print('wrote canned_widths.py')

if __name__=='__main__':
    run()
    

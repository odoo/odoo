#How to add bleed to a page in this case 6mm to a landscape A4
from reportlab.lib import units, pagesizes
from reportlab.pdfgen.canvas import Canvas
import sys, os, glob, time
bleedX = 6*units.mm
bleedY = 6*units.mm
pageWidth, pageHeight = pagesizes.landscape(pagesizes.A4)
def process_pdf(c,infn,prefix='PageForms'):
    from rlextra.pageCatcher import pageCatcher
    names, data = pageCatcher.storeFormsInMemory(open(infn,'rb').read(),prefix=prefix,all=1)
    names = pageCatcher.restoreFormsInMemory(data,c)
    del data
    for i in xrange(len(names)):
        thisname = names[i]
        c.saveState()
        c.translate(bleedX,bleedY)
        c.doForm(thisname)
        c.restoreState()
        c.showPage()

def main():
    for infn in sys.argv[1:]:
        outfn = 'bleeding_'+os.path.basename(infn)
        c = Canvas(outfn,pagesize=(pageWidth+2*bleedX,pageHeight+2*bleedY))
        process_pdf(c,infn)
        c.save()
if __name__=='__main__':
    main()

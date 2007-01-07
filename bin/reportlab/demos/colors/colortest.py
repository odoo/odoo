#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/demos/colors/colortest.py
import reportlab.pdfgen.canvas
from reportlab.lib import colors
from reportlab.lib.units import inch


def run():
    c = reportlab.pdfgen.canvas.Canvas('colortest.pdf')

    #do a test of CMYK interspersed with RGB

    #first do RGB values
    framePage(c, 'Color Demo - RGB Space and CMYK spaces interspersed' )

    y = 700

    c.setFillColorRGB(0,0,0)
    c.drawString(100, y, 'cyan')
    c.setFillColorCMYK(1,0,0,0)
    c.rect(200, y, 300, 30, fill=1)
    y = y - 40

    c.setFillColorRGB(0,0,0)
    c.drawString(100, y, 'red')
    c.setFillColorRGB(1,0,0)
    c.rect(200, y, 300, 30, fill=1)
    y = y - 40

    c.setFillColorRGB(0,0,0)
    c.drawString(100, y, 'magenta')
    c.setFillColorCMYK(0,1,0,0)
    c.rect(200, y, 300, 30, fill=1)
    y = y - 40

    c.setFillColorRGB(0,0,0)
    c.drawString(100, y, 'green')
    c.setFillColorRGB(0,1,0)
    c.rect(200, y, 300, 30, fill=1)
    y = y - 40

    c.setFillColorRGB(0,0,0)
    c.drawString(100, y, 'yellow')
    c.setFillColorCMYK(0,0,1,0)
    c.rect(200, y, 300, 30, fill=1)
    y = y - 40

    c.setFillColorRGB(0,0,0)
    c.drawString(100, y, 'blue')
    c.setFillColorRGB(0,0,1)
    c.rect(200, y, 300, 30, fill=1)
    y = y - 40

    c.setFillColorRGB(0,0,0)
    c.drawString(100, y, 'black')
    c.setFillColorCMYK(0,0,0,1)
    c.rect(200, y, 300, 30, fill=1)
    y = y - 40


    c.showPage()

    #do all named colors
    framePage(c, 'Color Demo - RGB Space - page %d' % c.getPageNumber())

    all_colors = reportlab.lib.colors.getAllNamedColors().items()
    all_colors.sort() # alpha order by name
    c.setFont('Times-Roman', 12)
    c.drawString(72,730, 'This shows all the named colors in the HTML standard.')
    y = 700
    for (name, color) in all_colors:
        c.setFillColor(colors.black)
        c.drawString(100, y, name)
        c.setFillColor(color)
        c.rect(200, y-10, 300, 30, fill=1)
        y = y - 40
        if y < 100:
            c.showPage()
            framePage(c, 'Color Demo - RGB Space - page %d' % c.getPageNumber())
            y = 700




    c.save()

def framePage(canvas, title):
    canvas.setFont('Times-BoldItalic',20)
    canvas.drawString(inch, 10.5 * inch, title)

    canvas.setFont('Times-Roman',10)
    canvas.drawCentredString(4.135 * inch, 0.75 * inch,
                            'Page %d' % canvas.getPageNumber())

    #draw a border
    canvas.setStrokeColorRGB(1,0,0)
    canvas.setLineWidth(5)
    canvas.line(0.8 * inch, inch, 0.8 * inch, 10.75 * inch)
    #reset carefully afterwards
    canvas.setLineWidth(1)
    canvas.setStrokeColorRGB(0,0,0)

if __name__ == '__main__':
    run()

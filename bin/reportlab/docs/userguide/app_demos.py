#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/docs/userguide/app_demos.py
from reportlab.tools.docco.rl_doc_utils import *

Appendix1("ReportLab Demos")
disc("""In the subdirectories of $reportlab/demos$ there are a number of working examples showing
almost all aspects of reportlab in use.""")

heading2("""Odyssey""")
disc("""
The three scripts odyssey.py, dodyssey.py and fodyssey.py all take the file odyssey.txt
and produce PDF documents. The included odyssey.txt is short; a longer and more testing version
can be found at ftp://ftp.reportlab.com/odyssey.full.zip.
""")
eg("""
Windows
cd reportlab\\demos\\odyssey
python odyssey.py
start odyssey.pdf

Linux
cd reportlab/demos/odyssey
python odyssey.py
acrord odyssey.pdf
""")
disc("""Simple formatting is shown by the odyssey.py script. It runs quite fast,
but all it does is gather the text and force it onto the canvas pages. It does no paragraph
manipulation at all so you get to see the XML &lt; &amp; &gt; tags.
""")
disc("""The scripts fodyssey.py and dodyssey.py handle paragraph formatting so you get
to see colour changes etc. Both scripts
use the document template class and the dodyssey.py script shows the ability to do dual column
layout and uses multiple page templates.
""")

heading2("""Standard Fonts and Colors""")
disc("""In $reportlab/demos/stdfonts$ the script stdfonts.py can be used to illustrate
ReportLab's standard fonts. Run the script using""")
eg("""
cd reportlab\\demos\\stdfonts
python stdfonts.py
""")
disc("""
to produce two PDF documents, StandardFonts_MacRoman.pdf &amp;
StandardFonts_WinAnsi.pdf which show the two most common built in
font encodings.
""")
disc("""The colortest.py script in $reportlab/demos/colors$ demonstrates the different ways in which
reportlab can set up and use colors.""")
disc("""Try running the script and viewing the output document, colortest.pdf. This shows
different color spaces and a large selection of the colors which are named
in the $reportlab.lib.colors$ module.
""")
heading2("""Py2pdf""")
disc("""Dinu Gherman (&lt;gherman@europemail.com&gt;) contributed this useful script
which uses reportlab to produce nicely colorized PDF documents from Python
scripts including bookmarks for classes, methods and functions.
To get a nice version of the main script try""")
eg("""
cd reportlab/demos/py2pdf
python py2pdf.py py2pdf.py
acrord py2pdf.pdf
""")
disc("""i.e. we used py2pdf to produce a nice version of py2pdf.py in
the document with the same rootname and a .pdf extension.
""")
disc("""
The py2pdf.py script has many options which are beyond the scope of this
simple introduction; consult the comments at the start of the script.
""")
heading2("Gadflypaper")
disc("""
The Python script, gfe.py, in $reportlab/demos/gadflypaper$ uses an inline style of
document preparation. The script almost entirely produced by Aaron Watters produces a document
describing Aaron's $gadfly$ in memory database for Python. To generate the document use
""")
eg("""
cd reportlab\\gadflypaper
python gfe.py
start gfe.pdf
""")
disc("""
everything in the PDF document was produced by the script which is why this is an inline style
of document production. So, to produce a header followed by some text the script uses functions
$header$ and $p$ which take some text and append to a global story list.
""")
eg('''
header("Conclusion")

p("""The revamped query engine design in Gadfly 2 supports
..........
and integration.""")
''')
heading2("""Pythonpoint""")
disc("""Andy Robinson has refined the pythonpoint.py script (in $reportlab\\demos\\pythonpoint$)
until it is a really useful script. It takes an input file containing an XML markup
and uses an xmllib style parser to map the tags into PDF slides. When run in its own directory
pythonpoint.py takes as a default input the file pythonpoint.xml and produces pythonpoint.pdf
which is documentation for Pythonpoint! You can also see it in action with an older paper
""")
eg("""
cd reportlab\\demos\\pythonpoint
python pythonpoint.py monterey.xml
start monterey.pdf
""")
disc("""
Not only is pythonpoint self documenting, but it also demonstrates reportlab and PDF. It uses
many features of reportlab (document templates, tables etc).
Exotic features of PDF such as fadeins and bookmarks are also shown to good effect. The use of
an XML document can be contrasted with the <i>inline</i> style of the gadflypaper demo; the
content is completely separate from the formatting
""")
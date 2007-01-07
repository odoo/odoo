This contains a number of benchmarks and demos
based on Homer's Odyssey (which is widely available
in plain, line-oriented text format). There are a large 
selection of online books at:
	http://classics.mit.edu/


Our distribution ships with just the first chapter
in odyssey.txt.  For a more meaningful speed test,
download the full copy from
  http://www.reportlab.com/ftp/odyssey.full.zip
or
 ftp://ftp.reportlab.com/odyssey.full.zip
and unzip to extract odyssey.full.txt (608kb).

Benchmark speed depends quite critically
on the presence of our accelerator module,
_rl_accel, which is a C (or Java) extension.
Serious users ought to compile or download this!

The times quoted are from one machine (Andy Robinson's
home PC, approx 1.2Ghz 128Mb Ram, Win2k in Sep 2003)
in order to give a rough idea of what features cost
what performance.


The tests are as follows:

(1) odyssey.py   (produces odyssey.pdf)
This demo takes a large volume of text and prints it
in the simplest way possible.  It is a demo of the
basic technique of looping down a page manually and 
breaking at the bottom.  On my 1.2 Ghz machine this takes
1.91 seconds (124 pages per second)

(2) fodyssey.py  (produces fodyssey.pdf)
This is a 'flowing document' we parse the file and
throw away line breaks to make proper paragraphs.
The Platypus framework renders these.  This necessitates
measuring the width of every word in every paragraph
for wrapping purposes.  

This takes 3.27 seconds on the same machine.  Paragraph
wrapping basically doubles the work.  The text is more 
compact with about 50% more words per page.  Very roughly,
we can wrap 40 pages of ten-point text per second and save
to PDF.

(3) dodyssey.py  (produced dodyssey.pdf)
This is a slightly fancier version which uses different
page templates (one column for first page in a chapter,
two column for body poages).  The additional layout logic
adds about 15%, going up to 3.8 seconds.  This is probably
a realistic benchmark for a simple long text document
with a single pass.  Documents doing cross-references
and a table of contents might need twice as long.

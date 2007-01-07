#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/docs/graphguide/ch1_intro.py
from reportlab.tools.docco.rl_doc_utils import *
import reportlab

title("Graphics Guide")
centred('ReportLab Version ' + reportlab.Version)

nextTemplate("Normal")

########################################################################
#
#               Chapter 1
#
########################################################################


heading1("Introduction")


heading2("About this document")
disc("""
This document is intended to be a helpful and reasonably full
introduction to the use of the ReportLab Graphics sub-package.
Starting with simple drawings and shapes, we will take you through the
slightly more complex reusable widgets all the way through to our
powerful and flexible chart library. You will see examples of using
reportlab/graphics to make bar charts, line charts, line plots, pie
charts... and a smiley face.
""")

disc("""
We presume that you have already installed both the Python programming
language and the core ReportLab library. If you have not done either
of these, look in the ReportLab User Guide where chapter one
talks you through all the required steps.
""")

disc("""
We recommend that you read some or all of the User Guide and have at
least a basic understanding of how the ReportLab library works before
you start getting to grips with ReportLab Graphics.
""")

disc("")
todo("""
Be warned! This document is in a <em>very</em> preliminary form.  We need
your help to make sure it is complete and helpful.  Please send any
feedback to our user mailing list, reportlab-users@reportlab.com.
""")

heading2("What is ReportLab?")
disc("""ReportLab is a software library that lets you directly
create documents in Adobe's Portable Document Format (PDF) using
the Python programming language. """)

disc("""The ReportLab library directly creates PDF based on
your graphics commands.  There are no intervening steps.  Your applications
can generate reports extremely fast - sometimes orders
of magnitude faster than traditional report-writing
tools.""")

heading2("What is ReportLab Graphics?")
disc("""
ReportLab Graphics is one of the sub-packages to the ReportLab
library. It started off as a stand-alone set of programs, but is now a
fully integrated part of the ReportLab toolkit that allows you to use
its powerful charting and graphics features to improve your PDF forms
and reports.
""")

heading2("Getting Involved")
disc("""ReportLab is an Open Source project.  Although we are
a commercial company we provide the core PDF generation
sources freely, even for commercial purposes, and we make no income directly
from these modules.  We also welcome help from the community
as much as any other Open Source project.  There are many
ways in which you can help:""")

bullet("""General feedback on the core API. Does it work for you?
Are there any rough edges?  Does anything feel clunky and awkward?""")

bullet("""New objects to put in reports, or useful utilities for the library.
We have an open standard for report objects, so if you have written a nice
chart or table class, why not contribute it?""")

bullet("""Demonstrations and Case Studies: If you have produced some nice
output, send it to us (with or without scripts).  If ReportLab solved a
problem for you at work, write a little 'case study' and send it in.
And if your web site uses our tools to make reports, let us link to it.
We will be happy to display your work (and credit it with your name
and company) on our site!""")

bullet("""Working on the core code:  we have a long list of things
to refine or to implement.  If you are missing some features or
just want to help out, let us know!""")

disc("""The first step for anyone wanting to learn more or
get involved is to join the mailing list.  To Subscribe visit
$http://two.pairlist.net/mailman/listinfo/reportlab-users$.
From there you can also browse through the group's archives
and contributions.  The mailing list is
the place to report bugs and get support. """)


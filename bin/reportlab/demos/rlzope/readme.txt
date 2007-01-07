# rlzope : an external Zope method to show people how to use
# the ReportLab toolkit from within Zope.
#
# this method searches an image named 'logo' in the
# ZODB then prints it at the top of a simple PDF
# document made with ReportLab
#
# the resulting PDF document is returned to the
# user's web browser and, if possible, it is
# simultaneously saved into the ZODB.
#
# this method illustrates how to use both the platypus
# and canvas frameworks.
#
# License : The ReportLab Toolkit's license (similar to BSD)
#
# Author : Jerome Alet - alet@unice.fr
#

Installation instructions :
===========================

  0 - If not installed then install Zope.

  1 - Install reportlab in the Zope/lib/python/Shared directory by unpacking 
      the tarball and putting a reportlabs.pth file in site-packages for the Zope
      used with Python.  The path value in the reportlabs.pth file must be 
      relative.  For a typical Zope installation,  the path is "../../python/Shared".
      Remember to restart Zope so the new path is instantiated.

  2 - Install PIL in the Zope/lib/python/Shared directory. You need to
      ensure that the _imaging.so or .pyd is also installed appropriately.
	  It should be compatible with the python running the zope site.

  3 - Copy rlzope.py to your Zope installation's "Extensions"
      subdirectory, e.g. /var/lib/zope/Extensions/ under Debian GNU/Linux.

  4 - From within Zope's management interface, add an External Method with
      these parameters :

		   Id : rlzope
		Title : rlzope
	  Module Name : rlzope
	Function Name : rlzope

  5 - From within Zope's management interface, add an image called "logo"
      in the same Folder than rlzope, or somewhere above in the Folder
      hierarchy. For example you can use ReportLab's logo which you
      can find in reportlab/docs/images/replogo.gif

  6 - Point your web browser to rlzope, e.g. on my laptop under
      Debian GNU/Linux :

		http://localhost:9673/rlzope

	This will send a simple PDF document named 'dummy.pdf' to your
	web browser, and if possible save it as a File object in the
	Zope Object DataBase, with this name. Note, however, that if
	an object with the same name already exists then it won't
	be replaced for security reasons.

	You can optionally add a parameter called 'name' with
	a filename as the value, to specify another filename,
	e.g. :
logo
		http://localhost:9673/rlzope?name=sample.pdf

  7 - Adapt it to your own needs.

  8 - Enjoy !

Send comments or bug reports at : alet@unice.fr


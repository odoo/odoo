from xlrd import xlsx
from lxml import etree

# xlrd.xlsx supports defusedxml, defusedxml's etree interface is broken
# (missing ElementTree and thus ElementTree.iter) which causes a fallback to
# Element.getiterator(), triggering a warning before 3.9 and an error from 3.9.
#
# We have defusedxml installed because zeep has a hard dep on defused and
# doesn't want to drop it (mvantellingen/python-zeep#1014).
#
# Ignore the check and set the relevant flags directly using lxml as we have a
# hard dependency on it.
xlsx.ET = etree
xlsx.ET_has_iterparse = True
xlsx.Element_has_iter = True

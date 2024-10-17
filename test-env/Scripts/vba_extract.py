#!C:\Users\Admin\odoo\test-env\Scripts\python.exe

##############################################################################
#
# vba_extract - A simple utility to extract a vbaProject.bin binary from an
# Excel 2007+ xlsm file for insertion into an XlsxWriter file.
#
# Copyright 2013-2018, John McNamara, jmcnamara@cpan.org
#
import sys
import shutil
from zipfile import ZipFile
from zipfile import BadZipfile

# The VBA project file we want to extract.
vba_filename = 'vbaProject.bin'

# Get the xlsm file name from the commandline.
if len(sys.argv) > 1:
    xlsm_file = sys.argv[1]
else:
    print("\nUtility to extract a vbaProject.bin binary from an Excel 2007+ "
          "xlsm macro file for insertion into an XlsxWriter file."
          "\n"
          "See: https://xlsxwriter.readthedocs.io/working_with_macros.html\n"
          "\n"
          "Usage: vba_extract file.xlsm\n")
    exit()

try:
    # Open the Excel xlsm file as a zip file.
    xlsm_zip = ZipFile(xlsm_file, 'r')

    # Read the xl/vbaProject.bin file.
    vba_data = xlsm_zip.read('xl/' + vba_filename)

    # Write the vba data to a local file.
    vba_file = open(vba_filename, "wb")
    vba_file.write(vba_data)
    vba_file.close()

except IOError:
    # Use exc_info() for Python 2.5+ compatibility.
    e = sys.exc_info()[1]
    print("File error: %s" % str(e))
    exit()

except KeyError:
    # Usually when there isn't a xl/vbaProject.bin member in the file.
    e = sys.exc_info()[1]
    print("File error: %s" % str(e))
    print("File may not be an Excel xlsm macro file: '%s'" % xlsm_file)
    exit()

except BadZipfile:
    # Usually if the file is an xls file and not an xlsm file.
    e = sys.exc_info()[1]
    print("File error: %s: '%s'" % (str(e), xlsm_file))
    print("File may not be an Excel xlsm macro file.")
    exit()

except:
    # Catch any other exceptions.
    e = sys.exc_info()[1]
    print("File error: %s" % str(e))
    exit()

print("Extracted: %s" % vba_filename)

#!/home/thang2k6adu/workspace/odoo/odoo/venv/bin/python3

##############################################################################
#
# vba_extract - A simple utility to extract a vbaProject.bin binary from an
# Excel 2007+ xlsm file for insertion into an XlsxWriter file.
#
# SPDX-License-Identifier: BSD-2-Clause
# Copyright 2013-2023, John McNamara, jmcnamara@cpan.org
#
import sys
from zipfile import ZipFile
from zipfile import BadZipFile


def extract_file(xlsm_zip, filename):
    # Extract a single file from an Excel xlsm macro file.
    data = xlsm_zip.read("xl/" + filename)

    # Write the data to a local file.
    file = open(filename, "wb")
    file.write(data)
    file.close()


# The VBA project file and project signature file we want to extract.
vba_filename = "vbaProject.bin"
vba_signature_filename = "vbaProjectSignature.bin"

# Get the xlsm file name from the commandline.
if len(sys.argv) > 1:
    xlsm_file = sys.argv[1]
else:
    print(
        "\nUtility to extract a vbaProject.bin binary from an Excel 2007+ "
        "xlsm macro file for insertion into an XlsxWriter file.\n"
        "If the macros are digitally signed, extracts also a vbaProjectSignature.bin "
        "file.\n"
        "\n"
        "See: https://xlsxwriter.readthedocs.io/working_with_macros.html\n"
        "\n"
        "Usage: vba_extract file.xlsm\n"
    )
    exit()

try:
    # Open the Excel xlsm file as a zip file.
    xlsm_zip = ZipFile(xlsm_file, "r")

    # Read the xl/vbaProject.bin file.
    extract_file(xlsm_zip, vba_filename)
    print("Extracted: %s" % vba_filename)

    if "xl/" + vba_signature_filename in xlsm_zip.namelist():
        extract_file(xlsm_zip, vba_signature_filename)
        print("Extracted: %s" % vba_signature_filename)


except IOError as e:
    print("File error: %s" % str(e))
    exit()

except KeyError as e:
    # Usually when there isn't a xl/vbaProject.bin member in the file.
    print("File error: %s" % str(e))
    print("File may not be an Excel xlsm macro file: '%s'" % xlsm_file)
    exit()

except BadZipFile as e:
    # Usually if the file is an xls file and not an xlsm file.
    print("File error: %s: '%s'" % (str(e), xlsm_file))
    print("File may not be an Excel xlsm macro file.")
    exit()

except Exception as e:
    # Catch any other exceptions.
    print("File error: %s" % str(e))
    exit()

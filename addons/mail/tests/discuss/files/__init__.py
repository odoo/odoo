from odoo.tools import file_path

_directory = 'mail/tests/discuss/files/'

AES_pdf = file_path(_directory + 'test_AES.pdf', filter_ext=('.pdf',))
unicode_pdf = file_path(_directory + 'test_unicode.pdf', filter_ext=('.pdf',))

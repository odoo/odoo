# This test can be run stand-alone with something like:
# > PYTHONPATH=. python2 openerp/tests/test_view_validation.py

from lxml import etree
from StringIO import StringIO
import unittest2

import openerp
from openerp.tools.view_validation import valid_page_in_book, valid_view

invalid_page = etree.parse(StringIO('''\
<form>
  <group>
    <div>
      <page>
      </page>
    </div>
  </group>
</form>
''')).getroot()

valid_page = etree.parse(StringIO('''\
<form>
  <notebook>
    <div>
      <page>
      </page>
    </div>
  </notebook>
</form>
''')).getroot()

class test_view_validation(unittest2.TestCase):
    """ Test the view validation code (but not the views themselves). """

    def test_page_validation(self):
        assert not valid_page_in_book(invalid_page)
        assert valid_page_in_book(valid_page)

        assert not valid_view(invalid_page)
        assert valid_view(valid_page)

if __name__ == '__main__':
    unittest2.main()

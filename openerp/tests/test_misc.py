# This test can be run stand-alone with something like:
# > PYTHONPATH=. python2 openerp/tests/test_misc.py

import unittest2

class test_misc(unittest2.TestCase):
    """ Test some of our generic utility functions """

    def test_append_to_html(self):
        from openerp.tools import append_content_to_html
        test_samples = [
            ('<!DOCTYPE...><HTML encoding="blah">some <b>content</b></HtMl>', '--\nYours truly', True,
             '<!DOCTYPE...><html encoding="blah">some <b>content</b>\n<pre>--\nYours truly</pre>\n</html>'),
            ('<html><body>some <b>content</b></body></html>', '<!DOCTYPE...>\n<html><body>\n<p>--</p>\n<p>Yours truly</p>\n</body>\n</html>', False,
             '<html><body>some <b>content</b>\n\n\n<p>--</p>\n<p>Yours truly</p>\n\n\n</body></html>'),
        ]
        for html, content, flag, expected in test_samples:
            self.assertEqual(append_content_to_html(html,content,flag), expected, 'append_content_to_html is broken')

if __name__ == '__main__':
    unittest2.main()
from datetime import datetime, timedelta

from odoo.tests import common, tagged
from odoo.tools._vendor.pdf417gen import encode, render_image, render_svg


ZEN = """
Beautiful is better than ugly.
Explicit is better than implicit.
Simple is better than complex.
Complex is better than complicated.
Flat is better than nested.
Sparse is better than dense.
Readability counts.
Special cases aren't special enough to break the rules.
Although practicality beats purity.
Errors should never pass silently.
Unless explicitly silenced.
In the face of ambiguity, refuse the temptation to guess.
There should be one-- and preferably only one --obvious way to do it.
Although that way may not be obvious at first unless you're Dutch.
Now is better than never.
Although never is often better than *right* now.
If the implementation is hard to explain, it's a bad idea.
If the implementation is easy to explain, it may be a good idea.
Namespaces are one honking great idea -- let's do more of those!
""".strip()


@tagged('-at_install', 'post_install')
class TestPerformance(common.TransactionCase):

    def test_encode(self, cycles=100):
        start = datetime.now()
        for _ in range(cycles):
            encode(ZEN)
        duration = datetime.now() - start
        self.assertLess(duration, timedelta(milliseconds=500))


    def test_render_image(self, cycles=100):
        codes = encode(ZEN)
        start = datetime.now()
        for _ in range(cycles):
            render_image(codes)
        duration = datetime.now() - start
        self.assertLess(duration, timedelta(milliseconds=500))


    def test_render_svg(self, cycles=100):
        codes = encode(ZEN)
        start = datetime.now()
        for _ in range(cycles):
            render_svg(codes)
        duration = datetime.now() - start
        self.assertLess(duration, timedelta(seconds=2))

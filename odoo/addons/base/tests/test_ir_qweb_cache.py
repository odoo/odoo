# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree, html
from lxml.builder import E
from textwrap import dedent

from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.addons.base.models.ir_qweb import QWebError, render
from odoo.tools import mute_logger


@tagged('post_install', '-at_install')
class TestQwebCache(TransactionCase):
    def test_render_xml_cache_base(self):
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">
                    <div t-cache="cache_id" class="toto">
                        <table>
                            <tr><td><span t-out="value[0]"/></td></tr>
                            <tr><td><span t-out="value[1]"/></td></tr>
                            <tr><td><span t-out="value[2]"/></td></tr>
                        </table>
                    </div>
                </t>
            """
        })
        expected_result = etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td><span>1</span></td></tr>
                    <tr><td><span>2</span></td></tr>
                    <tr><td><span>3</span></td></tr>
                </table>
            </div>
        """)

        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=False)

        result = etree.fromstring(IrQweb._render(view1.id, {'cache_id': 1, 'value': [1, 2, 3]}))
        self.assertEqual(result, expected_result, 'First rendering (add in cache)')

        result = etree.fromstring(IrQweb._render(view1.id, {'cache_id': 1, 'value': [10, 20, 30]}))
        self.assertEqual(result, expected_result, 'Next rendering use cache')

    def test_render_xml_cache_different(self):
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">
                    <div class="toto">
                        <table t-cache="cache_id">
                            <tr><td><span t-out="value[0]"/></td></tr>
                            <tr><td><span t-out="value[1]"/></td></tr>
                            <tr><td><span t-out="value[2]"/></td></tr>
                        </table>
                        <table t-cache="cache_id2">
                            <tr><td><span t-out="value2[0]"/></td></tr>
                            <tr><td><span t-out="value2[1]"/></td></tr>
                            <tr><td><span t-out="value2[2]"/></td></tr>
                        </table>
                    </div>
                </t>
            """
        })
        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=False)

        # use same cache id, display the same content
        result = etree.fromstring(IrQweb._render(view1.id, {
            'cache_id': (1,),
            'cache_id2': (1,),
            'value': [1, 2, 3],
            'value2': [10, 20, 30]
        }))
        self.assertEqual(result, etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td><span>1</span></td></tr>
                    <tr><td><span>2</span></td></tr>
                    <tr><td><span>3</span></td></tr>
                </table>
                <table>
                    <tr><td><span>10</span></td></tr>
                    <tr><td><span>20</span></td></tr>
                    <tr><td><span>30</span></td></tr>
                </table>
            </div>
        """), 'First rendering (add in cache with different cache)')

        result = etree.fromstring(IrQweb._render(view1.id, {
            'cache_id': (2, 5, 6),
            'cache_id2': (2, 5, 5),
            'value': [41, 42, 43],
            'value2': [51, 52, 53]
        }))
        self.assertEqual(result, etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td><span>41</span></td></tr>
                    <tr><td><span>42</span></td></tr>
                    <tr><td><span>43</span></td></tr>
                </table>
                <table>
                    <tr><td><span>51</span></td></tr>
                    <tr><td><span>52</span></td></tr>
                    <tr><td><span>53</span></td></tr>
                </table>
            </div>
        """), 'Use different cache id')

    def test_render_xml_cache_contains_nocache(self):
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">
                    <div t-cache="cache_id" class="toto">
                        <table>
                            <tr><td><span t-out="value[0]"/></td></tr>
                            <tr t-nocache=""><td><span t-out="value[1]"/></td></tr>
                            <tr><td><span t-out="value[2]"/></td></tr>
                        </table>
                    </div>
                </t>
            """
        })
        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=False)

        result = etree.fromstring(IrQweb._render(view1.id, {'cache_id': 1, 'value': [1, 2, 3]}))
        self.assertEqual(result, etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td><span>1</span></td></tr>
                    <tr><td><span>2</span></td></tr>
                    <tr><td><span>3</span></td></tr>
                </table>
            </div>
        """), 'First rendering add compiled values in cache')

        result = etree.fromstring(IrQweb._render(view1.id, {'cache_id': 1, 'value': [10, 20, 30]}))
        self.assertEqual(result, etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td><span>1</span></td></tr>
                    <tr><td><span>20</span></td></tr>
                    <tr><td><span>3</span></td></tr>
                </table>
            </div>
        """), 'Next rendering use cache exept for t-nocache=""')

    def test_render_xml_cache_nocache_cache(self):
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">
                    <div class="toto">
                        <table t-cache="cache_id">
                            <tr><td><t t-out="value[0]"/></td></tr>
                            <tr>
                                <td>
                                    <table t-nocache="The content is not used, we can put documentation in it." t-cache="cache_id2">
                                        <tr><td><t t-out="value2[0]"/></td></tr>
                                        <tr><td><t t-out="value2[1]"/></td></tr>
                                        <tr><td><t t-out="value2[2]"/></td></tr>
                                    </table>
                                </td>
                            </tr>
                            <tr><td><t t-out="value[2]"/></td></tr>
                        </table>
                    </div>
                </t>
            """
        })

        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=False)

        # use same cache id, display the same content
        result = etree.fromstring(IrQweb._render(view1.id, {
            'cache_id': (1, 0),
            'cache_id2': (2, 0),
            'value': [1, 2, 3],
            'value2': [10, 20, 30]
        }))
        self.assertEqual(result, etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td>1</td></tr>
                    <tr>
                        <td>
                            <table>
                                <tr><td>10</td></tr>
                                <tr><td>20</td></tr>
                                <tr><td>30</td></tr>
                            </table>
                        </td>
                    </tr>
                    <tr><td>3</td></tr>
                </table>
            </div>
        """), 'First rendering (add in cache)')

        result = etree.fromstring(IrQweb._render(view1.id, {
            'cache_id': (1, 0),
            'cache_id2': (2, 1),
            'value': [41, 42, 43],
            'value2': [51, 52, 53]
        }))
        self.assertEqual(result, etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td>1</td></tr>
                    <tr>
                        <td>
                            <table>
                                <tr><td>51</td></tr>
                                <tr><td>52</td></tr>
                                <tr><td>53</td></tr>
                            </table>
                        </td>
                    </tr>
                    <tr><td>3</td></tr>
                </table>
            </div>
        """), 'Second rendering (change inside cache id)')

        result = etree.fromstring(IrQweb._render(view1.id, {
            'cache_id': (1, 1),
            'cache_id2': (2, 0),
            'value': [31, 32, 33],
            'value2': [51, 52, 53]
        }))
        self.assertEqual(result, etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td>31</td></tr>
                    <tr>
                        <td>
                            <table>
                                <tr><td>10</td></tr>
                                <tr><td>20</td></tr>
                                <tr><td>30</td></tr>
                            </table>
                        </td>
                    </tr>
                    <tr><td>33</td></tr>
                </table>
            </div>
        """), 'Third rendering (change main cache id, old cache inside)')

    def test_render_xml_cache_nocache_cache_on_same_tag(self):
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">
                    <div class="toto">
                        <table t-cache="cache_id">
                            <tr><td><t t-out="value[0]"/></td></tr>
                            <tr t-nocache="">
                                <td>
                                    <table t-cache="cache_id2">
                                        <tr><td><t t-out="value2[0]"/></td></tr>
                                        <tr><td><t t-out="value2[1]"/></td></tr>
                                        <tr><td><t t-out="value2[2]"/></td></tr>
                                    </table>
                                </td>
                            </tr>
                            <tr><td><t t-out="value[2]"/></td></tr>
                        </table>
                    </div>
                </t>
            """
        })

        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=False)

        # use same cache id, display the same content
        result = etree.fromstring(IrQweb._render(view1.id, {
            'cache_id': (1, 0),
            'cache_id2': (2, 0),
            'value': [1, 2, 3],
            'value2': [10, 20, 30]
        }))
        self.assertEqual(result, etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td>1</td></tr>
                    <tr>
                        <td>
                            <table>
                                <tr><td>10</td></tr>
                                <tr><td>20</td></tr>
                                <tr><td>30</td></tr>
                            </table>
                        </td>
                    </tr>
                    <tr><td>3</td></tr>
                </table>
            </div>
        """), 'First rendering (add in cache)')

        result = etree.fromstring(IrQweb._render(view1.id, {
            'cache_id': (1, 0),
            'cache_id2': (2, 1),
            'value': [41, 42, 43],
            'value2': [51, 52, 53]
        }))
        self.assertEqual(result, etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td>1</td></tr>
                    <tr>
                        <td>
                            <table>
                                <tr><td>51</td></tr>
                                <tr><td>52</td></tr>
                                <tr><td>53</td></tr>
                            </table>
                        </td>
                    </tr>
                    <tr><td>3</td></tr>
                </table>
            </div>
        """), 'Second rendering (change inside cache id)')

        result = etree.fromstring(IrQweb._render(view1.id, {
            'cache_id': (1, 1),
            'cache_id2': (2, 0),
            'value': [31, 32, 33],
            'value2': [51, 52, 53]
        }))
        self.assertEqual(result, etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td>31</td></tr>
                    <tr>
                        <td>
                            <table>
                                <tr><td>10</td></tr>
                                <tr><td>20</td></tr>
                                <tr><td>30</td></tr>
                            </table>
                        </td>
                    </tr>
                    <tr><td>33</td></tr>
                </table>
            </div>
        """), 'Third rendering (change main cache id, old cache inside)')

    def test_render_xml_dont_use_cache_base(self):
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">
                    <div t-cache="cache_id" class="toto">
                        <table>
                            <tr><td><span t-out="value[0]"/></td></tr>
                            <tr><td><span t-out="value[1]"/></td></tr>
                            <tr><td><span t-out="value[2]"/></td></tr>
                        </table>
                    </div>
                </t>
            """
        })
        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=True)

        result = etree.fromstring(IrQweb._render(view1.id, {'cache_id': 1, 'value': [1, 2, 3]}))
        self.assertEqual(result, etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td><span>1</span></td></tr>
                    <tr><td><span>2</span></td></tr>
                    <tr><td><span>3</span></td></tr>
                </table>
            </div>
        """), 'First rendering')

        result = etree.fromstring(IrQweb._render(view1.id, {'cache_id': 1, 'value': [10, 20, 30]}))
        self.assertEqual(result, etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td><span>10</span></td></tr>
                    <tr><td><span>20</span></td></tr>
                    <tr><td><span>30</span></td></tr>
                </table>
            </div>
        """), 'Next rendering cannot cache (use_qweb_t_cache is False)')

    def test_render_xml_dont_use_cache_different(self):
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">
                    <div class="toto">
                        <table t-cache="cache_id">
                            <tr><td><span t-out="value[0]"/></td></tr>
                            <tr><td><span t-out="value[1]"/></td></tr>
                            <tr><td><span t-out="value[2]"/></td></tr>
                        </table>
                        <table t-cache="cache_id2">
                            <tr><td><span t-out="value2[0]"/></td></tr>
                            <tr><td><span t-out="value2[1]"/></td></tr>
                            <tr><td><span t-out="value2[2]"/></td></tr>
                        </table>
                    </div>
                </t>
            """
        })
        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=True)

        # use same cache id, display the same content
        result = etree.fromstring(IrQweb._render(view1.id, {
            'cache_id': 1,
            'cache_id2': 1,
            'value': [1, 2, 3],
            'value2': [10, 20, 30]
        }))
        self.assertEqual(result, etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td><span>1</span></td></tr>
                    <tr><td><span>2</span></td></tr>
                    <tr><td><span>3</span></td></tr>
                </table>
                <table>
                    <tr><td><span>10</span></td></tr>
                    <tr><td><span>20</span></td></tr>
                    <tr><td><span>30</span></td></tr>
                </table>
            </div>
        """), 'First rendering')

        result = etree.fromstring(IrQweb._render(view1.id, {
            'cache_id': (2, 5, 6),
            'cache_id2': (2, 5, 5),
            'value': [41, 42, 43],
            'value2': [51, 52, 53]
        }))
        self.assertEqual(result, etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td><span>41</span></td></tr>
                    <tr><td><span>42</span></td></tr>
                    <tr><td><span>43</span></td></tr>
                </table>
                <table>
                    <tr><td><span>51</span></td></tr>
                    <tr><td><span>52</span></td></tr>
                    <tr><td><span>53</span></td></tr>
                </table>
            </div>
        """), 'Use different cache id')

    def test_render_xml_dont_use_cache_contains_nocache(self):
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">
                    <div t-cache="cache_id" class="toto">
                        <table>
                            <tr><td><span t-out="value[0]"/></td></tr>
                            <tr t-nocache=""><td><span t-out="value[1]"/></td></tr>
                            <tr><td><span t-out="value[2]"/></td></tr>
                        </table>
                    </div>
                </t>
            """
        })
        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=True)

        result = etree.fromstring(IrQweb._render(view1.id, {'cache_id': 1, 'value': [1, 2, 3]}))
        self.assertEqual(result, etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td><span>1</span></td></tr>
                    <tr><td><span>2</span></td></tr>
                    <tr><td><span>3</span></td></tr>
                </table>
            </div>
        """), 'First rendering')

        result = etree.fromstring(IrQweb._render(view1.id, {'cache_id': 1, 'value': [10, 20, 30]}))
        self.assertEqual(result, etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td><span>10</span></td></tr>
                    <tr><td><span>20</span></td></tr>
                    <tr><td><span>30</span></td></tr>
                </table>
            </div>
        """), 'Next rendering cannot use cache (use_qweb_t_cache is False)')

    def test_render_xml_dont_use_cache_recursive(self):
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">
                    <div class="toto">
                        <table t-cache="cache_id">
                            <tr><td><t t-out="value[0]"/></td></tr>
                            <tr>
                                <td>
                                    <table t-nocache="" t-cache="cache_id2">
                                        <tr><td><t t-out="value2[0]"/></td></tr>
                                        <tr><td><t t-out="value2[1]"/></td></tr>
                                        <tr><td><t t-out="value2[2]"/></td></tr>
                                    </table>
                                </td>
                            </tr>
                            <tr><td><t t-out="value[2]"/></td></tr>
                        </table>
                    </div>
                </t>
            """
        })
        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=True)

        # use same cache id, display the same content
        result = etree.fromstring(IrQweb._render(view1.id, {
            'cache_id': (1, 0),
            'cache_id2': (2, 0),
            'value': [1, 2, 3],
            'value2': [10, 20, 30]
        }))
        self.assertEqual(result, etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td>1</td></tr>
                    <tr>
                        <td>
                            <table>
                                <tr><td>10</td></tr>
                                <tr><td>20</td></tr>
                                <tr><td>30</td></tr>
                            </table>
                        </td>
                    </tr>
                    <tr><td>3</td></tr>
                </table>
            </div>
        """), 'First rendering')

        result = etree.fromstring(IrQweb._render(view1.id, {
            'cache_id': (1, 0),
            'cache_id2': (2, 1),
            'value': [41, 42, 43],
            'value2': [51, 52, 53]
        }))
        self.assertEqual(result, etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td>41</td></tr>
                    <tr>
                        <td>
                            <table>
                                <tr><td>51</td></tr>
                                <tr><td>52</td></tr>
                                <tr><td>53</td></tr>
                            </table>
                        </td>
                    </tr>
                    <tr><td>43</td></tr>
                </table>
            </div>
        """), 'Next rendering cannot use cache (use_qweb_t_cache is False)')

        result = etree.fromstring(IrQweb._render(view1.id, {
            'cache_id': (1, 1),
            'cache_id2': (2, 0),
            'value': [31, 32, 33],
            'value2': [51, 52, 53]
        }))
        self.assertEqual(result, etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td>31</td></tr>
                    <tr>
                        <td>
                            <table>
                                <tr><td>51</td></tr>
                                <tr><td>52</td></tr>
                                <tr><td>53</td></tr>
                            </table>
                        </td>
                    </tr>
                    <tr><td>33</td></tr>
                </table>
            </div>
        """), 'Third rendering cannot use cache (use_qweb_t_cache is False)')

    def test_render_xml_dont_use_cache_false_recursive(self):
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">
                    <div class="toto">
                        <table t-cache="cache_id">
                            <tr><td><t t-out="value[0]"/></td></tr>
                            <tr t-nocache="">
                                <td>
                                    <table t-cache="cache_id2">
                                        <tr><td><t t-out="value2[0]"/></td></tr>
                                        <tr><td><t t-out="value2[1]"/></td></tr>
                                        <tr><td><t t-out="value2[2]"/></td></tr>
                                    </table>
                                </td>
                            </tr>
                            <tr><td><t t-out="value[2]"/></td></tr>
                        </table>
                    </div>
                </t>
            """
        })
        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=True)

        # use same cache id, display the same content
        result = etree.fromstring(IrQweb._render(view1.id, {
            'cache_id': (1, 0),
            'cache_id2': (2, 0),
            'value': [1, 2, 3],
            'value2': [10, 20, 30]
        }))
        self.assertEqual(result, etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td>1</td></tr>
                    <tr>
                        <td>
                            <table>
                                <tr><td>10</td></tr>
                                <tr><td>20</td></tr>
                                <tr><td>30</td></tr>
                            </table>
                        </td>
                    </tr>
                    <tr><td>3</td></tr>
                </table>
            </div>
        """), 'First rendering')

        result = etree.fromstring(self.env['ir.qweb']._render(view1.id, {
            'cache_id': (1, 0),
            'cache_id2': (2, 1),
            'value': [41, 42, 43],
            'value2': [51, 52, 53]
        }))
        self.assertEqual(result, etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td>41</td></tr>
                    <tr>
                        <td>
                            <table>
                                <tr><td>51</td></tr>
                                <tr><td>52</td></tr>
                                <tr><td>53</td></tr>
                            </table>
                        </td>
                    </tr>
                    <tr><td>43</td></tr>
                </table>
            </div>
        """), 'Next rendering cannot use cache (use_qweb_t_cache is False)')

        result = etree.fromstring(self.env['ir.qweb']._render(view1.id, {
            'cache_id': (1, 1),
            'cache_id2': (2, 0),
            'value': [31, 32, 33],
            'value2': [51, 52, 53]
        }))
        self.assertEqual(result, etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td>31</td></tr>
                    <tr>
                        <td>
                            <table>
                                <tr><td>51</td></tr>
                                <tr><td>52</td></tr>
                                <tr><td>53</td></tr>
                            </table>
                        </td>
                    </tr>
                    <tr><td>33</td></tr>
                </table>
            </div>
        """), 'Third rendering cannot use cache (use_qweb_t_cache is False)')

    def test_render_xml_nocache_use_the_cached_values(self):
        """ The values set in the cached content are kept for the t-nocache. """
        template_page = self.env['ir.ui.view'].create({
            'name': "template_page",
            'type': 'qweb',
            'arch': """
                <t t-name="template_page">
                    <section t-cache="cache_id">
                        <t t-set="counter" t-value="counter + 100"/>
                        <article t-nocache=""><t t-out="counter"/></article>
                        <div>cache: <t t-out="counter"/></div>
                    </section>
                </t>
            """
        })

        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=False)

        render = IrQweb._render(template_page.id, {
            'cache_id': 1,
            'counter': 1,
        })
        result = """
            <section>
                <article>101</article>
                <div>cache: 101</div>
            </section>
        """
        self.assertEqual(etree.fromstring(render), etree.fromstring(result), 'rendering 1')

        render = IrQweb._render(template_page.id, {
            'cache_id': 1,
            'counter': 2,
        })
        result = """
            <section>
                <article>101</article>
                <div>cache: 101</div>
            </section>
        """
        self.assertEqual(etree.fromstring(render), etree.fromstring(result), 'rendering 2 (101: the t-set value is kept in cache)')

        render = IrQweb._render(template_page.id, {
            'cache_id': 3,
            'counter': 3,
        })
        result = """
            <section>
                <article>103</article>
                <div>cache: 103</div>
            </section>
        """
        self.assertEqual(etree.fromstring(render), etree.fromstring(result), 'rendering 3 (new cache key)')

    def test_render_xml_nocache_use_the_root_values_and_cached_values(self):
        template_page = self.env['ir.ui.view'].create({
            'name': "template_page",
            'type': 'qweb',
            'arch': """
                <t t-name="template_page">
                    <section t-cache="cache_id">
                        <t t-set="counter" t-value="counter + 100"/>
                        <article t-nocache="" t-nocache-counter="counter"><t t-out="counter"/></article>
                        <div>cache: <t t-out="counter"/></div>
                    </section>
                </t>
            """
        })

        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=False)

        render = IrQweb._render(template_page.id, {
            'cache_id': 1,
            'counter': 1,
        })
        result = """
            <section>
                <article>101</article>
                <div>cache: 101</div>
            </section>
        """
        self.assertEqual(etree.fromstring(render), etree.fromstring(result), 'rendering 1 (1 != 101: new cached values should be add to the root rendering)')

        render = IrQweb._render(template_page.id, {
            'cache_id': 1,
            'counter': 2,
        })
        result = """
            <section>
                <article>101</article>
                <div>cache: 101</div>
            </section>
        """
        self.assertEqual(etree.fromstring(render), etree.fromstring(result), 'rendering 2 (102 != 2: cached values should be used)')

        render = IrQweb._render(template_page.id, {
            'cache_id': 3,
            'counter': 3,
        })
        result = """
            <section>
                <article>103</article>
                <div>cache: 103</div>
            </section>
        """
        self.assertEqual(etree.fromstring(render), etree.fromstring(result), 'rendering 3 (3 != 103: new cached values should be add to the root rendering)')

    def test_render_xml_nocache_use_the_root_values_and_cached_values_error(self):
        template_page = self.env['ir.ui.view'].create({
            'name': "template_page",
            'type': 'qweb',
            'arch': """
                <t t-name="template_page">
                    <section t-cache="cache_id">
                        <article t-nocache="" t-nocache-record="view_record"><t t-out="view_record"/></article>
                    </section>
                </t>
            """
        })

        with self.assertRaisesRegex(QWebError, "The value type of 't-nocache-record' cannot be cached"):
            self.env['ir.qweb'].with_context(is_t_cache_disabled=False)._render(template_page.id, {
                'cache_id': 1,
                'view_record': self.env['ir.ui.view'].search([], limit=1),
            })

    def test_render_xml_cache_with_t_set_out_of_cache(self):
        template_page = self.env['ir.ui.view'].create({
            'name': "template_page",
            'type': 'qweb',
            'arch': """
                <t t-name="template_page">
                    <root>
                        <t t-set="counter" t-value="counter + 100"/>
                        <section t-cache="cache_id">
                            <article t-nocache=""><t t-out="counter"/></article>
                            <div>cache: <t t-out="counter"/></div>
                        </section>
                    </root>
                </t>
            """
        })

        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=False)

        render = IrQweb._render(template_page.id, {
            'cache_id': 1,
            'counter': 1,
        })
        result = """
            <root>
                <section>
                    <article>101</article>
                    <div>cache: 101</div>
                </section>
            </root>
        """
        self.assertEqual(etree.fromstring(render), etree.fromstring(result), 'rendering 1')

        render = IrQweb._render(template_page.id, {
            'cache_id': 1,
            'counter': 2,
        })
        result = """
            <root>
                <section>
                    <article>102</article>
                    <div>cache: 101</div>
                </section>
            </root>
        """
        self.assertEqual(etree.fromstring(render), etree.fromstring(result), 'rendering 2 (102: the values out of the t-cache are always up-to-date)')

        render = IrQweb._render(template_page.id, {
            'cache_id': 3,
            'counter': 3,
        })
        result = """
            <root>
                <section>
                    <article>103</article>
                    <div>cache: 103</div>
                </section>
            </root>
        """
        self.assertEqual(etree.fromstring(render), etree.fromstring(result), 'rendering 3 (new cache key)')

    def test_render_xml_cache_with_t_set_in_cache(self):
        template_page = self.env['ir.ui.view'].create({
            'name': "template_page",
            'type': 'qweb',
            'arch': """
                <t t-name="template_page">
                    <root>
                        <section t-cache="cache_id">
                            <t t-set="counter" t-value="counter + 100"/>
                            <article t-nocache=""><t t-out="counter"/></article>
                            <div>cache: <t t-out="counter"/></div>
                        </section>
                        <div>out of cache: <t t-out="counter"/></div>
                    </root>
                </t>
            """
        })
        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=False)

        render = IrQweb._render(template_page.id, {
            'cache_id': 1,
            'counter': 1,
        })
        result = """
            <root>
                <section>
                    <article>101</article>
                    <div>cache: 101</div>
                </section>
                <div>out of cache: 1</div>
            </root>
        """
        self.assertEqual(etree.fromstring(render), etree.fromstring(result), 'rendering 1')

        render = IrQweb._render(template_page.id, {
            'cache_id': 1,
            'counter': 2,
        })
        result = """
            <root>
                <section>
                    <article>101</article>
                    <div>cache: 101</div>
                </section>
                <div>out of cache: 2</div>
            </root>
        """
        self.assertEqual(etree.fromstring(render), etree.fromstring(result), 'rendering 2')

        render = IrQweb._render(template_page.id, {
            'cache_id': 3,
            'counter': 3,
        })
        result = """
            <root>
                <section>
                    <article>103</article>
                    <div>cache: 103</div>
                </section>
                <div>out of cache: 3</div>
            </root>
        """
        self.assertEqual(etree.fromstring(render), etree.fromstring(result), 'rendering 3')

    def test_render_xml_cache_with_t_set_wrap_t_cache(self):
        template_page = self.env['ir.ui.view'].create({
            'name': "template_page",
            'type': 'qweb',
            'arch': """
                <t t-name="template_page">
                    <cache_1 t-cache="cache_1">
                        <t t-set="a">
                            <cache_2 t-cache="cache_2">
                                <t t-set="counter" t-value="counter + 100"/>
                                <nocache t-nocache="" class="no_cache"><t t-out="counter"/></nocache>
                                <div>cache: <t t-out="counter"/></div>
                            </cache_2>
                            <nocache t-nocache="" class="no_cache"><t t-out="counter * 10"/></nocache>
                        </t>
                        <div>
                            <t t-out="a"/>
                        </div>
                    </cache_1>
                </t>
            """
        })
        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=False)

        render = IrQweb._render(template_page.id, {
            'cache_1': 1,
            'cache_2': 1,
            'counter': 1,
        })
        result = """
            <cache_1>
                <div>
                    <cache_2>
                        <nocache class="no_cache">101</nocache>
                        <div>cache: 101</div>
                    </cache_2>
                    <nocache class="no_cache">10</nocache>
                </div>
            </cache_1>
        """
        self.assertEqual(etree.fromstring(render), etree.fromstring(result), 'rendering 1')

        render = IrQweb._render(template_page.id, {
            'cache_1': 2,
            'cache_2': 1,
            'counter': 2,
        })
        result = """
            <cache_1>
                <div>
                    <cache_2>
                        <nocache class="no_cache">101</nocache>
                        <div>cache: 101</div>
                    </cache_2>
                    <nocache class="no_cache">20</nocache>
                </div>
            </cache_1>
        """
        self.assertEqual(etree.fromstring(render), etree.fromstring(result), 'rendering 2')

        # the t-nocache are always rendered, even in a t-set of a t-cache
        render = IrQweb._render(template_page.id, {
            'cache_1': 2,
            'cache_2': 3,
            'counter': 3,
        })
        result = """
            <cache_1>
                <div>
                    <cache_2>
                        <nocache class="no_cache">101</nocache>
                        <div>cache: 101</div>
                    </cache_2>
                    <nocache class="no_cache">30</nocache>
                </div>
            </cache_1>
        """
        self.assertEqual(etree.fromstring(render), etree.fromstring(result), 'rendering 3')

        render = IrQweb._render(template_page.id, {
            'cache_1': 3,
            'cache_2': 3,
            'counter': 3,
        })
        result = """
            <cache_1>
                <div>
                    <cache_2>
                        <nocache class="no_cache">103</nocache>
                        <div>cache: 103</div>
                    </cache_2>
                    <nocache class="no_cache">30</nocache>
                </div>
            </cache_1>
        """
        self.assertEqual(etree.fromstring(render), etree.fromstring(result), 'rendering 4')

    def test_render_xml_t_set_wrap_t_cache(self):
        template_page = self.env['ir.ui.view'].create({
            'name': "template_page",
            'type': 'qweb',
            'arch': """
                <t t-name="template_page">
                    <root>
                        <t t-set="a">
                            <section t-cache="cache_id">
                                <t t-set="counter" t-value="counter + 100"/>
                                <article t-nocache="" class="no_cache"><t t-out="counter"/></article>
                                <div>cache: <t t-out="counter"/></div>
                            </section>
                            <footer t-nocache="" class="no_cache"><t t-out="counter * 10"/></footer>
                        </t>
                        <div>
                            <t t-out="a"/>
                        </div>
                    </root>
                </t>
            """
        })
        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=False)

        render = IrQweb._render(template_page.id, {
            'cache_id': 1,
            'counter': 1,
        })
        result = """
            <root>
                <div>
                    <section>
                        <article class="no_cache">101</article>
                        <div>cache: 101</div>
                    </section>
                    <footer class="no_cache">10</footer>
                </div>
            </root>
        """
        self.assertEqual(etree.fromstring(render), etree.fromstring(result), 'rendering 1')

        render = IrQweb._render(template_page.id, {
            'cache_id': 1,
            'counter': 2,
        })
        result = """
            <root>
                <div>
                    <section>
                        <article class="no_cache">101</article>
                        <div>cache: 101</div>
                    </section>
                    <footer class="no_cache">20</footer>
                </div>
            </root>
        """
        self.assertEqual(etree.fromstring(render), etree.fromstring(result), 'rendering 2')

        render = IrQweb._render(template_page.id, {
            'cache_id': 3,
            'counter': 3,
        })
        result = """
            <root>
                <div>
                    <section>
                        <article class="no_cache">103</article>
                        <div>cache: 103</div>
                    </section>
                    <footer class="no_cache">30</footer>
                </div>
            </root>
        """
        self.assertEqual(etree.fromstring(render), etree.fromstring(result), 'rendering 3')

    def test_render_xml_nocache_in_cache_in_cache(self):
        template_page = self.env['ir.ui.view'].create({
            'name': "template_page",
            'type': 'qweb',
            'arch': """
                <t t-name="template_page">
                    <root>
                        <section t-cache="key1">
                            <span t-out="val"/>
                            <article t-cache="key2">
                                <span t-nocache="" t-out="val"/>
                            </article>
                        </section>
                    </root>
                </t>
            """
        })

        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=False)

        render = IrQweb._render(template_page.id, {
            'key1': (1,),
            'key2': (1,),
            'val': 1,
        })
        result = """
            <root>
                <section>
                    <span>1</span>
                    <article>
                        <span>1</span>
                    </article>
                </section>
            </root>
        """
        self.assertEqual(etree.fromstring(render), etree.fromstring(result), 'rendering 1')

        render = IrQweb._render(template_page.id, {
            'key1': (1,),
            'key2': (1,),
            'val': 2,
        })
        result = """
            <root>
                <section>
                    <span>1</span>
                    <article>
                        <span>2</span>
                    </article>
                </section>
            </root>
        """
        self.assertEqual(etree.fromstring(render), etree.fromstring(result), 'rendering 2')

        render = IrQweb._render(template_page.id, {
            'key1': (1,),
            'key2': (2,),
            'val': 3,
        })
        result = """
            <root>
                <section>
                    <span>1</span>
                    <article>
                        <span>3</span>
                    </article>
                </section>
            </root>
        """
        self.assertEqual(etree.fromstring(render), etree.fromstring(result), 'rendering 3')

    def test_render_xml_nocache_in_nocache(self):
        template_page = self.env['ir.ui.view'].create({
            'name': "template_page",
            'type': 'qweb',
            'arch': """
                <t t-name="template_page">
                    <cache_a t-cache="cache_a">
                        <t t-set="counter" t-value="counter + 100"/>(counter + 100)
                        <t t-out="counter"/>
                        <nocache t-nocache="wrap cache_b">
                            <t t-set="counter" t-value="counter + 10"/>(counter + 10)
                            <t t-out="counter"/>
                            <cache_b t-cache="cache_b">
                                <t t-out="counter"/>
                                <nocache_value t-nocache="" t-nocache-a="counter"><t t-out="a"/></nocache_value>
                                <nocache t-nocache=""><t t-out="counter"/></nocache>
                            </cache_b>
                        </nocache>
                    </cache_a>
                </t>
            """
        })

        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=False)

        render = IrQweb._render(template_page.id, {
            'cache_a': 1,
            'cache_b': 1,
            'counter': 1,
        })
        result = """
            <cache_a>(counter + 100)
                101
                <nocache>(counter + 10)
                    111
                    <cache_b>
                        111
                        <nocache_value>111</nocache_value>
                        <nocache>111</nocache>
                    </cache_b>
                </nocache>
            </cache_a>
        """
        self.assertEqual(dedent(str(render)).strip(), dedent(result).strip())

        render = IrQweb._render(template_page.id, {
            'cache_a': 1,
            'cache_b': 1,
            'counter': 2,
        })
        result = """
            <cache_a>(counter + 100)
                101
                <nocache>(counter + 10)
                    111
                    <cache_b>
                        111
                        <nocache_value>111</nocache_value>
                        <nocache>111</nocache>
                    </cache_b>
                </nocache>
            </cache_a>
        """
        self.assertEqual(dedent(str(render)).strip(), dedent(result).strip())

        render = IrQweb._render(template_page.id, {
            'cache_a': 1,
            'cache_b': 2,
            'counter': 3,
        })
        result = """
            <cache_a>(counter + 100)
                101
                <nocache>(counter + 10)
                    111
                    <cache_b>
                        111
                        <nocache_value>111</nocache_value>
                        <nocache>111</nocache>
                    </cache_b>
                </nocache>
            </cache_a>
        """
        self.assertEqual(dedent(str(render)).strip(), dedent(result).strip())

        render = IrQweb._render(template_page.id, {
            'cache_a': 2,
            'cache_b': 2,
            'counter': 4,
        })
        result = """
            <cache_a>(counter + 100)
                104
                <nocache>(counter + 10)
                    114
                    <cache_b>
                        111
                        <nocache_value>111</nocache_value>
                        <nocache>114</nocache>
                    </cache_b>
                </nocache>
            </cache_a>
        """
        self.assertEqual(dedent(str(render)).strip(), dedent(result).strip())

    def test_render_xml_nocache_alone(self):
        """ t-nocache without any parented t-cache is ignored"""
        template_page = self.env['ir.ui.view'].create({
            'name': "template_page",
            'type': 'qweb',
            'arch': """
                <t t-name="template_page">
                    <section>
                        <t t-set="counter" t-value="counter + 100"/>
                        <t t-out="counter"/>
                        <nocache t-nocache="">
                            <t t-set="counter" t-value="counter + 10"/>
                            <t t-out="counter"/>
                        </nocache>
                        <t t-out="counter"/>
                        <nocache_value t-nocache="" t-nocache-a="counter"><t t-out="a"/></nocache_value>
                        <nocache t-nocache=""><t t-out="counter"/></nocache>
                    </section>
                </t>
            """
        })

        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=False)

        render = IrQweb._render(template_page.id, {
            'counter': 1,
        })
        result = """
            <section>
                101
                <nocache>
                    111
                </nocache>
                111
                <nocache_value>111</nocache_value>
                <nocache>111</nocache>
            </section>
        """
        self.assertEqual(dedent(str(render)).strip(), dedent(result).strip())

        render = IrQweb._render(template_page.id, {
            'counter': 2,
        })
        result = """
            <section>
                102
                <nocache>
                    112
                </nocache>
                112
                <nocache_value>112</nocache_value>
                <nocache>112</nocache>
            </section>
        """
        self.assertEqual(dedent(str(render)).strip(), dedent(result).strip())

    def test_render_xml_nocache_in_t_call_simple(self):
        self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'key': 'base.testing_callee',
            'arch_db': '''
                        <nocache t-nocache="">
                            <cache_b t-cache="cache_b">
                                <div><t t-out="counter"/></div>
                                <nocache_value t-nocache="" t-nocache-a="counter"><t t-out="a"/></nocache_value>
                                <nocache t-nocache=""><t t-out="counter"/></nocache>
                            </cache_b>
                        </nocache>
            '''
        })
        template_page = self.env['ir.ui.view'].create({
            'name': "template_page",
            'type': 'qweb',
            'key': 'base.testing_page',
            'arch': """
                <t t-name="template_page">
                    <cache_a t-cache="cache_a">
                        <t t-set="counter" t-value="counter + 100"/>
                        <div><t t-out="counter"/></div>
                        <t t-call="base.testing_callee"/>
                    </cache_a>
                </t>
            """
        })

        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=False)

        render = IrQweb._render(template_page.id, {
            'cache_a': 1,
            'cache_b': 1,
            'counter': 1,
        })
        result = """
            <cache_a>
                <div>101</div><nocache>
                    <cache_b>
                        <div>101</div>
                        <nocache_value>101</nocache_value>
                        <nocache>101</nocache>
                    </cache_b>
                </nocache>
            </cache_a>
        """
        self.assertEqual(dedent(str(render)).strip(), dedent(result).strip())

        render = IrQweb._render(template_page.id, {
            'cache_a': 1,
            'cache_b': 1,
            'counter': 2,
        })
        result = """
            <cache_a>
                <div>101</div><nocache>
                    <cache_b>
                        <div>101</div>
                        <nocache_value>101</nocache_value>
                        <nocache>101</nocache>
                    </cache_b>
                </nocache>
            </cache_a>
        """
        self.assertEqual(dedent(str(render)).strip(), dedent(result).strip())

        render = IrQweb._render(template_page.id, {
            'cache_a': 1,
            'cache_b': 2,
            'counter': 3,
        })
        result = """
            <cache_a>
                <div>101</div><nocache>
                    <cache_b>
                        <div>101</div>
                        <nocache_value>101</nocache_value>
                        <nocache>101</nocache>
                    </cache_b>
                </nocache>
            </cache_a>
        """
        self.assertEqual(dedent(str(render)).strip(), dedent(result).strip())

        render = IrQweb._render(template_page.id, {
            'cache_a': 2,
            'cache_b': 2,
            'counter': 4,
        })
        result = """
            <cache_a>
                <div>104</div><nocache>
                    <cache_b>
                        <div>101</div>
                        <nocache_value>101</nocache_value>
                        <nocache>104</nocache>
                    </cache_b>
                </nocache>
            </cache_a>
        """
        self.assertEqual(dedent(str(render)).strip(), dedent(result).strip())

    def test_render_xml_nocache_in_t_call(self):
        self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'key': 'base.testing_callee_1',
            'arch_db': '''<nocache_value t-nocache="" t-nocache-a="counter">cache:<t t-out="a"/> val:<t t-out="val"/></nocache_value>'''
        })
        self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'key': 'base.testing_callee_2',
            'arch_db': '''<nocache t-nocache=""><t t-out="counter"/></nocache>'''
        })
        self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'key': 'base.testing_callee',
            'arch_db': '''
                        <nocache t-nocache="">
                            <cache_b t-cache="cache_b">
                                <t t-out="counter"/>
                                <t t-call="base.testing_callee_1"/>
                                <t t-call="base.testing_callee_2"/>
                            </cache_b>
                        </nocache>
            '''
        })
        template_page = self.env['ir.ui.view'].create({
            'name': "template_page",
            'type': 'qweb',
            'key': 'base.testing_page',
            'arch': """
                <t t-name="template_page">
                    <cache_a t-cache="cache_a">
                        <t t-set="counter" t-value="counter + 100"/>
                        <t t-out="counter"/>
                        <t t-call="base.testing_callee"/>
                    </cache_a>
                </t>
            """
        })

        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=False)

        render = IrQweb._render(template_page.id, {
            'cache_a': 1,
            'cache_b': 1,
            'counter': 1,
            'val': 1,
        })
        result = """
            <cache_a>
                101<nocache>
                    <cache_b>
                        101<nocache_value>cache:101 val:1</nocache_value><nocache>101</nocache>
                    </cache_b>
                </nocache>
            </cache_a>
        """
        self.assertEqual(dedent(str(render)).strip(), dedent(result).strip())

        render = IrQweb._render(template_page.id, {
            'cache_a': 1,
            'cache_b': 1,
            'counter': 2,
            'val': 2,
        })
        result = """
            <cache_a>
                101<nocache>
                    <cache_b>
                        101<nocache_value>cache:101 val:2</nocache_value><nocache>101</nocache>
                    </cache_b>
                </nocache>
            </cache_a>
        """
        self.assertEqual(dedent(str(render)).strip(), dedent(result).strip())

        render = IrQweb._render(template_page.id, {
            'cache_a': 1,
            'cache_b': 2,
            'counter': 3,
            'val': 3,
        })
        result = """
            <cache_a>
                101<nocache>
                    <cache_b>
                        101<nocache_value>cache:101 val:3</nocache_value><nocache>101</nocache>
                    </cache_b>
                </nocache>
            </cache_a>
        """
        self.assertEqual(dedent(str(render)).strip(), dedent(result).strip())

        render = IrQweb._render(template_page.id, {
            'cache_a': 2,
            'cache_b': 2,
            'counter': 4,
            'val': 4,
        })
        result = """
            <cache_a>
                104<nocache>
                    <cache_b>
                        101<nocache_value>cache:101 val:4</nocache_value><nocache>104</nocache>
                    </cache_b>
                </nocache>
            </cache_a>
        """
        self.assertEqual(dedent(str(render)).strip(), dedent(result).strip())

    def test_render_xml_nocache_in_t_call_0(self):
        self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'key': 'base.testing_callee',
            'arch_db': '<callee><t t-out="0"/></callee>'
        })
        template_page = self.env['ir.ui.view'].create({
            'name': "template_page",
            'type': 'qweb',
            'key': 'base.testing_page',
            'arch': """
                <t t-name="template_page">
                    <t t-set="counter" t-value="counter + 100"/>
                    <cache t-cache="cache_a">
                        <t t-call="base.testing_callee">
                            <counter><t t-out="counter"/></counter>
                            <nocache><t t-nocache="" t-out="counter"/></nocache>
                        </t>
                    </cache>
                </t>
            """
        })

        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=False)

        render = IrQweb._render(template_page.id, {
            'cache_a': 1,
            'counter': 1,
        })

        result = """
            <cache><callee>
                    <counter>101</counter>
                    <nocache>101</nocache>
                </callee>
            </cache>
        """
        self.assertEqual(dedent(str(render)).strip(), dedent(result).strip())

        render = IrQweb._render(template_page.id, {
            'cache_a': 1,
            'counter': 2,
        })
        result = """
            <cache><callee>
                    <counter>101</counter>
                    <nocache>102</nocache>
                </callee>
            </cache>
        """
        self.assertEqual(dedent(str(render)).strip(), dedent(result).strip())

        render = IrQweb._render(template_page.id, {
            'cache_a': 2,
            'counter': 3,
        })
        result = """
            <cache><callee>
                    <counter>103</counter>
                    <nocache>103</nocache>
                </callee>
            </cache>
        """
        self.assertEqual(dedent(str(render)).strip(), dedent(result).strip())

    def test_render_xml_conditional_cache(self):
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">
                    <div t-cache="cache_id if condition else None" class="toto">
                        <table>
                            <tr><td><span t-out="value[0]"/></td></tr>
                            <tr><td><span t-out="value[1]"/></td></tr>
                            <tr><td><span t-out="value[2]"/></td></tr>
                        </table>
                    </div>
                </t>
            """
        })
        expected_result = etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td><span>1</span></td></tr>
                    <tr><td><span>2</span></td></tr>
                    <tr><td><span>3</span></td></tr>
                </table>
            </div>
        """)

        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=False)

        result = etree.fromstring(IrQweb._render(view1.id, {'cache_id': 1, 'condition': True, 'value': [1, 2, 3]}))
        self.assertEqual(result, expected_result, 'First rendering (add in cache)')

        result = etree.fromstring(IrQweb._render(view1.id, {'cache_id': 1, 'condition': True, 'value': [10, 20, 30]}))
        self.assertEqual(result, expected_result, 'Next rendering use cache')


        expected_result = etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td><span>10</span></td></tr>
                    <tr><td><span>20</span></td></tr>
                    <tr><td><span>30</span></td></tr>
                </table>
            </div>
        """)
        result = etree.fromstring(IrQweb._render(view1.id, {'cache_id': 1, 'value': [10, 20, 30]}))
        self.assertEqual(result, expected_result, 'Next rendering use cache')

    def test_render_xml_cache_and_inherit_view(self):
        view1 = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">
                    <div t-cache="True" class="toto">
                        <table>
                            <tr><td><span t-out="value[0]"/></td></tr>
                            <tr><td><span t-out="value[1]"/></td></tr>
                            <tr><td><span t-out="value[2]"/></td></tr>
                        </table>
                    </div>
                </t>
            """
        })
        # t-cache value can be an interable then we can add value as a tuple (without parenthesis)
        view2 = self.env['ir.ui.view'].create({
            'name': 'Child View',
            'mode': 'extension',
            'inherit_id': view1.id,
            'arch': '''
                <xpath expr="//div[@t-cache]" position="attributes">
                    <attribute name="t-cache" add="company,value[0]" remove="True," separator=","/>
                </xpath>
            ''',
        })

        IrQweb = self.env['ir.qweb'].with_context(use_qweb_t_cache=True)

        expected_result = etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td><span>1</span></td></tr>
                    <tr><td><span>2</span></td></tr>
                    <tr><td><span>3</span></td></tr>
                </table>
            </div>
        """)
        result = etree.fromstring(IrQweb._render(view2.id, {'value': [1, 2, 3]}))
        self.assertEqual(result, expected_result, 'First rendering create cache from company and the value 1')

        expected_result = etree.fromstring("""
            <div class="toto">
                <table>
                    <tr><td><span>10</span></td></tr>
                    <tr><td><span>20</span></td></tr>
                    <tr><td><span>30</span></td></tr>
                </table>
            </div>
        """)
        result = etree.fromstring(IrQweb._render(view2.id, {'value': [10, 20, 30]}))
        self.assertEqual(result, expected_result, 'Next rendering create cache from company and the value 10')

    def test_render_nodb(self):
        """ Render an html page without db ans wihtout registry
        """
        expected = dedent("""
            <html>
                <head>
                    <title>Odoo</title>
                </head>
                <body>
                    <section class="toto">
                        <div>3</div>
                    </section>
                </body>
            </html>
        """).strip()

        templates = {
            'html': html.document_fromstring("""
                <html t-name="html">
                    <head>
                        <title>Odoo</title>
                    </head>
                    <body>
                        <section class="toto">
                            <t t-call="content"/>
                        </section>
                    </body>
                </html>
            """),
            'content': html.fragment_fromstring("""
                <t t-name="content">
                        <div><t t-out="val"/></div>
                </t>
            """)
        }
        def load(template_name):
            return (templates[template_name], template_name)
        rendering = render('html', {'val': 3}, load).strip()

        self.assertEqual(html.document_fromstring(rendering), html.document_fromstring(expected))

    def test_render_xml_cache_record_key_not_invalidated(self):
        """ The record modifications don't invalidate the cache, it must be
        reset (e.g. with the "Reset Cache" button of the website settings). """
        view = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """<t t-name="base.dummy"><div t-cache="partner" t-out="partner.name"/></t>""",
        })
        partner = self.env['res.partner'].create({'name': 'Before'})
        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=False)

        self.assertEqual(str(IrQweb._render(view.id, {'partner': partner})), '<div>Before</div>')
        partner.name = 'After'
        self.assertEqual(str(IrQweb._render(view.id, {'partner': partner})), '<div>Before</div>', 'the cache is not up-to-date')

        self.env.transaction.invalidate_ormcache('templates')
        self.assertEqual(str(IrQweb._render(view.id, {'partner': partner})), '<div>After</div>', 'the cache is reset')

        IrQweb = IrQweb.with_context(is_t_cache_disabled=True)
        partner.name = 'Disabled'
        self.assertEqual(str(IrQweb._render(view.id, {'partner': partner})), '<div>Disabled</div>')

    def test_render_xml_show_t_cache(self):
        view = self.env['ir.ui.view'].create({
            'name': "dummy",
            'type': 'qweb',
            'arch': """
                <t t-name="base.dummy">
                    <section t-cache="cache_id"><span t-nocache="" t-out="value"/></section>
                    <article t-cache="None"/>
                </t>""",
        })
        IrQweb = self.env['ir.qweb'].with_context(is_t_cache_disabled=False, show_t_cache=True)
        for value in (1, 2):
            render = IrQweb._render(view.id, {'cache_id': 1, 'value': value})
            root = html.fromstring(f'<div>{render}</div>')
            self.assertEqual(root.xpath('//section/@data-oe-t-cache-zone'), ['t-cache'])
            self.assertIn('miss' if value == 1 else 'hit', root.xpath('//section/@title')[0])
            self.assertEqual(root.xpath('//span/@data-oe-t-cache-zone'), ['t-nocache'])
            self.assertEqual(root.xpath('//span/text()'), [str(value)])
            self.assertEqual(root.xpath('//article/@data-oe-t-cache-zone'), ['t-cache-disabled'])

        # the zones are not displayed without the debug mode
        render = self.env['ir.qweb'].with_context(is_t_cache_disabled=False)._render(view.id, {'cache_id': 1, 'value': 3})
        self.assertNotIn('data-oe-t-cache-zone', render)

from lxml import etree

from odoo.addons.web_studio.controllers.keyed_xml_differ import (
    KeyedXmlDiffer,
    dedent_tree,
    indent_tree,
    diff_dicts,
    longest_increasing_subsequence,
)
from odoo.tests.common import TransactionCase
from odoo.tools.template_inheritance import apply_inheritance_specs


class TestXmlDiffer(TransactionCase):
    def test_attribute_diff(self):
        d1 = {"k": "v", "k2": "v2", "kignore": "ignore"}
        d2 = {"k": "v1", "kignore": "changed", "k3": "v3"}
        changes = diff_dicts(d1, d2, {"kignore"})
        self.assertEqual(changes, {
            "k": "v1",
            "k3": "v3",
            "k2": None,
        })

    def test_longest_increasing_sequence(self):
        self.assertEqual(longest_increasing_subsequence([]), [])
        self.assertEqual(longest_increasing_subsequence([8, 3, 4, 6, 5, 2, 0, 7, 9, 1]), [9, 7, 5, 4, 3])
        self.assertEqual(longest_increasing_subsequence([1, 3, 4, 2]), [4, 3, 1])
        self.assertEqual(longest_increasing_subsequence([4, 3, 2, 1]), [1])
        self.assertEqual(longest_increasing_subsequence([1, 2, 3, 4]), [4, 3, 2, 1])
        self.assertEqual(longest_increasing_subsequence([4, 2, 6, 3, 5]), [5, 3, 2])

        # longest_increasing_subsequence compares items on their value
        # in the case items are string: "11" < "2" == True
        # transforming an item to its value if necessary should be done before hand
        self.assertEqual(longest_increasing_subsequence(["11", "2", "3"]), ["3", "2", "11"])
        d1 = {
            "a": "3",
            "b": "13",
            "c": "1",
            "d": "2",
            "e": "14",
        }
        items = [(int(val), key) for key, val in d1.items()]
        self.assertEqual([key for val, key in longest_increasing_subsequence(items)], ["e", "d", "c"])

    def _standard_indent(self, str_arch):
        arch = etree.fromstring(str_arch)
        dedent_tree(arch)
        indent_tree(arch)
        return etree.tostring(arch)

    def _assertXpathDiffAndReapply(self, old, new, expected_arch_diff, differ_options=None, reapplied_arch=None):
        differ_options = {} if differ_options is None else differ_options
        differ = KeyedXmlDiffer(**differ_options)

        old = self._standard_indent(old)
        new = self._standard_indent(new)
        expected_arch_diff = self._standard_indent(expected_arch_diff)
        if reapplied_arch:
            reapplied_arch = self._standard_indent(reapplied_arch)

        arch = differ.diff_xpath(old, new)
        self.assertXMLEqual(arch, expected_arch_diff)

        reapplied = apply_inheritance_specs(etree.fromstring(old), etree.fromstring(arch))
        dedent_tree(reapplied)
        indent_tree(reapplied)

        self.assertXMLEqual(etree.tostring(reapplied), reapplied_arch or new)

    def test_diff_move(self):
        xml_old = """
            <div o-diff-key="0">
                <div o-diff-key="1" a="1">
                    <div o-diff-key="2" a="2"/>
                    <div o-diff-key="3" a="3"/>
                </div>
                <div o-diff-key="4">
                    <div o-diff-key="5" a="5"/>
                    <div o-diff-key="6" a="6" />
                </div>
            </div>
        """

        xml_new = """
            <div o-diff-key="0">
                <div o-diff-key="1" a="1">
                    <div o-diff-key="2" a="2"/>
                </div>
                <div o-diff-key="4">
                    <div o-diff-key="3" a="3"/>
                    <div o-diff-key="5" a="5"/>
                    <div o-diff-key="6" a="6" />
                </div>
            </div>
        """
        self._assertXpathDiffAndReapply(xml_old, xml_new, """
        <data>
          <data>
            <xpath position="before" expr="/div/div[2]/div">
              <xpath position="move" expr="/div/div/div[2]"/>
            </xpath>
          </data>
        </data>
        """)

        xml_new = """
            <div o-diff-key="0">
                <div o-diff-key="1" a="1"><div o-diff-key="5" a="5"/><div o-diff-key="2" a="2"/><div o-diff-key="3" a="3"/></div>
                <div o-diff-key="4"><div o-diff-key="6" a="6" /></div>
            </div>
        """
        self._assertXpathDiffAndReapply(xml_old, xml_new, """
        <data>
          <data>
            <xpath position="before" expr="/div/div/div">
              <xpath position="move" expr="/div/div[2]/div"/>
            </xpath>
          </data>
        </data>
        """)

    def test_move_from_removed(self):
        xml_old = """
            <div o-diff-key="0">
                <div o-diff-key="1" a="1">
                    <div o-diff-key="2" a="2"/>
                    <div o-diff-key="3" a="3"/>
                </div>
                <div o-diff-key="4">
                    <div o-diff-key="5" a="5"/>
                    <div o-diff-key="6" a="6" />
                </div>
            </div>
        """

        xml_new = """
            <div o-diff-key="0">
                <div o-diff-key="4">
                    <div o-diff-key="5" a="5"/>
                    <div o-diff-key="2" a="3"/>
                    <div o-diff-key="6" a="6" />
                </div>
            </div>
        """
        self._assertXpathDiffAndReapply(xml_old, xml_new, """
        <data>
            <data>
                <xpath position="after" expr="/div/div[2]/div">
                <xpath position="move" expr="/div/div/div"/>
                </xpath>
            </data>
            <data>
                <xpath position="attributes" expr="/div/div[2]/div[2]">
                <attribute name="a">3</attribute>
                </xpath>
            </data>
            <data>
                <xpath position="replace" expr="/div/div"/>
            </data>
        </data>
        """)

    def test_move_from_move(self):
        xml_old = """
            <div o-diff-key="0">
                <div o-diff-key="1" a="1">
                    <div o-diff-key="2" a="2"/>
                    <div o-diff-key="3" a="3"/>
                </div>
                <div o-diff-key="4">
                    <div o-diff-key="5" a="5"/>
                    <div o-diff-key="6" a="6" />
                </div>
            </div>
        """

        xml_new = """
            <div o-diff-key="0">
                <div o-diff-key="4">
                    <div o-diff-key="1" a="1">
                        <div o-diff-key="3" a="3"/>
                    </div>
                    <div o-diff-key="5" a="5"/>
                    <div o-diff-key="2" a="3"/>
                    <div o-diff-key="6" a="6" />
                </div>
            </div>
        """
        self._assertXpathDiffAndReapply(xml_old, xml_new, """
        <data>
           <data>
             <xpath position="before" expr="/div/div[2]/div">
               <xpath position="move" expr="/div/div"/>
             </xpath>
             <xpath position="after" expr="/div/div/div[2]">
               <xpath position="move" expr="/div/div/div/div"/>
             </xpath>
           </data>
           <data>
             <xpath position="attributes" expr="/div/div/div[3]">
               <attribute name="a">3</attribute>
             </xpath>
           </data>
        </data>
        """)

    def test_diff_inner_move(self):
        xml_old = """
            <div o-diff-key="0">
                <div o-diff-key="1" a="1">
                    <div o-diff-key="2" a="2"/>
                    <div o-diff-key="3" a="3"/>
                    <div o-diff-key="4" name="4"/>
                    <div o-diff-key="5" a="5"/>
                    <div o-diff-key="6" a="6" />
                </div>
            </div>
        """

        xml_new = """
            <div o-diff-key="0">
                <div o-diff-key="1" a="1">
                    <div o-diff-key="4" name="4"/>
                    <div o-diff-key="2" a="2"/>
                    <div o-diff-key="6" a="6"/>
                    <div o-diff-key="3" a="3"/>
                    <div o-diff-key="5" a="5"/>
                </div>
            </div>
        """
        self._assertXpathDiffAndReapply(xml_old, xml_new, """
        <data>
            <data>
                <xpath position="before" expr="/div/div/div">
                    <xpath position="move" expr="/div/div/div[@name='4']"/>
                </xpath>
                <xpath position="after" expr="/div/div/div[2]">
                    <xpath position="move" expr="/div/div/div[5]"/>
                </xpath>
            </data>
        </data>
        """)

    def test_text_replace(self):
        xml_old = """
        <div o-diff-key="0">
            <div o-diff-key="1">
                A
                <div o-diff-key="2" a="2"/>
                B
            </div>
        </div>
        """

        xml_new = """
        <div o-diff-key="0">
            <div o-diff-key="1">
                <div o-diff-key="2" a="2"/>
            </div>
        </div>
        """

        self._assertXpathDiffAndReapply(xml_old, xml_new, """
        <data>
            <data>
                <xpath position="inside" expr="/div/div">
                    <div o-diff-key="1"/>
                </xpath>
                <xpath expr="/div/div/div[2]" position="inside">
                    <xpath position="move" expr="/div/div/div"/>
                </xpath>
                <xpath position="replace" expr="/div/div">
                    <xpath expr="/div/div/div" position="move"/>
                </xpath>
            </data>
        </data>
        """)

    def test_text_replace2(self):
        xml_old = """
            <div o-diff-key="0">
              <div o-diff-key="1">
                A
                <div o-diff-key="2" a="2"/>
                B
              </div>
            </div>
        """

        xml_new = """
            <div o-diff-key="0">
              <div o-diff-key="1">
                AB
                <div o-diff-key="2" a="2"/>
                BC
              </div>
            </div>
        """

        self._assertXpathDiffAndReapply(xml_old, xml_new, """
        <data>
            <data>
                <xpath position="inside" expr="/div/div">
                    <div o-diff-key="1"/>
                </xpath>
                <xpath expr="/div/div/div[2]" position="inside">
                  AB
                  <xpath position="move" expr="/div/div/div"/>
                  BC
                </xpath>
                <xpath position="replace" expr="/div/div">
                    <xpath expr="/div/div/div" position="move"/>
                </xpath>
            </data>
        </data>
        """)

    def test_text_replace3(self):
        xml_old = """
        <div o-diff-key="0">
            <div o-diff-key="1">
                A
                <div o-diff-key="2" a="2"/>
                B
            </div>
        </div>
        """

        xml_new = """
        <div o-diff-key="0">
            <div o-diff-key="1">
            C
            </div>
        </div>
        """

        self._assertXpathDiffAndReapply(xml_old, xml_new, """
        <data>
          <data>
            <xpath position="replace" expr="/div/div">
              <div o-diff-key="1">C</div>
            </xpath>
          </data>
        </data>
        """)

    def test_replace_all(self):
        xml_old = """
        <div o-diff-key="0">
            <div o-diff-key="1" a="1">
                A
                <div o-diff-key="2" a="2">
                    <div o-diff-key="3" a="3" />
                </div>
                <div o-diff-key="4" a="4" />
                B
            </div>
            <div o-diff-key="5" a="5"/>
        </div>
        """

        xml_new = """
        <div o-diff-key="0">
            <div o-diff-key="1" a="changed">
                <div o-diff-key="2" a="2"/>
                C
                <h1>
                    <div o-diff-key="3" a="change3" />
                </h1>
                <div o-diff-key="5" a="5"/>
                B
            </div>
        </div>
        """
        self._assertXpathDiffAndReapply(xml_old, xml_new, """
        <data>
          <data>
            <xpath position="inside" expr="/div/div">
              <div o-diff-key="1" a="changed"/>
            </xpath>
            <xpath expr="/div/div/div[3]" position="inside">
              <xpath position="move" expr="/div/div/div"/>
              C
              <h1>
                <o-diff-hole for="3"/>
              </h1>
              <xpath position="move" expr="/div/div[2]"/>
              B
            </xpath>
            <xpath expr="/div/div//o-diff-hole[@for='3']" position="replace">
              <xpath position="move" expr="/div/div/div[2]/div/div"/>
            </xpath>
            <xpath position="replace" expr="/div/div">
              <xpath expr="/div/div/div[2]" position="move"/>
            </xpath>
          </data>
          <data>
            <xpath position="attributes" expr="/div/div/h1/div">
              <attribute name="a">change3</attribute>
            </xpath>
          </data>
        </data>
        """)

    def test_text_keep(self):
        xml_old = """
            <div o-diff-key="0">
                A
                <div o-diff-key="2" a="2"/>
                B
            </div>
        """

        xml_new = """
            <div o-diff-key="0">
                A<h1/>D
                <div o-diff-key="2" a="2"/>C<span/>
                B
            </div>
        """

        self._assertXpathDiffAndReapply(xml_old, xml_new, """
        <data>
            <data>
                <xpath position="before" expr="/div/div"><h1/>D</xpath>
                <xpath position="after" expr="/div/div">C<span/></xpath>
            </data>
        </data>
        """)

    def test_move_in_new(self):
        xml_old = """
            <div o-diff-key="0">
                <div o-diff-key="2" a="2"/>
            </div>
        """

        xml_new = """
            <div o-diff-key="0">
                <span>
                    <h1>
                        <div o-diff-key="2" a="7"/>
                    </h1>
                </span>
            </div>
        """
        reapplied_arch = """
            <div o-diff-key="0">
                <span is_new="true">
                    <h1 is_new="true">
                        <div o-diff-key="2" a="7"/>
                    </h1>
                </span>
            </div>
        """

        differ_options = {
            "on_new_node": lambda n: n.set("is_new", "true"),
        }

        self._assertXpathDiffAndReapply(xml_old, xml_new, """
        <data>
            <data>
                <xpath position="inside" expr="/div">
                    <span is_new="true">
                        <h1 is_new="true">
                            <o-diff-hole for="2"/>
                        </h1>
                    </span>
                </xpath>
                <xpath expr="/div//o-diff-hole[@for='2']" position="replace">
                    <xpath position="move" expr="/div/div"/>
                </xpath>
            </data>
            <data>
                <xpath position="attributes" expr="/div/span/h1/div">
                    <attribute name="a">7</attribute>
                </xpath>
            </data>
        </data>
        """, differ_options=differ_options, reapplied_arch=reapplied_arch)

    def test_all_descendants_xpath(self):
        xml_old = """
        <form o-diff-key="0">
            <field name="display_name" o-diff-key="1"/>
            <field name="name" o-diff-key="2" />
            <field name="some_ids" o-diff-key="3">
                <form o-diff-key="4">
                    <div o-diff-key="5" ><field name="display_name" o-diff-key="6" /></div>
                    <notebook o-diff-key="7"/>
                </form>
            </field>
        </form>
        """

        xml_new = """
        <form o-diff-key="0">
            <field name="display_name" o-diff-key="1"/>
            <field name="name" o-diff-key="2" />
            <field name="some_ids" o-diff-key="3">
                <form o-diff-key="4">
                    <div o-diff-key="5" ></div>
                    <notebook o-diff-key="7">
                        <field name="display_name" o-diff-key="6" />
                    </notebook>
                </form>
            </field>
        </form>
        """

        differ_options = {
            "is_subtree": lambda n: n.tag in ("form", "field") and n.getparent() is not None,
        }

        self._assertXpathDiffAndReapply(xml_old, xml_new, """
        <data>
            <data>
                <xpath position="inside" expr=".//field[@name='some_ids']/form/notebook">
                    <xpath position="move" expr=".//field[@name='some_ids']/form//field[@name='display_name']"/>
                </xpath>
            </data>
        </data>""", differ_options=differ_options)

    def test_with_meta(self):
        xml_old = """
        <div o-diff-key="1">
            <div o-diff-key="2" class="some-class" />
            <div o-diff-key="3" class="some-class2">
                <div o-diff-key="4" a="3" class="some-class3" name="name"/>
                <div o-diff-key="5"/>
                <div o-diff-key="6" class="some-class4"/>
            </div>
            <div o-diff-key="7" class="some-class5"/>
        </div>
        """

        xml_new = """
        <div o-diff-key="1">
            <div o-diff-key="3">
                <div o-diff-key="4" a="4"/>
                <div o-diff-key="6"/>
                <div o-diff-key="5"/>
            </div>
            <div o-diff-key="7">
                <span>new</span>
            </div>
        </div>
        """

        differ_options = {
            "xpath_with_meta": True
        }

        expected_arch = """
        <data>
          <data>
            <xpath position="replace" expr="/div/div" meta-class="some-class"/>
          </data>
          <data>
            <xpath position="after" expr="/div/div/div[@name='name']" meta-a="3" meta-class="some-class3" meta-name="name">
              <xpath position="move" expr="/div/div/div[3]" meta-class="some-class4"/>
            </xpath>
            <xpath position="attributes" expr="/div/div" meta-class="some-class2">
              <attribute name="class"/>
            </xpath>
          </data>
          <data>
            <xpath position="attributes" expr=".//div[@name='name']" meta-a="3" meta-class="some-class3" meta-name="name">
              <attribute name="a">4</attribute>
              <attribute name="class"/>
              <attribute name="name"/>
            </xpath>
          </data>
          <data>
            <xpath position="attributes" expr="/div/div/div[2]" meta-class="some-class4">
              <attribute name="class"/>
            </xpath>
          </data>
          <data>
            <xpath position="inside" expr="/div/div[2]" meta-class="some-class5">
              <span>new</span>
            </xpath>
            <xpath position="attributes" expr="/div/div[2]" meta-class="some-class5">
              <attribute name="class"/>
            </xpath>
          </data>
        </data>
        """
        self._assertXpathDiffAndReapply(xml_old, xml_new, expected_arch, differ_options=differ_options)

import random
import textwrap
from odoo.http import _request_stack
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import DotDict
from odoo.addons.web_studio.controllers.main import WebStudioController


@tagged('web_studio_normalization')
class TestViewNormalization(TransactionCase):

    maxDiff = None

    def setUp(self):
        super(TestViewNormalization, self).setUp()
        random.seed('https://youtu.be/tFjNH9l6-sQ')
        self.session = DotDict({'debug': ''})
        _request_stack.push(self)
        self.base_view = self.env.ref('base.view_partner_form')
        self.gantt_view = self.env['ir.ui.view'].create({
            'arch_base':
            """
            <gantt date_start="date" date_stop="" string="Test">
            </gantt>
            """,
            'model': 'res.partner',
            'type': 'gantt',
        })
        self.view = self.base_view.create({
            'arch_base':
            """
            <form string="Partners">
                <sheet>
                    <field name="image_1920" widget="image" class="oe_avatar" options="{&quot;preview_image&quot;: &quot;image_128&quot;, &quot;size&quot;: [90, 90]}"/>
                    <div class="oe_title">
                        <field name="is_company" invisible="1"/>
                        <field name="type" invisible="1"/>
                        <field name="company_type" widget="radio" class="oe_edit_only" on_change="on_change_company_type(company_type)" options="{'horizontal': true}"/>
                        <h1>
                            <field name="name" default_focus="1" placeholder="Name" required="type == 'contact'"/>
                        </h1>
                        <div class="o_row">
                            <field name="parent_id" placeholder="Company" domain="[('is_company', '=', True)]" context="{'default_is_company': True}" invisible="is_company and not parent_id" on_change="onchange_parent_id(parent_id)"/>
                        </div>
                    </div>

                    <group>
                        <group>
                            <field name="type" invisible="not parent_id" groups="base.group_no_one"/>
                            <label for="street" string="Address"/>
                            <div class="o_address_format">
                                <div class="oe_edit_only">
                                    <button name="open_commercial_entity" type="object" string="(edit)" class="oe_link" invisible="not parent_id or type != 'contact'"/>
                                </div>

                                <field name="street" placeholder="Street..." class="o_address_street" readonly="type == 'contact' and parent_id"/>
                                <field name="street2" placeholder="Street 2..." class="o_address_street" readonly="type == 'contact' and parent_id"/>
                                <field name="city" placeholder="City" class="o_address_city" readonly="type == 'contact' and parent_id"/>
                                <field name="state_id" class="o_address_state" placeholder="State" options="{&quot;no_open&quot;: True}" on_change="onchange_state(state_id)" readonly="type == 'contact' and parent_id" context="{'country_id': country_id, 'zip': zip}"/>
                                <field name="zip" placeholder="ZIP" class="o_address_zip" readonly="type == 'contact' and parent_id"/>
                                <field name="country_id" placeholder="Country" class="o_address_country" options="{&quot;no_open&quot;: True, &quot;no_create&quot;: True}" readonly="type == 'contact' and parent_id"/>
                            </div>
                            <field name="website" widget="url" placeholder="e.g. www.odoo.com"/>
                        </group>
                        <group>
                            <field name="function" placeholder="e.g. Sales Director" invisible="is_company"/>
                            <field name="phone" widget="phone"/>
                            <field name="mobile" widget="phone"/>
                            <field name="user_ids" invisible="1"/>
                            <field name="email" widget="email" required="user_ids"/>
                            <field name="title" options="{&quot;no_open&quot;: True}" invisible="is_company"/>
                            <field name="lang"/>
                            <field name="category_id" widget="many2many_tags" placeholder="Tags..."/>
                        </group>
                        <group>
                            <field name="display_name"/>
                        </group>
                    </group>

                    <notebook colspan="4">
                        <page string="Contacts &amp; Addresses" autofocus="autofocus">
                            <field name="child_ids" mode="kanban" context="{'default_parent_id': id, 'default_street': street, 'default_street2': street2, 'default_city': city, 'default_state_id': state_id, 'default_zip': zip, 'default_country_id': country_id}">
                                <kanban>
                                    <field name="color"/>
                                    <field name="title"/>
                                    <field name="email"/>
                                    <field name="function"/>
                                    <field name="phone"/>
                                    <field name="mobile"/>
                                    <templates>
                                        <t t-name="card">
                                            <div>
                                                <field name="name"/>
                                            </div>
                                        </t>
                                    </templates>
                                </kanban>
                            </field>
                        </page>
                    </notebook>
                </sheet>
            </form>
            """,
            'model': 'res.partner'})
        self.studio_controller = WebStudioController()

    def _test_view_normalization(self, original, expected, view='form'):
        if view == 'gantt':
            view = self.gantt_view
        else:
            view = self.view

        original = original and textwrap.dedent(original)
        self.studio_controller._set_studio_view(view, original)

        studio_view = self.studio_controller._get_studio_view(view)
        studio_view = studio_view.with_context(load_all_views=True)
        normalized = studio_view.normalize()

        self.studio_controller._set_studio_view(view, normalized)
        self.env[self.view.model].with_context(studio=True, load_all_views=True).get_view(view.id, view.type)

        normalized = normalized and normalized.strip()
        expected = expected and textwrap.dedent(expected).strip()
        self.assertEqual(normalized, expected)

    # Flatten all xpath that target nodes added by studio itself
    def test_view_normalization_00(self):
        self._test_view_normalization("""
            <data>
              <xpath expr="/form[1]/sheet[1]/group[1]" position="after">
                <group name="studio_group_E16QG">
                  <group name="studio_group_E16QG_left" string="Left Title"/>
                  <group name="studio_group_E16QG_right" string="Right Title"/>
                </group>
              </xpath>
              <xpath expr="//group[@name='studio_group_E16QG_left']" position="inside">
                <field name="partner_latitude"/>
              </xpath>
              <xpath expr="//group[@name='studio_group_E16QG_left']" position="after">
                <field name="id"/>
              </xpath>
              <xpath expr="//group[@name='studio_group_E16QG_right']" position="inside">
                <field name="employee"/>
              </xpath>
              <xpath expr="//field[@name='partner_latitude']" position="after">
                <field name="contact_address"/>
              </xpath>
            </data>
        """, """
            <data>
              <xpath expr="//form[1]/sheet[1]/group[1]" position="after">
                <group name="studio_group_E16QG">
                  <group name="studio_group_E16QG_left" string="Left Title">
                    <field name="partner_latitude"/>
                    <field name="contact_address"/>
                  </group>
                  <field name="id"/>
                  <group name="studio_group_E16QG_right" string="Right Title">
                    <field name="employee"/>
                  </group>
                </group>
              </xpath>
            </data>
        """)

    # Delete children of deleted nodes and reanchor siblings
    def test_view_normalization_01(self):
        self._test_view_normalization("""
            <data>
              <xpath expr="/form[1]/sheet[1]/group[1]" position="after">
                <group name="studio_group_E16QG">
                  <group name="studio_group_E16QG_left" string="Left Title"/>
                  <group name="studio_group_E16QG_right" string="Right Title"/>
                </group>
              </xpath>
              <xpath expr="//group[@name='studio_group_E16QG_left']" position="inside">
                <field name="partner_latitude"/>
              </xpath>
              <xpath expr="//group[@name='studio_group_E16QG_left']" position="after">
                <field name="id"/>
              </xpath>
              <xpath expr="//group[@name='studio_group_E16QG_right']" position="inside">
                <field name="employee"/>
              </xpath>
              <xpath expr="//field[@name='partner_latitude']" position="after">
                <field name="contact_address"/>
              </xpath>
              <xpath expr="//group[@name='studio_group_E16QG_left']" position="replace"/>
            </data>
        """, """
            <data>
              <xpath expr="//form[1]/sheet[1]/group[1]" position="after">
                <group name="studio_group_E16QG">
                  <field name="id"/>
                  <group name="studio_group_E16QG_right" string="Right Title">
                    <field name="employee"/>
                  </group>
                </group>
              </xpath>
            </data>
        """)

    # When there is no more sibling, we need to reanchor on the parent
    def test_view_normalization_02(self):
        self._test_view_normalization("""
            <data>
              <xpath expr="/form[1]/sheet[1]/group[1]" position="after">
                <group name="studio_group_E16QG">
                  <group name="studio_group_E16QG_right" string="Right Title"/>
                </group>
              </xpath>
              <xpath expr="//group[@name='studio_group_E16QG_right']" position="before">
                <field name="id"/>
              </xpath>
              <xpath expr="//group[@name='studio_group_E16QG_right']" position="inside">
                <field name="employee"/>
              </xpath>
              <xpath expr="//group[@name='studio_group_E16QG_right']" position="replace"/>
            </data>
        """, """
            <data>
              <xpath expr="//form[1]/sheet[1]/group[1]" position="after">
                <group name="studio_group_E16QG">
                  <field name="id"/>
                </group>
              </xpath>
            </data>
        """)

    # When a field is deleted, other xpath that targets it need to be reanchored.
    def test_view_normalization_03(self):
        self._test_view_normalization("""
            <data>
              <xpath expr="/form[1]/sheet[1]/group[1]" position="after">
                <group name="studio_group_E16QG">
                  <group name="studio_group_E16QG_right" string="Right Title"/>
                </group>
              </xpath>
              <xpath expr="//group[@name='studio_group_E16QG_right']" position="before">
                <field name="id"/>
              </xpath>
              <xpath expr="//group[@name='studio_group_E16QG_right']" position="inside">
                <field name="employee"/>
              </xpath>
              <xpath expr="//group[@name='studio_group_E16QG_right']" position="replace"/>
            </data>
        """, """
            <data>
              <xpath expr="//form[1]/sheet[1]/group[1]" position="after">
                <group name="studio_group_E16QG">
                  <field name="id"/>
                </group>
              </xpath>
            </data>
        """)

    # If there is nothing left in the studio view, delete it.
    def test_view_normalization_04(self):
        expected = ''
        self._test_view_normalization("""
            <data>
              <xpath expr="/form[1]/sheet[1]/group[1]" position="after">
                <group name="studio_group_E16QG"/>
              </xpath>
              <xpath expr="//group[@name='studio_group_E16QG']" position="inside">
                <field name="id"/>
              </xpath>
              <xpath expr="//field[@name='id']" position="after">
                <field name="create_uid"/>
              </xpath>
              <xpath expr="//group[@name='studio_group_E16QG']" position="replace"/>
            </data>
        """, expected)
        studio_view = self.studio_controller._set_studio_view(self.view, expected)
        studio_view = self.studio_controller._get_studio_view(self.view)
        self.assertEqual(len(studio_view), 0)

    # An after can become a replace if the following sibling has been removed.
    def test_view_normalization_05(self):
        self._test_view_normalization("""
            <data>
              <xpath expr="//field[@name='mobile']" position="after">
                <field name="contact_address"/>
              </xpath>
              <xpath expr="//field[@name='mobile']" position="replace"/>
              <xpath expr="//field[@name='contact_address']" position="after">
                <field name="tz"/>
              </xpath>
              <xpath expr="//field[@name='contact_address']" position="replace"/>
            </data>
        """, """
            <data>
              <xpath expr="//form[1]/sheet[1]/group[1]/group[2]/field[@name='mobile']" position="replace">
                <field name="tz"/>
              </xpath>
            </data>
        """)

    # Multiple additions of fields should not appear if it was deleted
    def test_view_normalization_06(self):
        self._test_view_normalization("""
            <data>
              <xpath expr="//field[@name='website']" position="after">
                <field name="color"/>
              </xpath>
              <xpath expr="//field[@name='color']" position="replace">
              </xpath>
              <xpath expr="//field[@name='category_id']" position="after">
                <field name="color"/>
              </xpath>
              <xpath expr="//field[@name='color']" position="after">
                <field name="create_date"/>
              </xpath>
              <xpath expr="//field[@name='color']" position="replace"/>
            </data>
        """, """
            <data>
              <xpath expr="//field[@name='category_id']" position="after">
                <field name="create_date"/>
              </xpath>
            </data>
        """)

    # Consecutive xpaths around a field that was moved away can be merged.
    def test_view_normalization_07(self):
        self._test_view_normalization("""
            <data>
              <xpath expr="//field[@name='mobile']" position="after">
                <field name="contact_address"/>
              </xpath>
              <xpath expr="//field[@name='contact_address']" position="after">
                  <field name="tz"/>
              </xpath>
              <xpath expr="//field[@name='contact_address']" position="replace"/>
              <xpath expr="//field[@name='tz']" position="after">
                  <field name="contact_address"/>
              </xpath>
              <xpath expr="//field[@name='contact_address']" position="after">
                  <field name="create_uid"/>
              </xpath>
              <xpath expr="//field[@name='contact_address']" position="replace"/>
            </data>
        """, """
            <data>
              <xpath expr="//form[1]/sheet[1]/group[1]/group[2]/field[@name='mobile']" position="after">
                <field name="tz"/>
                <field name="create_uid"/>
              </xpath>
            </data>
        """)

    # A field that was added, then moved then deleted should not appear.
    def test_view_normalization_08(self):
        self._test_view_normalization("""
          <data>
            <xpath expr="//field[@name='website']" position="after">
              <field name="color"/>
            </xpath>
            <xpath expr="//field[@name='color']" position="replace">
              <field name="create_uid"/>
            </xpath>
            <xpath expr="//field[@name='category_id']" position="after">
              <field name="color"/>
            </xpath>
            <xpath expr="//field[@name='color']" position="after">
              <field name="create_date"/>
            </xpath>
            <xpath expr="//field[@name='color']" position="replace"/>
          </data>
        """, """
          <data>
            <xpath expr="//field[@name='website']" position="after">
              <field name="create_uid"/>
            </xpath>
            <xpath expr="//field[@name='category_id']" position="after">
              <field name="create_date"/>
            </xpath>
          </data>
        """)

    # Fields that were added then removed should not appear in the view at all,
    # and every other xpath that was using it should be reanchored elsewhere.
    def test_view_normalization_09(self):
        self._test_view_normalization("""
            <data>
              <xpath expr="//field[@name='phone']" position="after">
                <field name="contact_address"/>
              </xpath>
              <xpath expr="//field[@name='contact_address']" position="replace">
                  <field name="id"/>
              </xpath>
              <xpath expr="//field[@name='mobile']" position="after">
                  <field name="contact_address"/>
              </xpath>
              <xpath expr="//field[@name='contact_address']" position="after">
                  <field name="create_uid"/>
              </xpath>
              <xpath expr="//field[@name='contact_address']" position="replace"/>
            </data>
        """, """
            <data>
              <xpath expr="//form[1]/sheet[1]/group[1]/group[2]/field[@name='phone']" position="after">
                <field name="id"/>
              </xpath>
              <xpath expr="//form[1]/sheet[1]/group[1]/group[2]/field[@name='mobile']" position="after">
                <field name="create_uid"/>
              </xpath>
            </data>
        """)

    # When two fields are added after a given field, the second one will appear
    # before the first one.
    def test_view_normalization_10(self):
        self._test_view_normalization("""
            <data>
              <xpath expr="//field[@name='phone']" position="replace">
                <field name="create_date"/>
              </xpath>
              <xpath expr="//field[@name='create_date']" position="after">
                  <field name="id"/>
              </xpath>
              <xpath expr="//field[@name='create_date']" position="after">
                <field name="contact_address"/>
              </xpath>
              <xpath expr="//field[@name='create_date']" position="replace"/>
            </data>
        """, """
            <data>
              <xpath expr="//form[1]/sheet[1]/group[1]/group[2]/field[@name='phone']" position="replace">
                <field name="contact_address"/>
                <field name="id"/>
              </xpath>
            </data>
        """)

    # When we add a field after another one and replace the sibling of this one,
    # everything could be done in a single replace on the sibling node.
    def test_view_normalization_11(self):
        self._test_view_normalization("""
            <data>
              <xpath expr="//field[@name='phone']" position="after">
                <field name="create_uid"/>
              </xpath>
              <xpath expr="//field[@name='phone']" position="replace">
                <field name="create_date"/>
              </xpath>
              <xpath expr="//field[@name='create_date']" position="after">
                  <field name="id"/>
              </xpath>
              <xpath expr="//field[@name='create_date']" position="replace"/>
              <xpath expr="//field[@name='create_uid']" position="before">
                <field name="create_date"/>
              </xpath>
              <xpath expr="//field[@name='create_date']" position="after">
                  <field name="mobile"/>
              </xpath>
              <xpath expr="//field[@name='create_date']" position="replace"/>
            </data>
        """, """
            <data>
              <xpath expr="//form[1]/sheet[1]/group[1]/group[2]/field[@name='phone']" position="replace">
                <field name="id"/>
                <field name="mobile"/>
                <field name="create_uid"/>
              </xpath>
            </data>
        """)

    # When closest previous node has no name, the closest next node should be
    # used instead, provided it has a name. Also, attributes need to be handled
    # in a single xpath and alphabetically sorted.
    def test_view_normalization_12(self):
        self._test_view_normalization("""
            <data>
              <xpath expr="//form[1]/sheet[1]/notebook[1]/page[1]" position="attributes">
                <attribute name="zzz">PAGE 1 ZZZ</attribute>
              </xpath>
              <xpath expr="//form[1]/sheet[1]/notebook[1]/page[1]" position="after">
                <page name="PAGE_2" string="AWESOME PAGE 2"/>
              </xpath>
              <xpath expr="//form[1]/sheet[1]/notebook[1]/page[1]" position="attributes">
                <attribute name="help">PAGE 1 HELP</attribute>
              </xpath>
            </data>
        """, """
            <data>
              <xpath expr="//form[1]/sheet[1]/notebook[1]/page[1]" position="attributes">
                <attribute name="help">PAGE 1 HELP</attribute>
                <attribute name="zzz">PAGE 1 ZZZ</attribute>
              </xpath>
              <xpath expr="//form[1]/sheet[1]/notebook[1]" position="inside">
                <page name="PAGE_2" string="AWESOME PAGE 2"/>
              </xpath>
            </data>
        """)

    # Changing an already existing attribute will generate a remove line for
    # the previous value and an addition line for the new value. The removing
    # line should not close the attributes xpath, both attributes need to be
    # redefined in a single xpath.
    def test_view_normalization_13(self):
        self._test_view_normalization("""
            <data>
              <xpath expr="//form[1]/sheet[1]/notebook[1]/page[1]" position="attributes">
                <attribute name="string">PAGE 1</attribute>
              </xpath>
              <xpath expr="//form[1]/sheet[1]/notebook[1]/page[1]" position="after">
                <page name="PAGE_2" string="AWESOME PAGE 2"/>
              </xpath>
              <xpath expr="//form[1]/sheet[1]/notebook[1]/page[1]" position="attributes">
                <attribute name="help">PAGE 1 HELP</attribute>
              </xpath>
            </data>
        """, """
            <data>
              <xpath expr="//form[1]/sheet[1]/notebook[1]/page[1]" position="attributes">
                <attribute name="help">PAGE 1 HELP</attribute>
                <attribute name="string">PAGE 1</attribute>
              </xpath>
              <xpath expr="//form[1]/sheet[1]/notebook[1]" position="inside">
                <page name="PAGE_2" string="AWESOME PAGE 2"/>
              </xpath>
            </data>
        """)

    def test_view_normalization_14(self):
        # There is already a chatter on res.partner.form view, which is why
        # the resulting xpath is /div instead of /sheet.
        self._test_view_normalization("""
            <data>
              <xpath expr="/form[1]/*[last()]" position="after">
                <chatter/>
              </xpath>
            </data>
        """, """
            <data>
              <xpath expr="//form[1]/sheet[1]" position="after">
                <chatter/>
              </xpath>
            </data>
        """)

    # Don't break on text with newlines
    def test_view_normalization_15(self):
        # New lines in text used to create a new line in the diff, desynchronizing
        # the diff lines and the tree elements iterator
        self._test_view_normalization("""
            <data>
              <xpath expr="//field[@name='phone']" position="replace">
                <h1>
                    THIS
                    IS
                    A MULTILINE
                    TITLE
                </h1>
              </xpath>
            </data>
        """, """
            <data>
              <xpath expr="//form[1]/sheet[1]/group[1]/group[2]/field[@name='phone']" position="replace">
                <h1>
                    THIS
                    IS
                    A MULTILINE
                    TITLE
                </h1>
              </xpath>
            </data>
        """)

    # Test anchoring next to studio fields
    def test_view_normalization_16(self):
        self._test_view_normalization("""
            <data>
              <xpath expr="//field[@name='mobile']" position="after">
                <field name="contact_address"/>
              </xpath>
              <xpath expr="//field[@name='contact_address']" position="after">
                <field name="tz"/>
              </xpath>
              <xpath expr="//field[@name='tz']" position="before">
                <field name="phone"/>
              </xpath>
            </data>
        """, """
            <data>
              <xpath expr="//form[1]/sheet[1]/group[1]/group[2]/field[@name='mobile']" position="after">
                <field name="contact_address"/>
                <field name="phone"/>
                <field name="tz"/>
              </xpath>
            </data>
        """)

    # Test replace of last element in arch
    def test_view_normalization_17(self):
        self._test_view_normalization("""
            <data>
              <xpath expr="//field[@name='lang']" position="replace"/>
            </data>
        """, """
            <data>
              <xpath expr="//field[@name='lang']" position="replace"/>
            </data>
        """)

    # Replace an existing element then add it back in but somewhere before
    # its original position
    def test_view_normalization_18(self):
        self._test_view_normalization("""
            <data>
              <xpath expr="//field[@name='mobile']" position="replace"/>
              <xpath expr="//field[@name='function']" position="after">
                <field name="mobile" widget="phone"/>
              </xpath>
            </data>
        """, """
            <data>
              <xpath expr="//form[1]/sheet[1]/group[1]/group[2]/field[@name='function']" position="after">
                <xpath expr="//form[1]/sheet[1]/group[1]/group[2]/field[@name='mobile']" position="move"/>
              </xpath>
            </data>
        """)

    # Delete an existing element, then replace another element with the deleted
    # element further down
    def test_view_normalization_19(self):
        self._test_view_normalization("""
            <data>
              <xpath expr="//field[@name='phone']" position="replace"/>
              <xpath expr="//field[@name='email']" position="replace"/>
              <xpath expr="//field[@name='user_ids']" position="after">
                <field name="phone"/>
              </xpath>
            </data>
        """, """
            <data>
              <xpath expr="//form[1]/sheet[1]/group[1]/group[2]/field[@name='email']" position="replace">
                <xpath expr="//form[1]/sheet[1]/group[1]/group[2]/field[@name='phone']" position="move"/>
              </xpath>
              <xpath expr="//form[1]/sheet[1]/group[1]/group[2]/field[@name='phone']" position="attributes">
                <attribute name="widget"></attribute>
              </xpath>
            </data>
        """)

    # Delete an existing element, then replace another element before the
    # original element with the latter
    def test_view_normalization_20(self):
        self._test_view_normalization("""
            <data>
              <xpath expr="//field[@name='email']" position="replace"/>
              <xpath expr="//field[@name='phone']" position="replace"/>
              <xpath expr="//field[@name='function']" position="after">
                <field name="email"/>
              </xpath>
            </data>
        """, """
            <data>
              <xpath expr="//form[1]/sheet[1]/group[1]/group[2]/field[@name='phone']" position="replace">
                <xpath expr="//form[1]/sheet[1]/group[1]/group[2]/field[@name='email']" position="move"/>
              </xpath>
              <xpath expr="//form[1]/sheet[1]/group[1]/group[2]/field[@name='email']" position="attributes">
                <attribute name="required"></attribute>
                <attribute name="widget"></attribute>
              </xpath>
            </data>
        """)

    # template fields are appended to the templates, not to the kanban itself
    def test_view_normalization_21(self):
        self._test_view_normalization("""
            <data>
              <xpath expr="//templates//field[@name='name']" position="after">
                <field name="phone"/>
              </xpath>
              <xpath expr="//templates//field[@name='phone']" position="after">
                <field name="mobile"/>
              </xpath>
              <xpath expr="//templates//field[@name='name']" position="before">
                <field name="color"/>
              </xpath>
            </data>
        """, """
            <data>
              <xpath expr="//form[1]/sheet[1]/notebook[1]/page[1]/field[@name='child_ids']/kanban[1]/templates[1]/t[@t-name='card']/div[1]/field[@name='name']" position="before">
                <field name="color"/>
              </xpath>
              <xpath expr="//form[1]/sheet[1]/notebook[1]/page[1]/field[@name='child_ids']/kanban[1]/templates[1]/t[@t-name='card']/div[1]/field[@name='name']" position="after">
                <field name="phone"/>
                <field name="mobile"/>
              </xpath>
            </data>
        """)

    # adding kanban and template fields while using absolute xpaths
    def test_view_normalization_22(self):
        self._test_view_normalization("""
            <data>
              <xpath expr="//templates" position="before">
                <field name="lang"/>
              </xpath>
              <xpath expr="//templates//div" position="inside">
                <div class="o_dropdown_kanban dropdown">
                            <a role="button" class="dropdown-toggle o-no-caret btn" data-bs-toggle="dropdown" href="#">
                                <span class="fa fa-bars fa-lg" title="menu"/>
                            </a>
                            <div class="dropdown-menu" role="menu">
                                <t t-if="widget.editable"><a type="open" class="dropdown-item">Edit</a></t>
                                <t t-if="widget.deletable"><a type="delete" class="dropdown-item">Delete</a></t>
                                <field name="lang" widget="kanban_color_picker"/>
                            </div>
                        </div>
              </xpath>
              <xpath expr="//templates//div" position="attributes">
                <attribute name="color">lang</attribute>
              </xpath>
            </data>
        """, """
            <data>
              <xpath expr="//form[1]/sheet[1]/notebook[1]/page[1]/field[@name='child_ids']/kanban[1]/field[@name='mobile']" position="after">
                <field name="lang"/>
              </xpath>
              <xpath expr="//form[1]/sheet[1]/notebook[1]/page[1]/field[@name='child_ids']/kanban[1]/templates[1]/t[@t-name='card']/div[1]" position="attributes">
                <attribute name="color">lang</attribute>
              </xpath>
              <xpath expr="//form[1]/sheet[1]/notebook[1]/page[1]/field[@name='child_ids']/kanban[1]/templates[1]/t[@t-name='card']/div[1]/field[@name='name']" position="after">
                <div class="o_dropdown_kanban dropdown" name="studio_div_302a40">
                  <a role="button" class="dropdown-toggle o-no-caret btn" data-bs-toggle="dropdown" href="#">
                    <span class="fa fa-bars fa-lg" title="menu"/>
                  </a>
                  <div class="dropdown-menu" role="menu" name="studio_div_4e2ccd">
                    <t t-if="widget.editable">
                      <a type="open" class="dropdown-item">Edit</a>
                    </t>
                    <t t-if="widget.deletable">
                      <a type="delete" class="dropdown-item">Delete</a>
                    </t>
                    <field name="lang" widget="kanban_color_picker"/>
                  </div>
                </div>
              </xpath>
            </data>
        """)

    # Correctly calculate the expr on flat views
    def test_view_normalization_23(self):
        self._test_view_normalization("""
            <data>
              <xpath expr="//gantt[1]" position="attributes">
                <attribute name="date_stop">date</attribute>
              </xpath>
            </data>
            """, """
            <data>
              <xpath expr="//gantt[1]" position="attributes">
                <attribute name="date_stop">date</attribute>
              </xpath>
            </data>
            """, 'gantt')

    # test that unnamed groups/pages are given a pseudo-random name attribute
    def test_view_normalization_24(self):
        random.seed("https://i.redd.it/pnyr50lf0jh01.png")
        self._test_view_normalization("""
            <data>
                <xpath expr="//form[1]/sheet[1]/notebook[1]" position="after">
                  <group>
                    <p>hello world!</p>
                  </group>
                  <group>
                    <p>foo bar baz</p>
                  </group>
                  <group>
                    <p>spam eggs bacon</p>
                  </group>
                </xpath>
            </data>
        """, """
            <data>
              <xpath expr="//form[1]/sheet[1]/notebook[1]" position="after">
                <group name="studio_group_a9eb51">
                  <p>hello world!</p>
                </group>
                <group name="studio_group_70d54a">
                  <p>foo bar baz</p>
                </group>
                <group name="studio_group_71063a">
                  <p>spam eggs bacon</p>
                </group>
              </xpath>
            </data>
        """)
        random.seed()

    # test that unnamed pages are given a pseudo-random name attribute
    def test_view_normalization_25(self):
        self._test_view_normalization("""
            <data>
                <xpath expr="//form[1]/sheet[1]/notebook[1]" position="inside">
                  <page>
                    <p>hello world!</p>
                  </page>
                  <page>
                    <p>foo bar baz</p>
                  </page>
                  <page>
                    <p>spam eggs bacon</p>
                  </page>
                </xpath>
            </data>
        """, """
            <data>
              <xpath expr="//form[1]/sheet[1]/notebook[1]" position="inside">
                <page name="studio_page_302a40">
                  <p>hello world!</p>
                </page>
                <page name="studio_page_4e2ccd">
                  <p>foo bar baz</p>
                </page>
                <page name="studio_page_ff8328">
                  <p>spam eggs bacon</p>
                </page>
              </xpath>
            </data>
        """)

    # Adjacent addition/removal changes ends with correct xpath
    def test_view_normalization_26(self):
        self._test_view_normalization("""
            <data>
              <field name="category_id" position="attributes">
                <attribute name="placeholder" />
                <attribute name="widget" />
              </field>
              <field name="category_id" position="after">
                <field name="create_uid"/>
              </field>
            </data>
        """, """
            <data>
              <xpath expr="//field[@name='category_id']" position="attributes">
                <attribute name="placeholder"/>
                <attribute name="widget"/>
              </xpath>
              <xpath expr="//field[@name='category_id']" position="after">
                <field name="create_uid"/>
              </xpath>
            </data>
        """)

    # Test descendants equivalent nodes does not change children
    def test_view_normalization_27(self):
        self._test_view_normalization("""
            <data>
              <field name="website" position="after">
                <div>
                    <field name="create_uid"/>
                </div>
                <div>
                    <field name="write_uid"/>
                </div>
              </field>
            </data>
        """, """
            <data>
              <xpath expr="//field[@name='website']" position="after">
                <div name="studio_div_302a40">
                  <field name="create_uid"/>
                </div>
                <div name="studio_div_4e2ccd">
                  <field name="write_uid"/>
                </div>
              </xpath>
            </data>
        """)

    # Test descendants equivalent nodes does not change children with unwrapped field
    def test_view_normalization_28(self):
        self._test_view_normalization("""
            <data>
              <field name="website" position="after">
                <div>
                    <div>
                    <field name="create_uid"/>
                    </div>
                    <field name="write_uid"/>
                </div>
              </field>
            </data>
        """, """
            <data>
              <xpath expr="//field[@name='website']" position="after">
                <div name="studio_div_302a40">
                  <div name="studio_div_4e2ccd">
                    <field name="create_uid"/>
                  </div>
                  <field name="write_uid"/>
                </div>
              </xpath>
            </data>
        """)

    # Move an existing element (after its position)
    def test_view_normalization_29_1(self):
        self._test_view_normalization("""
            <data>
              <xpath expr="//field[@name='email']" position="after">
                <field name="function" position="move"/>
              </xpath>
            </data>
        """, """
            <data>
              <xpath expr="//form[1]/sheet[1]/group[1]/group[2]/field[@name='email']" position="after">
                <xpath expr="//form[1]/sheet[1]/group[1]/group[2]/field[@name='function']" position="move"/>
              </xpath>
            </data>
        """)

    # Move an existing element (before its position)
    def test_view_normalization_29_2(self):
        self._test_view_normalization("""
            <data>
              <xpath expr="//field[@name='website']" position="after">
                <field name="function" position="move"/>
              </xpath>
            </data>
        """, """
            <data>
              <xpath expr="//field[@name='website']" position="after">
                <xpath expr="//form[1]/sheet[1]/group[1]/group[2]/field[@name='function']" position="move"/>
              </xpath>
            </data>
        """)

    # Move two existing elements (after its position)
    def test_view_normalization_30_1(self):
        self._test_view_normalization("""
            <data>
              <xpath expr="//field[@name='email']" position="after">
                <field name="function" position="move"/>
              </xpath>
              <xpath expr="//field[@name='email']" position="after">
                <field name="lang" position="move"/>
              </xpath>
            </data>
        """, """
            <data>
              <xpath expr="//form[1]/sheet[1]/group[1]/group[2]/field[@name='email']" position="after">
                <xpath expr="//field[@name='lang']" position="move"/>
                <xpath expr="//form[1]/sheet[1]/group[1]/group[2]/field[@name='function']" position="move"/>
              </xpath>
            </data>
        """)

    # Move two existing elements (before its position)
    def test_view_normalization_30_2(self):
        self._test_view_normalization("""
            <data>
              <xpath expr="//field[@name='website']" position="after">
                <field name="function" position="move"/>
              </xpath>
              <xpath expr="//field[@name='website']" position="after">
                <field name="lang" position="move"/>
              </xpath>
            </data>
        """, """
            <data>
              <xpath expr="//field[@name='website']" position="after">
                <xpath expr="//field[@name='lang']" position="move"/>
                <xpath expr="//form[1]/sheet[1]/group[1]/group[2]/field[@name='function']" position="move"/>
              </xpath>
            </data>
        """)

    # Move two consequentive existing elements
    def test_view_normalization_30_3(self):
        self._test_view_normalization("""
            <data>
              <xpath expr="//field[@name='email']" position="after">
                <field name="function" position="move"/>
              </xpath>
              <xpath expr="//field[@name='function']" position="after">
                <field name="lang" position="move"/>
              </xpath>
            </data>
        """, """
            <data>
              <xpath expr="//form[1]/sheet[1]/group[1]/group[2]/field[@name='email']" position="after">
                <xpath expr="//form[1]/sheet[1]/group[1]/group[2]/field[@name='function']" position="move"/>
                <xpath expr="//field[@name='lang']" position="move"/>
              </xpath>
            </data>
        """)

    # xpath based on a moved element
    def test_view_normalization_31(self):
        self._test_view_normalization("""
            <data>
              <xpath expr="//field[@name='email']" position="after">
                <field name="function" position="move"/>
              </xpath>
              <xpath expr="//field[@name='function']" position="after">
                <field name="partner_latitude"/>
              </xpath>
            </data>
        """, """
            <data>
              <xpath expr="//form[1]/sheet[1]/group[1]/group[2]/field[@name='email']" position="after">
                <xpath expr="//form[1]/sheet[1]/group[1]/group[2]/field[@name='function']" position="move"/>
                <field name="partner_latitude"/>
              </xpath>
            </data>
        """)

    # Move an existing element and its attributes
    def test_view_normalization_32(self):
        self._test_view_normalization("""
            <data>
              <xpath expr="//field[@name='email']" position="after">
                <field name="function" position="move"/>
              </xpath>
              <xpath expr="//field[@name='function']" position="attributes">
                <attribute name="placeholder">Kikou</attribute>
              </xpath>
            </data>
        """, """
            <data>
              <xpath expr="//form[1]/sheet[1]/group[1]/group[2]/field[@name='email']" position="after">
                <xpath expr="//form[1]/sheet[1]/group[1]/group[2]/field[@name='function']" position="move"/>
              </xpath>
              <xpath expr="//form[1]/sheet[1]/group[1]/group[2]/field[@name='function']" position="attributes">
                <attribute name="placeholder">Kikou</attribute>
              </xpath>
            </data>
        """)

    # Move fields and one of them needs to generate an absolute xpath
    def test_view_normalization_33(self):
        self._test_view_normalization("""
            <data>
              <xpath expr="//field[@name='display_name']" position="before">
                <field name="title" position="move"/>
                <field name="lang" position="move"/>
                <field name="category_id" position="move"/>
              </xpath>
            </data>
        """, """
            <data>
              <xpath expr="//field[@name='display_name']" position="before">
                <xpath expr="//form[1]/sheet[1]/group[1]/group[2]/field[@name='title']" position="move"/>
                <xpath expr="//field[@name='lang']" position="move"/>
                <xpath expr="//field[@name='category_id']" position="move"/>
              </xpath>
            </data>
        """)

    def test_view_normalization_34(self):
        self._test_view_normalization("""
          <data>
            <xpath expr="//form[1]/sheet[1]/notebook[1]" position="inside">
              <page name="my_new_page">
                <group name="my_new_group"/>
              </page>
            </xpath>
            <xpath expr="//group[@name='my_new_group']" position="inside">
              <field name="lang" position="move"/>
            </xpath>
          </data>
        """, """
          <data>
            <xpath expr="//form[1]/sheet[1]/notebook[1]" position="inside">
              <page name="my_new_page">
                <group name="my_new_group"/>
              </page>
            </xpath>
            <xpath expr="//group[@name='my_new_group']" position="inside">
              <xpath expr="//field[@name='lang']" position="move"/>
            </xpath>
          </data>
        """)

    def test_view_normalization_29(self):
        self.view = self.base_view.create({
            'arch_base':
            '''
              <form string="Partner">
                <sheet>
                  <div class="oe_title">
                    <h1>
                        <field name="name" />
                    </h1>
                  </div>
                </sheet>
              </form>
            ''',
            'model': 'res.partner',
            'type': 'form'})

        self._test_view_normalization(
            '''
              <data>
                <xpath expr="//sheet/*[1]" position="before">
                  <div class="oe_button_box" name="button_box">
                  </div>
                </xpath>
              </data>
            ''',
            '''
               <data>
                <xpath expr="//form[1]/sheet[1]/div[not(@name)][1]" position="before">
                  <div class="oe_button_box" name="button_box">
                  </div>
                </xpath>
              </data>
            ''')

    def test_view_normalization_30(self):
        self.view = self.base_view.create({
            'arch_base':
            '''
              <form string="Partner">
                <sheet>
                  <div class="oe_title">
                    <h1>
                        <field name="name" />
                    </h1>
                  </div>
                </sheet>
              </form>
            ''',
            'model': 'res.partner',
            'type': 'form'})

        self._test_view_normalization(
            '''
              <data>
                <xpath expr="//sheet/*[1]" position="before">
                  <div name="x_path_1"></div>
                </xpath>
                <xpath expr="//sheet/*[1]" position="before">
                  <div name="x_path_2"></div>
                </xpath>
              </data>
            ''',
            '''
               <data>
                <xpath expr="//form[1]/sheet[1]/div[not(@name)][1]" position="before">
                  <div name="x_path_2"/>
                  <div name="x_path_1"/>
                </xpath>
              </data>
            ''')

    def test_view_normalization_31_2(self):
        self.view = self.base_view.create({
            'arch_base':
            '''
              <form string="Partner">
                <sheet>
                  <div class="oe_title">
                    <h1>
                        <field name="name" />
                    </h1>
                  </div>
                  <div class="other_div">
                  </div>
                </sheet>
              </form>
            ''',
            'model': 'res.partner',
            'type': 'form'})

        # x_path_[1-3] target <div class="oe_title"/>
        # x_path_4 targets <div class="other_div"/>
        self._test_view_normalization(
            '''
              <data>
                <xpath expr="//sheet/*[1]" position="before">
                  <div name="x_path_1"></div>
                </xpath>
                <xpath expr="//sheet/*[2]" position="before">
                  <div name="x_path_2"></div>
                </xpath>
                <xpath expr="//sheet/*[4]" position="before">
                  <div name="x_path_3"></div>
                </xpath>
                <xpath expr="//sheet/*[5]" position="after">
                  <div name="x_path_4"></div>
                </xpath>
              </data>
            ''',
            '''
               <data>
                <xpath expr="//form[1]/sheet[1]/div[not(@name)][1]" position="before">
                  <div name="x_path_1"/>
                  <div name="x_path_2"/>
                </xpath>
                <xpath expr="//form[1]/sheet[1]/div[not(@name)][1]" position="after">
                  <div name="x_path_3"/>
                </xpath>
                <xpath expr="//form[1]/sheet[1]/div[not(@name)][2]" position="after">
                  <div name="x_path_4"/>
                </xpath>
              </data>
            ''')

    # Removed line can be adjacent to added xpath with [not(@name)]
    def test_view_normalization_35(self):
        self.view = self.base_view.create({
            'arch_base':
            '''
              <form string="Partner">
                <sheet>
                  <div class="block1">hello</div>
                  <div class="block2">world</div>
                  <div class="block3">!</div>
                </sheet>
              </form>
            ''',
            'model': 'res.partner',
            'type': 'form'})

        # end result: orator:/hello/cruel/world/!?
        self._test_view_normalization(
            '''
              <data>
                <xpath expr="//sheet/*[2]" position="before">
                  <div name="x_path_1">cruel</div>
                </xpath>
                <xpath expr="//sheet/*[1]" position="before">
                  <div name="x_path_2">orator:</div>
                </xpath>
                <xpath expr="//sheet/*[5]" position="replace">
                  <div name="x_path_3"/>
                  <div name="x_path_4">!?</div>
                </xpath>
              </data>
            ''',
            '''
               <data>
                <xpath expr="//form[1]/sheet[1]/div[3]" position="replace">
                  <div name="x_path_3"/>
                  <div name="x_path_4">!?</div>
                </xpath>
                <xpath expr="//form[1]/sheet[1]/div[not(@name)][1]" position="before">
                  <div name="x_path_2">orator:</div>
                </xpath>
                <xpath expr="//form[1]/sheet[1]/div[not(@name)][1]" position="after">
                  <div name="x_path_1">cruel</div>
                </xpath>
              </data>
            ''')

    # Added line adjacent to comment should be ignored when xpathing
    def test_view_normalization_36(self):
        self.view = self.base_view.create({
            'arch_base':
            '''
              <form>
                <!-- hello -->
                <div />
                <!-- world -->
              </form>
            ''',
            'model': 'res.partner',
            'type': 'form'})

        # end result: orator:/hello/cruel/world/!?
        self._test_view_normalization(
            '''
              <data>
                <xpath expr="//div" position="before">
                  <!-- , -->
                  <div/>
                </xpath>
              </data>
            ''',
            '''
              <data>
                <xpath expr="//form[1]/div[1]" position="before">
                  <!-- , -->
                  <div name="studio_div_302a40"/>
                </xpath>
              </data>
            ''')

    # Identical fields in same xpath do not have mistaken identity
    def test_view_normalization_37(self):
        self.view = self.base_view.create({
            'arch_base':
            '''
              <form>
                <group name="o2m_field"/>
              </form>
            ''',
            'model': 'res.partner',
            'type': 'form'})

        self._test_view_normalization(
            '''
              <data>
                <xpath expr="//group" position="inside">
                    <list>
                        <button name="first_in_tree"/>
                        <button name="middle"/>
                        <button name="last_in_tree"/>
                    </list>
                    <form>
                        <button name="first_in_form"/>
                        <button name="middle"/>
                        <button name="last_in_form"/>
                    </form>
                </xpath>
              </data>
            ''',
            '''
              <data>
                <xpath expr="//group[@name='o2m_field']" position="inside">
                  <list>
                    <button name="first_in_tree"/>
                    <button name="middle"/>
                    <button name="last_in_tree"/>
                  </list>
                  <form>
                    <button name="first_in_form"/>
                    <button name="middle"/>
                    <button name="last_in_form"/>
                  </form>
                </xpath>
              </data>
            ''')

    def test_view_normalization_37_2(self):
        """Button have a name which is not unique"""

        self.view = self.base_view.create({
            'arch_base':
            '''
              <form>
                <header>
                    <button name="action_confirm"/>
                    <button name="action_confirm"/>
                </header>
              </form>
            ''',
            'model': 'res.partner',
            'type': 'form'})

        self._test_view_normalization(
            '''
              <data>
                <xpath expr="/form[1]/header[1]/button[2]" position="attributes">
                  <attribute name="fire">on the bayou</attribute>
                </xpath>
              </data>
            ''',
            '''
              <data>
                <xpath expr="//form[1]/header[1]/button[@name='action_confirm'][2]" position="attributes">
                  <attribute name="fire">on the bayou</attribute>
                </xpath>
              </data>
            ''')

    def test_view_normalization_with_field_having_the_same_name_as_a_group(self):
        self.view = self.base_view.create({
            'arch_base':
            '''
            <form>
              <sheet>
                <notebook>
                  <page>
                    <group>
                      <group name="group_general">
                        <field name="active" invisible="1"/>
                          </group>
                            <group name="group_standard_price"/>
                          </group>
                          <group string="Internal notes">
                            <field name="display_name"/>
                          </group>
                        </page>
                        <page>
                          <group><group name="display_name">
                              <field name="company_name"/>
                          </group></group>
                        </page>
                    </notebook>
                </sheet>
            </form>
            ''',
            'model': 'res.partner',
            'type': 'form'
        })

        self._test_view_normalization(
            '''
            <data>
              <xpath expr="/form[1]/sheet[1]/notebook[1]/page[1]/group[2]" position="replace"/>
              <xpath expr="/form[1]/sheet[1]/notebook[1]/page[1]/group[1]/group[1]/field[1]" position="before">
                <field name="email"/>
              </xpath>
            </data>
            ''',
            '''
            <data>
              <xpath expr="//form[1]/sheet[1]/notebook[1]/page[1]/group[2]" position="replace"/>
              <xpath expr="//field[@name='active']" position="before">
                <field name="email"/>
              </xpath>
            </data>
            '''
        )

    def test_view_normalization_with_same_name(self):
        self.view = self.base_view.create({
            'arch_base':
                '''
                <form>
                    <group>
                        <group name="group_name">
                            <div class="o_td_label">
                                <label for="create_date" string="Quotation Date"/>
                            </div>
                            <field name="create_date"/>
                            <div class="o_td_label">
                                <label for="create_date" string="Order Date"/>
                            </div>
                            <field name="create_date"/>
                            <field name="display_name"/>
                            <field name="name"/>
                            <field name="title"/>
                        </group>
                    </group>
                </form>
                ''',
            'model': 'res.partner',
            'type': 'form'
        })

        self._test_view_normalization(
            '''
            <data>
                <xpath expr="/form/group/group[1]/div[2]" position="replace"/>
                <xpath expr="/form/group/group[1]/field[2]" position="replace"/>
            </data>
            ''',
            '''
            <data>
              <xpath expr="//form[1]/group[1]/group[@name='group_name']/field[@name='create_date'][2]" position="replace"/>
              <xpath expr="//form[1]/group[1]/group[@name='group_name']/div[2]" position="replace"/>
            </data>
            ''',
        )

    def test_normalization_adjacent_remove_add(self):
        self.view = self.base_view.create({
            'arch_base':
                '''
                <form>
                    <group>
                        <group name="group_name">
                            <field name="display_name" />
                        </group>
                        <group name="group_name_2"/>
                    </group>
                </form>
                ''',
            'model': 'res.partner',
            'type': 'form'
        })

        self._test_view_normalization(
            '''
            <data>
                <xpath expr="/form/group/group[1]/field[1]" position="after">
                    <field name="function" />
                </xpath>
                <xpath expr="/form/group/group[2]" position="replace"/>
            </data>
            ''', """
            <data>
              <xpath expr="//group[@name='group_name_2']" position="replace"/>
              <xpath expr="//field[@name='display_name']" position="after">
                <field name="function"/>
              </xpath>
            </data>
            """)

    def tearDown(self):
        super(TestViewNormalization, self).tearDown()
        random.seed()
        _request_stack.pop()

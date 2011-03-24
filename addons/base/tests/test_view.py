import xml.etree.ElementTree

import unittest2

import base.controllers.main

class ViewTest(unittest2.TestCase):
    def test_identity(self):
        view = base.controllers.main.View()
        base_view = """
            <form string="Title">
                <group>
                    <field name="some_field"/>
                    <field name="some_other_field"/>
                </group>
                <field name="stuff"/>
            </form>
        """

        pristine = xml.etree.ElementTree.fromstring(base_view)
        transformed = view.transform_view(base_view)

        self.assertEqual(
             xml.etree.ElementTree.tostring(transformed),
             xml.etree.ElementTree.tostring(pristine)
        )


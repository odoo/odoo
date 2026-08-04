from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

from odoo.addons.base.tests.test_ir_ui_view import ViewCase


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestCalendarView(ViewCase):
    def test_field_then_popover(self):
        self.assertValid(
            """
                <calendar date_start="create_date">
                    <field name="name"/>
                    <popover>
                        <field name="model"/>
                    </popover>
                </calendar>
            """,
        )

    def test_popover_then_field(self):
        # the popover used to be required to come after every <field>,
        # RelaxNG now interleaves them so either order is valid
        self.assertValid(
            """
                <calendar date_start="create_date">
                    <popover>
                        <field name="model"/>
                    </popover>
                    <field name="name"/>
                </calendar>
            """,
        )

    def test_field_popover_field(self):
        self.assertValid(
            """
                <calendar date_start="create_date">
                    <field name="name"/>
                    <popover>
                        <field name="model"/>
                    </popover>
                    <field name="type"/>
                </calendar>
            """,
        )

    def test_popover_only(self):
        self.assertValid(
            """
                <calendar date_start="create_date">
                    <popover>
                        <field name="model"/>
                    </popover>
                </calendar>
            """,
        )

    def test_fields_only_no_popover(self):
        self.assertValid(
            """
                <calendar date_start="create_date">
                    <field name="name"/>
                    <field name="model"/>
                </calendar>
            """,
        )

    def test_two_popovers_invalid(self):
        with self.assertRaises(ValidationError):
            self.View.create({
                "arch": """
                    <calendar date_start="create_date">
                        <popover>
                            <field name="model"/>
                        </popover>
                        <popover>
                            <field name="type"/>
                        </popover>
                    </calendar>
                """,
                "model": "res.partner",
            })

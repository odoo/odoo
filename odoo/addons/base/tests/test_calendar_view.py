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
        with self.assertRaises(ValidationError, msg="We cannot have more than one popover XML element inside the calendar view"):
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

    def test_schedulecard_card_id(self):
        self.assertValid(
            """
                <calendar date_start="create_date">
                    <schedulecard card_id="1"/>
                </calendar>
            """,
        )

    def test_schedulecard_inline_templates(self):
        self.assertValid(
            """
                <calendar date_start="create_date">
                    <schedulecard>
                        <templates>
                            <t t-name="card"><field name="name"/></t>
                        </templates>
                    </schedulecard>
                </calendar>
            """,
        )

    def test_schedulecard_empty_invalid(self):
        self.assertInvalid(
            """
                <calendar date_start="create_date">
                    <schedulecard/>
                </calendar>
            """,
            "Schedulecard must have a card_id attribute or a templates tag",
        )

    def test_schedulecard_card_node_invalid(self):
        self.assertInvalid(
            """
                <calendar date_start="create_date">
                    <schedulecard>
                        <card/>
                    </schedulecard>
                </calendar>
            """,
            "Schedulecard child can only be field or templates, got card",
        )

import { expect, test, beforeEach } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";

import { defineMailModels } from "@mail/../tests/mail_test_helpers";

import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
} from "@web/../tests/web_test_helpers";

defineMailModels();

class HrAttendance extends models.Model {
    _name = "hr.attendance";
    linked_overtime_ids = fields.One2many({ relation: "hr.attendance.overtime.line" });

    _records = [{ id: 1, linked_overtime_ids: [1] }];
}

class HrAttendanceOvertimeLine extends models.Model {
    _name = "hr.attendance.overtime.line";
    rule_ids = fields.Many2many({ relation: "hr.attendance.overtime.rule" });
    manual_duration = fields.Float();
    amount_rate = fields.Float();

    _records = [{ id: 1, manual_duration: 1, amount_rate: 1.5, rule_ids: [] }];
}

class HrAttendanceOvertimeRule extends models.Model {
    _name = "hr.attendance.overtime.rule";
}

defineModels([HrAttendance, HrAttendanceOvertimeLine, HrAttendanceOvertimeRule]);

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

beforeEach(async () => {
    await mountView({
        type: "form",
        resModel: "hr.attendance",
        resId: 1,
        arch: `
            <form>
                <sheet>
                    <group>
                        <field
                            name="linked_overtime_ids"
                            widget="overtime_details">
                            <list>
                                <field name="rule_ids" widget="many2many_tags" string="Applied Rules"/>
                                <field name="manual_duration" widget="float_time" string="Overtime"/>
                                <field name="amount_rate" widget="percentage" string="Overtime Pay Rate"/>
                            </list>
                        </field>
                    </group>
                </sheet>
            </form>
        `,
    });
});

test.tags("desktop");
test("overtime details opens a list in a popover onclick on the total overtime duration", async () => {
    expect(".popover").toHaveCount(0);

    await contains(".o_field_widget[name='linked_overtime_ids'] button.btn-link").click();
    await animationFrame();

    expect(".popover .o_list_renderer").toHaveCount(1);

    await contains(".popover .popover-header .fa-close").click();
    await animationFrame();

    expect(".popover").toHaveCount(0);
});

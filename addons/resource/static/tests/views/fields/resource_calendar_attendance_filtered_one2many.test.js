import { expect, test } from "@odoo/hoot";
import { clickSave, contains, mountView, onRpc } from "@web/../tests/web_test_helpers";
import { defineResourceModels } from "../../resource_test_helpers";

defineResourceModels();

test.tags("desktop");
test(`abandoned attendance line is not saved`, async () => {
    onRpc("resource.calendar", "web_save", ({ args }) => {
        expect.step("web_save");
        expect(args[1].attendance_ids).toHaveLength(1);
    });
    await mountView({
        resId: 1,
        resModel: "resource.calendar",
        type: "form",
        arch: `
            <form>
                <field name="attendance_ids" widget="resource_calendar_attendance_filtered_one2many" domain_filter="[('date', '=', False)]">
                    <list editable="bottom">
                        <field name="date" column_invisible="True"/>
                        <field name="duration_hours"/>
                    </list>
                </field>
            </form>
        `,
    });
    await contains(".o_field_x2many_list_row_add button").click();
    await contains(".o_selected_row [name=duration_hours] input").edit(8, { confirm: false });
    await contains(".o_field_x2many_list_row_add button").click();
    expect(".o_data_row").toHaveCount(2);

    await contains(".o_data_row:first .o_data_cell").click();
    expect(".o_data_row").toHaveCount(1);

    await clickSave();
    expect.verifySteps(["web_save"]);
});

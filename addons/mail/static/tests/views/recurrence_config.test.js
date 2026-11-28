import { mailModels } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import { contains, defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";

class RecurringRecord extends models.Model {
    _name = "recurring.record";

    recurrency = fields.Boolean();
    is_recurring_field_name = fields.Char({ default: "recurrency" });
    rrule_type_ui = fields.Selection({
        selection: [
            ["daily", "Daily"],
            ["weekly", "Weekly"],
            ["custom", "Custom"],
        ],
    });
    rrule_type = fields.Selection({
        selection: [
            ["daily", "Days"],
            ["weekly", "Weeks"],
        ],
    });
    interval = fields.Integer();
    month_by = fields.Selection({
        selection: [
            ["date", "Date of month"],
            ["day", "Day of month"],
        ],
    });
    day = fields.Integer();
    byday = fields.Selection({ selection: [["1", "First"]] });
    weekday = fields.Selection({ selection: [["MON", "Monday"]] });
    end_type = fields.Selection({
        selection: [
            ["count", "Number of repetitions"],
            ["end_date", "End date"],
            ["forever", "Forever"],
        ],
    });
    count = fields.Integer();
    until = fields.Date();
    mon = fields.Boolean({ string: "Mon" });
    tue = fields.Boolean({ string: "Tue" });
    wed = fields.Boolean({ string: "Wed" });
    thu = fields.Boolean({ string: "Thu" });
    fri = fields.Boolean({ string: "Fri" });
    sat = fields.Boolean({ string: "Sat" });
    sun = fields.Boolean({ string: "Sun" });

    _records = [
        {
            id: 1,
            recurrency: true,
            rrule_type_ui: "weekly",
            rrule_type: "weekly",
            interval: 1,
            end_type: "forever",
            mon: true,
        },
    ];
}

defineModels({ ...mailModels, RecurringRecord });

// As in the real views, the selection fields of the widget are declared (invisible) for their options.
const arch = `
    <form>
        <field name="recurrency"/>
        <field name="rrule_type_ui" invisible="1"/>
        <field name="rrule_type" invisible="1"/>
        <field name="month_by" invisible="1"/>
        <field name="byday" invisible="1"/>
        <field name="weekday" invisible="1"/>
        <field name="end_type" invisible="1"/>
        <widget name="recurrence_config" invisible="not recurrency"/>
    </form>`;

test("recurrence widget shows and updates its selection fields", async () => {
    await mountView({ type: "form", resModel: "recurring.record", resId: 1, arch });

    await contains(".o_field_selection[name='rrule_type_ui'] input").click();
    expect(queryAllTexts(".o_select_menu_item")).toEqual(["Daily", "Weekly", "Custom"]);
    await contains(".o_select_menu_item:contains(Custom)").click();
    expect(".o_field_selection[name='rrule_type_ui'] input").toHaveValue("Custom");

    // shown once "Custom" is selected
    await contains(".o_field_selection[name='rrule_type'] input").click();
    expect(queryAllTexts(".o_select_menu_item")).toEqual(["Days", "Weeks"]);

    await contains(".o_field_selection[name='end_type'] input").click();
    expect(queryAllTexts(".o_select_menu_item")).toEqual([
        "Number of repetitions",
        "End date",
        "Forever",
    ]);
    await contains(".o_select_menu_item:contains(Number of repetitions)").click();
    expect(".o_field_selection[name='end_type'] input").toHaveValue("Number of repetitions");
    expect(".o_field_widget[name='count']").toHaveCount(1);
});

test("recurrence widget shows the labels of its selection fields when readonly", async () => {
    await mountView({
        type: "form",
        resModel: "recurring.record",
        resId: 1,
        arch: arch.replace("<form>", "<form edit='0'>"),
    });

    expect(".o_recurrence_config_widget span:contains(Weekly)").toHaveCount(1);
    expect(".o_recurrence_config_widget span:contains(Forever)").toHaveCount(1);
});

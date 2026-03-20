/** @odoo-module **/

import {
    contains,
    defineModels,
    fields,
    makeMockServer,
    models,
    mountView,
} from "@web/../tests/web_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { queryAll } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { defineHrModels } from "@hr/../tests/hr_test_helpers";

defineHrModels();
class Partner extends models.Model {
    _name = "partner";

    name = fields.Char({ string: "Name" });
    start_date = fields.Date({ string: "Start Date" });
    end_date = fields.Date({ string: "End Date" });
    event_date = fields.Date({ string: "Event Date" });
}

defineModels([Partner]);
describe.current.tags("desktop");

test("date_dynamic_min field renders with minDateField option", async function () {
    const { env } = await makeMockServer();
    const partnerId = env["partner"].create({
        name: "Test Partner",
        start_date: "2024-01-15",
        end_date: "2024-02-20",
    });

    await mountView({
        type: "form",
        resModel: "partner",
        resId: partnerId,
        arch: `
            <form>
                <field name="start_date"/>
                <field name="end_date" widget="date_dynamic_min" 
                       options="{'min_date_field': 'start_date'}"/>
            </form>`,
    });

    expect("div[name='end_date']").toHaveCount(1);
    expect("div[name='start_date']").toHaveCount(1);
});

test("minDateField is applied from referenced field value", async function () {
    const { env } = await makeMockServer();
    const partnerId = env["partner"].create({
        name: "Test Partner",
        start_date: "2024-01-02 10:00:00",
    });

    await mountView({
        type: "form",
        resModel: "partner",
        resId: partnerId,
        arch: `
            <form>
                <field name="start_date"/>
                <field name="end_date" widget="date_dynamic_min" 
                       options="{'min_date_field': 'start_date'}"/>
            </form>`,
    });

    // Click on end_date to open datepicker
    await contains("input[id='end_date_0']").click();
    await animationFrame();

    // Datepicker should be visible
    const allCells = queryAll(".o_datetime_picker .o_date_item_cell");
    // The first day should be disabled because it's before the minDate'
    const dayBefore = allCells.find((el) => el.textContent.trim() === "1");
    expect(dayBefore).toHaveAttribute("disabled");
    expect(dayBefore).toHaveClass("opacity-50");
    // the day after should be enabled
    const dayAfter = allCells.find((el) => el.textContent.trim() === "3");
    expect(dayAfter).not.toHaveAttribute("disabled");
    expect(dayAfter).not.toHaveClass("opacity-50");
});

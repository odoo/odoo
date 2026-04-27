import { describe, expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    foo = fields.Integer({ aggregator: "sum" });

    _records = [
        {
            id: 1,
            foo: 12,
        },
        {
            id: 2,
            foo: 1,
        },
        {
            id: 3,
            foo: 17,
        },
        {
            id: 4,
            foo: 2,
        },
    ];
}

defineModels([Partner]);

describe.current.tags("mobile");

test("simple pivot rendering", async () => {
    expect.assertions(2);

    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: /* xml */ `
            <pivot string="Partners">
                <field name="foo" type="measure"/>
            </pivot>
        `,
    });

    expect(".o_pivot_view").toHaveClass("o_view_controller");
    expect("td.o_pivot_cell_value:contains(32)").toHaveCount(1, {
        message: "should contain a pivot cell with the sum of all records",
    });
});

test("unselecting all measures should not crash pivot rendering", async () => {
    expect.assertions(1);

    await mountView({
        type: "pivot",
        resModel: "partner",
        arch: /* xml */ `
            <pivot string="Partners">
                <field name="foo" type="measure"/>
            </pivot>
        `,
    });

    await click(".dropdown-toggle.btn.btn-primary:eq(1)");
    await animationFrame();
    await click(".dropdown-item.o_menu_item.selected:eq(0)");
    await animationFrame();
    expect("div.o_nocontent_help").toHaveCount(1, {
        message: "Instead of error action helper will appear",
    });
});

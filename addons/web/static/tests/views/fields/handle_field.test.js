import { expect, test } from "@odoo/hoot";
import { click, queryFirst } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import {
    defineModels,
    fields,
    MockServer,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    display_name = fields.Char({ string: "Displayed name", searchable: true });
    p = fields.One2many({ string: "one2many field", relation: "partner", searchable: true });
    sequence = fields.Integer({ string: "Sequence", searchable: true });
    _records = [
        {
            id: 1,
            display_name: "first record",
            p: [],
        },
        {
            id: 2,
            display_name: "second record",
            p: [],
            sequence: 4,
        },
        {
            id: 4,
            display_name: "aaa",
            sequence: 9,
        },
    ];
}
defineModels([Partner]);

test("HandleField in x2m", async () => {
    Partner._records[0].p = [2, 4];
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <field name="p">
                    <list editable="bottom">
                        <field name="sequence" widget="handle" />
                        <field name="display_name" />
                    </list>
                </field>
            </form>`,
    });

    expect("td span.o_row_handle").toHaveText("", {
        message: "handle should not have any content",
    });
    expect(queryFirst("td span.o_row_handle")).toBeVisible({
        message: "handle should be invisible",
    });

    expect("span.o_row_handle").toHaveCount(2, { message: "should have 2 handles" });

    expect(queryFirst("td")).toHaveClass("o_handle_cell", {
        message: "column widget should be displayed in css class",
    });
    await click("td:eq(1)");
    await animationFrame();

    expect("td:eq(0) span.o_row_handle").toHaveCount(1, {
        message: "content of the cell should have been replaced",
    });
});

test("HandleField with falsy values", async () => {
    onRpc("has_group", () => true);
    await mountView({
        type: "list",
        resModel: "partner",
        arch: /* xml */ `
            <list>
                <field name="sequence" widget="handle" />
                <field name="display_name" />
            </list>`,
    });

    expect(".o_row_handle:visible").toHaveCount(MockServer.env["partner"].length, {
        message: "there should be a visible handle for each record",
    });
});

test("HandleField in a readonly one2many", async () => {
    Partner._records[0].p = [1, 2, 4];

    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <field name="p" readonly="1">
                    <list editable="top">
                        <field name="sequence" widget="handle" />
                        <field name="display_name" />
                    </list>
                </field>
            </form>`,
        resId: 1,
    });

    expect(".o_row_handle.o_disabled").toHaveCount(3, {
        message: "there should be 3 handles but they should be disabled from readonly",
    });
});

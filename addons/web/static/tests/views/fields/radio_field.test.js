import { expect, test } from "@odoo/hoot";
import { check, click, queryRect } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import {
    clickSave,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    bar = fields.Boolean({ default: true });
    int_field = fields.Integer();
    trululu = fields.Many2one({ relation: "partner" });
    product_id = fields.Many2one({ relation: "product" });
    color = fields.Selection({
        selection: [
            ["red", "Red"],
            ["black", "Black"],
        ],
        default: "red",
    });
    _records = [
        {
            id: 1,
            display_name: "first record",
            bar: true,
            int_field: 10,
        },
        {
            id: 2,
            display_name: "second record",
        },
        {
            id: 3,
            display_name: "third record",
        },
    ];
}

class Product extends models.Model {
    display_name = fields.Char();
    _records = [
        {
            id: 37,
            display_name: "xphone",
        },
        {
            id: 41,
            display_name: "xpad",
        },
    ];
}

defineModels([Partner, Product]);

test("radio field on a many2one in a new record", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `<form><field name="product_id" widget="radio"/></form>`,
    });

    expect("div.o_radio_item").toHaveCount(2);
    expect("input.o_radio_input").toHaveCount(2);
    expect(".o_field_radio:first").toHaveText("xphone\nxpad");
    expect("input.o_radio_input:checked").toHaveCount(0);
});

test("required radio field on a many2one", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `<form><field name="product_id" widget="radio" required="1"/></form>`,
    });

    expect(".o_field_radio input:checked").toHaveCount(0);
    await clickSave();
    expect(".o_notification_title:first").toHaveText("Invalid fields:");
    expect(".o_notification_content:first").toHaveProperty(
        "innerHTML",
        "<ul><li>Product</li></ul>"
    );
    expect(".o_notification_bar:first").toHaveClass("bg-danger");
});

test("radio field change value by onchange", async () => {
    Partner._fields.bar = fields.Boolean({
        default: true,
        onChange: (obj) => {
            obj.product_id = obj.bar ? [41] : [37];
            obj.color = obj.bar ? "red" : "black";
        },
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <field name="bar" />
                <field name="product_id" widget="radio" />
                <field name="color" widget="radio" />
            </form>
        `,
    });

    await click(".o_field_boolean input[type='checkbox']");
    await animationFrame();
    expect("input.o_radio_input[data-value='37']").toBeChecked();
    expect("input.o_radio_input[data-value='black']").toBeChecked();

    await click(".o_field_boolean input[type='checkbox']");
    await animationFrame();
    expect("input.o_radio_input[data-value='41']").toBeChecked();
    expect("input.o_radio_input[data-value='red']").toBeChecked();
});

test("radio field on a selection in a new record", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `<form><field name="color" widget="radio"/></form>`,
    });

    expect("div.o_radio_item").toHaveCount(2);
    expect("input.o_radio_input").toHaveCount(2, { message: "should have 2 possible choices" });
    expect(".o_field_radio").toHaveText("Red\nBlack");

    // click on 2nd option
    await click("input.o_radio_input:eq(1)");
    await animationFrame();

    await clickSave();

    expect("input.o_radio_input[data-value=black]").toBeChecked({
        message: "should have saved record with correct value",
    });
});

test("two radio field with same selection", async () => {
    Partner._fields.color_2 = { ...Partner._fields.color };
    Partner._records[0].color = "black";
    Partner._records[0].color_2 = "black";

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <group>
                    <field name="color" widget="radio"/>
                </group>
                <group>
                    <field name="color_2" widget="radio"/>
                </group>
            </form>
        `,
    });

    expect("[name='color'] input.o_radio_input[data-value=black]").toBeChecked();
    expect("[name='color_2'] input.o_radio_input[data-value=black]").toBeChecked();

    // click on Red
    await click("[name='color_2'] label");
    await animationFrame();

    expect("[name='color'] input.o_radio_input[data-value=black]").toBeChecked();
    expect("[name='color_2'] input.o_radio_input[data-value=red]").toBeChecked();
});

test("radio field has o_horizontal or o_vertical class", async () => {
    Partner._fields.color2 = Partner._fields.color;

    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <group>
                    <field name="color" widget="radio" />
                    <field name="color2" widget="radio" options="{'horizontal': True}" />
                </group>
            </form>
        `,
    });

    expect(".o_field_radio > div.o_vertical").toHaveCount(1, {
        message: "should have o_vertical class",
    });

    const verticalRadio = ".o_field_radio > div.o_vertical:first";
    expect(`${verticalRadio} .o_radio_item:first`).toHaveRect({
        right: queryRect(`${verticalRadio} .o_radio_item:last`).right,
    });
    expect(".o_field_radio > div.o_horizontal").toHaveCount(1, {
        message: "should have o_horizontal class",
    });
    const horizontalRadio = ".o_field_radio > div.o_horizontal:first";
    expect(`${horizontalRadio} .o_radio_item:first`).toHaveRect({
        top: queryRect(`${horizontalRadio} .o_radio_item:last`).top,
    });
});

test("radio field with numerical keys encoded as strings", async () => {
    Partner._fields.selection = fields.Selection({
        selection: [
            ["0", "Red"],
            ["1", "Black"],
        ],
    });

    onRpc("partner", "web_save", ({ args }) => expect.step(args[1].selection));

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `<form><field name="selection" widget="radio"/></form>`,
    });
    expect(".o_field_widget").toHaveText("Red\nBlack");
    expect(".o_radio_input:checked").toHaveCount(0);

    await check("input.o_radio_input:last");
    await animationFrame();
    await clickSave();

    expect(".o_field_widget").toHaveText("Red\nBlack");
    expect(".o_radio_input[data-value='1']").toBeChecked();

    expect.verifySteps(["1"]);
});

test("radio field is empty", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 2,
        arch: /* xml */ `
            <form edit="0">
                <field name="trululu" widget="radio" />
            </form>
        `,
    });

    expect(".o_field_widget[name=trululu]").toHaveClass("o_field_empty");
    expect(".o_radio_input").toHaveCount(3);
    expect(".o_radio_input:disabled").toHaveCount(3);
    expect(".o_radio_input:checked").toHaveCount(0);
});

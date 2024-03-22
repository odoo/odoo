import { expect, test } from "@odoo/hoot";
import { click, queryFirst, queryLast } from "@odoo/hoot-dom";
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
    expect("input.o_radio_input:checked").toHaveCount(0, {
        message: "none of the input should be checked",
    });
});

test("required radio field on a many2one", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `<form><field name="product_id" widget="radio" required="1"/></form>`,
    });

    expect(".o_field_radio input:checked").toHaveCount(0, {
        message: "none of the input should be checked",
    });
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

    click(".o_field_boolean input[type='checkbox']");
    await animationFrame();
    expect("input.o_radio_input[data-value='37']").toBeChecked();
    expect("input.o_radio_input[data-value='black']").toBeChecked();

    click(".o_field_boolean input[type='checkbox']");
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
    click(queryLast("input.o_radio_input"));
    await animationFrame();

    await clickSave();

    expect("input.o_radio_input:checked").toHaveAttribute("data-value", "black", {
        message: "should have saved record with correct value",
    });
});

test("two radio field with same selection", async () => {
    Partner._fields.color_2 = Partner._fields.color;
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

    expect("[name='color'] input.o_radio_input:checked").toHaveAttribute("data-value", "black");
    expect("[name='color_2'] input.o_radio_input:checked").toHaveAttribute("data-value", "black");

    // click on Red
    click(queryFirst("[name='color_2'] label"));
    await animationFrame();
    expect("[name='color'] input.o_radio_input:checked").toHaveAttribute("data-value", "black");
    expect("[name='color_2'] input.o_radio_input:checked").toHaveAttribute("data-value", "red");
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

    const verticalRadio = queryFirst(".o_field_radio > div.o_vertical");
    const elementT = queryFirst(".o_radio_item", { root: verticalRadio });
    const elementB = queryLast(".o_radio_item", { root: verticalRadio });
    expect(elementT.getBoundingClientRect().right).toBe(elementB.getBoundingClientRect().right);
    expect(".o_field_radio > div.o_horizontal").toHaveCount(1, {
        message: "should have o_horizontal class",
    });
    const horizontalRadio = queryFirst(".o_field_radio > div.o_horizontal");
    const elementL = queryFirst(".o_radio_item", { root: horizontalRadio });
    const elementR = queryLast(".o_radio_item", { root: horizontalRadio });
    expect(elementL.getBoundingClientRect().top).toBe(elementR.getBoundingClientRect().top);
});

test("radio field with numerical keys encoded as strings", async () => {
    expect.assertions(5);

    Partner._fields.selection = {
        type: "selection",
        selection: [
            ["0", "Red"],
            ["1", "Black"],
        ],
    };

    onRpc((route, { args, method, model }) => {
        if (model === "partner" && method === "web_save") {
            expect(args[1].selection).toBe("1", { message: "should write correct value" });
        }
    });

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `<form><field name="selection" widget="radio"/></form>`,
    });
    expect(".o_field_widget").toHaveText("Red\nBlack");
    expect(".o_radio_input:checked").toHaveCount(0, { message: "no value should be checked" });

    click(queryLast("input.o_radio_input"));
    await animationFrame();
    await clickSave();

    expect(".o_field_widget").toHaveText("Red\nBlack");
    expect(".o_radio_input[data-index='1']:checked").toHaveCount(1, {
        message: "'Black' should be checked",
    });
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

import { expect, test } from "@odoo/hoot";
import {
    contains,
    defineModels,
    fieldInput,
    fields,
    models,
    mountView,
    onRpc,
    stepAllNetworkCalls,
} from "@web/../tests/web_test_helpers";

class Color extends models.Model {
    hex_color = fields.Char({ string: "hexadecimal color" });
    text = fields.Char();

    _records = [
        {
            id: 1,
        },
        {
            id: 2,
            hex_color: "#ff4444",
        },
    ];

    _views = {
        form: /* xml */ `
            <form>
                <group>
                    <field name="hex_color" widget="color"/>
                </group>
            </form>`,
        list: /* xml */ `
            <list editable="bottom">
                <field name="hex_color" widget="color" />
            </list>`,
    };
}
class User extends models.Model {
    _name = "res.users";

    name = fields.Char();

    has_group() {
        return true;
    }
}

defineModels([Color, User]);

test("field contains a color input", async () => {
    Color._onChanges.hex_color = () => {};
    await mountView({ type: "form", resModel: "color", resId: 1 });

    onRpc("onchange", ({ args }) => {
        expect.step(`onchange ${JSON.stringify(args)}`);
    });

    expect(".o_field_color input[type='color']").toHaveCount(1);

    expect(".o_field_color div").toHaveStyle(
        { backgroundColor: "rgba(0, 0, 0, 0)" },
        {
            message: "field has the transparent background if no color value has been selected",
        }
    );
    expect(".o_field_color input").toHaveValue("#000000");

    await contains(".o_field_color input", { visible: false }).edit("#fefefe");
    expect.verifySteps([
        'onchange [[1],{"hex_color":"#fefefe"},["hex_color"],{"hex_color":{},"display_name":{}}]',
    ]);
    expect(".o_field_color input").toHaveValue("#fefefe");
    expect(".o_field_color div").toHaveStyle({ backgroundColor: "rgb(254, 254, 254)" });
});

test("color field in editable list view", async () => {
    await mountView({ type: "list", resModel: "color", resId: 1 });

    expect(".o_field_color input[type='color']").toHaveCount(2);
    await contains(".o_field_color input", { visible: false }).click();
    expect(".o_data_row").not.toHaveClass("o_selected_row");
});

test("read-only color field in editable list view", async () => {
    await mountView({
        type: "list",
        resModel: "color",
        arch: `
        <list editable="bottom">
            <field name="hex_color" readonly="1" widget="color" />
        </list>`,
    });

    expect(".o_field_color input:disabled").toHaveCount(2);
});

test("color field read-only in model definition, in non-editable list", async () => {
    Color._fields.hex_color.readonly = true;
    await mountView({ type: "list", resModel: "color" });

    expect(".o_field_color input:disabled").toHaveCount(2);
});

test("color field change via anoter field's onchange", async () => {
    Color._onChanges.text = (obj) => {
        obj.hex_color = "#fefefe";
    };

    await mountView({
        type: "form",
        resModel: "color",
        resId: 1,
        arch: `
        <form>
            <field name="text" />
            <field name="hex_color" widget="color" />
        </form>
    `,
    });

    onRpc("onchange", ({ args }) => {
        expect.step(`onchange ${JSON.stringify(args)}`);
    });

    expect(".o_field_color div").toHaveStyle(
        { backgroundColor: "rgba(0, 0, 0, 0)" },
        {
            message: "field has the transparent background if no color value has been selected",
        }
    );
    expect(".o_field_color input").toHaveValue("#000000");
    await fieldInput("text").edit("someValue");
    expect.verifySteps([
        'onchange [[1],{"text":"someValue"},["text"],{"text":{},"hex_color":{},"display_name":{}}]',
    ]);
    expect(".o_field_color input").toHaveValue("#fefefe");
    expect(".o_field_color div").toHaveStyle({ backgroundColor: "rgb(254, 254, 254)" });
});

test.tags("desktop");
test(`color field in form view => no automatic save by default`, async () => {
    stepAllNetworkCalls();
    await mountView({
        resModel: "color",
        type: "form",
    });

    await contains(`input[type=color]`, { visible: false }).edit("#fefefe");

    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "onchange",
    ]);
});

test.tags("desktop");
test(`color field in list view => automatic save by default`, async () => {
    stepAllNetworkCalls();
    await mountView({
        resModel: "color",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="text"/>
                <field name="hex_color" widget="color"/>
            </list>`,
    });

    await contains(`.o_data_row:eq(0) input[type=color]`, { visible: false }).edit("#fefefe");

    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
        "has_group",
        "web_save",
    ]);
});

test.tags("desktop");
test(`color field in list view => no save if autosave is false`, async () => {
    stepAllNetworkCalls();
    await mountView({
        resModel: "color",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="text"/>
                <field name="hex_color" widget="color" options="{'autosave': 0}"/>
            </list>`,
    });

    await contains(`.o_data_row:eq(0) input[type=color]`, { visible: false }).edit("#fefefe");

    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
        "has_group",
    ]);
});

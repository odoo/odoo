import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    is_raining_outside = fields.Boolean();
    mood = fields.Selection({
        selection: [
            ["happy", "Happy"],
            ["sad", "Sad"],
        ],
    });
    color = fields.Selection({
        selection: [
            ["white", "White"],
            ["grey", "Grey"],
            ["black", "Black"],
        ],
    });
    _records = [
        {
            id: 1,
            display_name: "first record",
            is_raining_outside: false,
            mood: "happy",
            color: "white",
        },
    ];
}

defineMailModels();
defineModels([Partner]);

test("radio selection field with filter, empty list", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <field name="color" widget="radio_selection_with_filter"
                       context="{'allowed_selection': []}" />
            </form>
        `,
    });

    expect(".o_radio_input").not.toBeVisible();
});

test("radio selection field with filter, single choice", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <field name="color" widget="radio_selection_with_filter"
                       context="{'allowed_selection': ['grey']}" />
            </form>
        `,
    });

    expect(".o_radio_input").toHaveCount(1);
    expect("input[data-value='white']").not.toBeVisible();
    expect("input[data-value='grey']").toBeVisible();
    expect("input[data-value='black']").not.toBeVisible();
});

test("radio selection field with filter, all choices", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <field name="color" widget="radio_selection_with_filter"
                       context="{'allowed_selection': ['white', 'grey', 'black']}" />
            </form>
        `,
    });

    expect(".o_radio_input").toHaveCount(3);
    expect("input[data-value='white']").toBeVisible();
    expect("input[data-value='grey']").toBeVisible();
    expect("input[data-value='black']").toBeVisible();
});

test("radio selection field with filter, synchronize with other field", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <group>
                    <field name="is_raining_outside" />
                    <field name="mood" widget="radio_selection_with_filter"
                           context="{'allowed_selection':
                                ['happy']
                                + (['sad'] if is_raining_outside else [])
                           }" />
                </group>
            </form>
        `,
    });
    // not raining outside => sad should be invisible
    expect("[name='is_raining_outside'] input").not.toBeChecked();
    expect("div[name='mood'] .o_radio_input").toHaveCount(1);
    expect("input[data-value='happy']").toBeVisible();
    expect("input[data-value='sad']").not.toBeVisible();

    await click("[name='is_raining_outside'] input");
    await animationFrame();

    // raining outside => sad should be visible
    expect("[name='is_raining_outside'] input").toBeChecked();
    expect("div[name='mood'] .o_radio_input").toHaveCount(2);
    expect("input[data-value='happy']").toBeVisible();
    expect("input[data-value='sad']").toBeVisible();

    await click("[name='is_raining_outside'] input");
    await animationFrame();

    // not raining outside => sad should be invisible
    expect("[name='is_raining_outside'] input").not.toBeChecked();
    expect("div[name='mood'] .o_radio_input").toHaveCount(1);
    expect("input[data-value='happy']").toBeVisible();
    expect("input[data-value='sad']").not.toBeVisible();
});

test("radio selection field with filter, cross radio synchronization", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <group>
                    <field name="mood" widget="radio_selection_with_filter"
                        context="{'allowed_selection':
                            (['happy'] if color != 'black' else [])
                            + (['sad'] if color != 'white' else [])
                        }"

                    />
                    <field name="color" widget="radio_selection_with_filter"
                           context="{'allowed_selection':
                                (['white'] if mood == 'happy' else [])
                                + ['grey']
                                + (['black'] if mood == 'sad' else [])
                           }" />
                </group>
            </form>
        `,
    });

    // happy and white by default, sad and black should be invisible
    expect("div[name='mood'] .o_radio_input").toHaveCount(1);
    expect("div[name='color'] .o_radio_input").toHaveCount(2);
    expect("input[data-value='happy']").toBeVisible();
    expect("input[data-value='sad']").not.toBeVisible();
    expect("input[data-value='white']").toBeVisible();
    expect("input[data-value='grey']").toBeVisible();
    expect("input[data-value='black']").not.toBeVisible();

    await click("[name='color'] input[data-value='grey']");
    await animationFrame();

    // happy and grey, sad should be revealed
    expect("div[name='mood'] .o_radio_input").toHaveCount(2);
    expect("div[name='color'] .o_radio_input").toHaveCount(2);
    expect("input[data-value='happy']").toBeVisible();
    expect("input[data-value='sad']").toBeVisible();
    expect("input[data-value='white']").toBeVisible();
    expect("input[data-value='grey']").toBeVisible();
    expect("input[data-value='black']").not.toBeVisible();

    await click("div[name='mood'] input[data-value='sad']");
    await animationFrame();

    // sad and grey, white should disappear and black should appear
    expect("div[name='mood'] .o_radio_input").toHaveCount(2);
    expect("div[name='color'] .o_radio_input").toHaveCount(2);
    expect("input[data-value='happy']").toBeVisible();
    expect("input[data-value='sad']").toBeVisible();
    expect("input[data-value='white']").not.toBeVisible();
    expect("input[data-value='grey']").toBeVisible();
    expect("input[data-value='black']").toBeVisible();

    await click("div[name='color'] input[data-value='black']");
    await animationFrame();

    // sad and black, happy should disappear
    expect("div[name='mood'] .o_radio_input").toHaveCount(1);
    expect("div[name='color'] .o_radio_input").toHaveCount(2);
    expect("input[data-value='happy']").not.toBeVisible();
    expect("input[data-value='sad']").toBeVisible();
    expect("input[data-value='white']").not.toBeVisible();
    expect("input[data-value='grey']").toBeVisible();
    expect("input[data-value='black']").toBeVisible();
});

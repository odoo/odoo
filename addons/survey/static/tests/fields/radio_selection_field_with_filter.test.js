import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { animationFrame, click } from "@odoo/hoot-dom";
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
    allowed_colors = fields.Json();
    allowed_moods = fields.Json();

    _onChanges = {
        is_raining_outside(record) {
            record.allowed_moods = ["happy"] + (record.is_raining_outside ? ["sad"] : []);
        },
        color(record) {
            record.allowed_moods =
                (record.color !== "black" ? ["happy"] : []) +
                (record.color !== "white" ? ["sad"] : []);
        },
        mood(record) {
            record.allowed_colors =
                (record.mood === "happy" ? ["white"] : []) +
                ["grey"] +
                (record.mood === "sad" ? ["black"] : []);
        },
    };

    _records = [
        {
            id: 1,
            allowed_colors: "['white', 'grey']",
            allowed_moods: "['happy']",
            display_name: "first record",
            is_raining_outside: false,
            mood: "happy",
            color: "white",
        },
    ];
}

defineMailModels();
defineModels([Partner]);

const formArchColorsOnly = /* xml */ `
    <form>
        <field name="is_raining_outside"/>
        <field name="allowed_colors" invisible="1"/>
        <field name="color" widget="radio_selection_with_filter"
            options="{'allowed_selection_field': 'allowed_colors'}"/>
    </form>
`;

const formArchFull = /* xml */ `
    <form>
        <field name="is_raining_outside"/>
        <field name="allowed_moods" invisible="1"/>
        <field name="allowed_colors" invisible="1"/>
        <field name="mood" widget="radio_selection_with_filter"
            options="{'allowed_selection_field': 'allowed_moods'}"/>
        <field name="color" widget="radio_selection_with_filter"
            options="{'allowed_selection_field': 'allowed_colors'}"/>
    </form>
`;

test("radio selection field with filter, empty list", async () => {
    Partner._records[0].allowed_colors = [];
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: formArchColorsOnly,
    });

    expect(".o_selection_badge").toHaveCount(0);
});

test("radio selection field with filter, single choice", async () => {
    Partner._records[0].allowed_colors = ["grey"];
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: formArchColorsOnly,
    });

    expect(".o_radio_input").toHaveCount(1);
    expect("input[data-value='white']").toHaveCount(0);
    expect("input[data-value='grey']").toBeVisible();
    expect("input[data-value='black']").toHaveCount(0);
});

test("radio selection field with filter, all choices", async () => {
    Partner._records[0].allowed_colors = ["white", "grey", "black"];
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: formArchColorsOnly,
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
        arch: formArchFull,
    });
    // not raining outside => sad should be invisible
    expect("[name='is_raining_outside'] input").not.toBeChecked();
    expect("div[name='mood'] .o_radio_input").toHaveCount(1);
    expect("input[data-value='happy']").toBeVisible();
    expect("input[data-value='sad']").toHaveCount(0);

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
    expect("input[data-value='sad']").toHaveCount(0);
});

test("radio selection field with filter, cross radio synchronization", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: formArchFull,
    });

    // happy and white by default, sad and black should be invisible
    expect("div[name='mood'] .o_radio_input").toHaveCount(1);
    expect("div[name='color'] .o_radio_input").toHaveCount(2);
    expect("input[data-value='happy']").toBeVisible();
    expect("input[data-value='sad']").toHaveCount(0);
    expect("input[data-value='white']").toBeVisible();
    expect("input[data-value='grey']").toBeVisible();
    expect("input[data-value='black']").toHaveCount(0);

    await click("[name='color'] input[data-value='grey']");
    await animationFrame();

    // happy and grey, sad should be revealed
    expect("div[name='mood'] .o_radio_input").toHaveCount(2);
    expect("div[name='color'] .o_radio_input").toHaveCount(2);
    expect("input[data-value='happy']").toBeVisible();
    expect("input[data-value='sad']").toBeVisible();
    expect("input[data-value='white']").toBeVisible();
    expect("input[data-value='grey']").toBeVisible();
    expect("input[data-value='black']").toHaveCount(0);

    await click("div[name='mood'] input[data-value='sad']");
    await animationFrame();

    // sad and grey, white should disappear and black should appear
    expect("div[name='mood'] .o_radio_input").toHaveCount(2);
    expect("div[name='color'] .o_radio_input").toHaveCount(2);
    expect("input[data-value='happy']").toBeVisible();
    expect("input[data-value='sad']").toBeVisible();
    expect("input[data-value='white']").toHaveCount(0);
    expect("input[data-value='grey']").toBeVisible();
    expect("input[data-value='black']").toBeVisible();

    await click("div[name='color'] input[data-value='black']");
    await animationFrame();

    // sad and black, happy should disappear
    expect("div[name='mood'] .o_radio_input").toHaveCount(1);
    expect("div[name='color'] .o_radio_input").toHaveCount(2);
    expect("input[data-value='happy']").toHaveCount(0);
    expect("input[data-value='sad']").toBeVisible();
    expect("input[data-value='white']").toHaveCount(0);
    expect("input[data-value='grey']").toBeVisible();
    expect("input[data-value='black']").toBeVisible();
});

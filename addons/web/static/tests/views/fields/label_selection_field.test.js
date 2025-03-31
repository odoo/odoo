import { expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { defineModels, fields, models, mountView, onRpc } from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    foo = fields.Char();
    selection = fields.Selection({
        selection: [
            ["normal", "Normal"],
            ["blocked", "Blocked"],
            ["done", "Done"],
        ],
    });
    _records = [
        {
            foo: "yop",
            selection: "blocked",
        },
        {
            foo: "blip",
            selection: "normal",
        },
        {
            foo: "abc",
            selection: "done",
        },
    ];
}
defineModels([Partner]);

test("LabelSelectionField in form view", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="selection" widget="label_selection"
                        options="{'classes': {'normal': 'secondary', 'blocked': 'warning','done': 'success'}}"/>
                    </group>
                </sheet>
            </form>`,
        resId: 1,
    });

    expect(".o_field_widget .badge.text-bg-warning").toHaveCount(1, {
        message: "should have a warning status label since selection is the second, blocked state",
    });
    expect(".o_field_widget .badge.text-bg-secondary").toHaveCount(0, {
        message: "should not have a default status since selection is the second, blocked state",
    });
    expect(".o_field_widget .badge.text-bg-success").toHaveCount(0, {
        message: "should not have a success status since selection is the second, blocked state",
    });
    expect(".o_field_widget .badge.text-bg-warning").toHaveText("Blocked", {
        message: "the label should say 'Blocked' since this is the label value for that state",
    });
});

test("LabelSelectionField in editable list view", async () => {
    onRpc("has_group", () => true);

    await mountView({
        type: "list",
        resModel: "partner",
        arch: /* xml */ `
            <list editable="bottom">
                <field name="foo"/>
                <field name="selection" widget="label_selection"
                options="{'classes': {'normal': 'secondary', 'blocked': 'warning','done': 'success'}}"/>
            </list>`,
    });

    expect(".o_field_widget .badge:not(:empty)").toHaveCount(3, {
        message: "should have three visible status labels",
    });
    expect(".o_field_widget .badge.text-bg-warning").toHaveCount(1, {
        message: "should have one warning status label",
    });
    expect(".o_field_widget .badge.text-bg-warning").toHaveText("Blocked", {
        message: "the warning label should read 'Blocked'",
    });
    expect(".o_field_widget .badge.text-bg-secondary").toHaveCount(1, {
        message: "should have one default status label",
    });
    expect(".o_field_widget .badge.text-bg-secondary").toHaveText("Normal", {
        message: "the default label should read 'Normal'",
    });
    expect(".o_field_widget .badge.text-bg-success").toHaveCount(1, {
        message: "should have one success status label",
    });
    expect(".o_field_widget .badge.text-bg-success").toHaveText("Done", {
        message: "the success label should read 'Done'",
    });

    // switch to edit mode and check the result
    await click("tbody td:not(.o_list_record_selector)");
    await animationFrame();

    expect(".o_field_widget .badge:not(:empty)").toHaveCount(3, {
        message: "should have three visible status labels",
    });
    expect(".o_field_widget .badge.text-bg-warning").toHaveCount(1, {
        message: "should have one warning status label",
    });
    expect(".o_field_widget .badge.text-bg-warning").toHaveText("Blocked", {
        message: "the warning label should read 'Blocked'",
    });
    expect(".o_field_widget .badge.text-bg-secondary").toHaveCount(1, {
        message: "should have one default status label",
    });
    expect(".o_field_widget .badge.text-bg-secondary").toHaveText("Normal", {
        message: "the default label should read 'Normal'",
    });
    expect(".o_field_widget .badge.text-bg-success").toHaveCount(1, {
        message: "should have one success status label",
    });
    expect(".o_field_widget .badge.text-bg-success").toHaveText("Done", {
        message: "the success label should read 'Done'",
    });

    // save and check the result
    await click(".o_control_panel_main_buttons .o_list_button_save");
    await animationFrame();
    expect(".o_field_widget .badge:not(:empty)").toHaveCount(3, {
        message: "should have three visible status labels",
    });
    expect(".o_field_widget .badge.text-bg-warning").toHaveCount(1, {
        message: "should have one warning status label",
    });
    expect(".o_field_widget .badge.text-bg-warning").toHaveText("Blocked", {
        message: "the warning label should read 'Blocked'",
    });
    expect(".o_field_widget .badge.text-bg-secondary").toHaveCount(1, {
        message: "should have one default status label",
    });
    expect(".o_field_widget .badge.text-bg-secondary").toHaveText("Normal", {
        message: "the default label should read 'Normal'",
    });
    expect(".o_field_widget .badge.text-bg-success").toHaveCount(1, {
        message: "should have one success status label",
    });
    expect(".o_field_widget .badge.text-bg-success").toHaveText("Done", {
        message: "the success label should read 'Done'",
    });
});

import { expect, test } from "@odoo/hoot";
import { click, press, queryAll, queryAllTexts, queryFirst } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { defineModels, fields, models, mountView, onRpc } from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    foo = fields.Char({ string: "Foo" });
    sequence = fields.Integer({ string: "Sequence", searchable: true });
    selection = fields.Selection({
        string: "Selection",
        selection: [
            ["normal", "Normal"],
            ["blocked", "Blocked"],
            ["done", "Done"],
        ],
    });

    _records = [
        { id: 1, foo: "yop", selection: "blocked" },
        { id: 2, foo: "blip", selection: "normal" },
        { id: 4, foo: "abc", selection: "done" },
        { id: 3, foo: "gnap" },
        { id: 5, foo: "blop" },
    ];
}

defineModels([Partner]);

test("StateSelectionField in form view", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="selection" widget="state_selection"/>
                    </group>
                </sheet>
            </form>
        `,
        resId: 1,
    });

    expect(".o_field_widget.o_field_state_selection span.o_status.o_status_red").toHaveCount(1, {
        message: "should have one red status since selection is the second, blocked state",
    });
    expect(".o_field_widget.o_field_state_selection span.o_status.o_status_green").toHaveCount(0, {
        message: "should not have one green status since selection is the second, blocked state",
    });
    expect(".o-dropdown--menu").toHaveCount(0, { message: "there should not be a dropdown" });

    // Click on the status button to make the dropdown appear
    await click(".o_field_widget.o_field_state_selection .o_status");
    await animationFrame();
    expect(".o-dropdown--menu").toHaveCount(1, { message: "there should be a dropdown" });
    expect(".o-dropdown--menu .dropdown-item").toHaveCount(3, {
        message: "there should be three options in the dropdown",
    });
    expect(".o-dropdown--menu .dropdown-item:nth-child(2)").toHaveClass("active", {
        message: "current value has a checkmark",
    });

    // Click on the first option, "Normal"
    await click(".o-dropdown--menu .dropdown-item");
    await animationFrame();
    expect(".o-dropdown--menu").toHaveCount(0, {
        message: "there should not be a dropdown anymore",
    });
    expect(".o_field_widget.o_field_state_selection span.o_status.o_status_red").toHaveCount(0, {
        message: "should not have one red status since selection is the first, normal state",
    });
    expect(".o_field_widget.o_field_state_selection span.o_status.o_status_green").toHaveCount(0, {
        message: "should not have one green status since selection is the first, normal state",
    });
    expect(".o_field_widget.o_field_state_selection span.o_status").toHaveCount(1, {
        message: "should have one grey status since selection is the first, normal state",
    });

    expect(".o-dropdown--menu").toHaveCount(0, { message: "there should still not be a dropdown" });
    expect(".o_field_widget.o_field_state_selection span.o_status.o_status_red").toHaveCount(0, {
        message: "should still not have one red status since selection is the first, normal state",
    });
    expect(".o_field_widget.o_field_state_selection span.o_status.o_status_green").toHaveCount(0, {
        message:
            "should still not have one green status since selection is the first, normal state",
    });
    expect(".o_field_widget.o_field_state_selection span.o_status").toHaveCount(1, {
        message: "should still have one grey status since selection is the first, normal state",
    });

    // Click on the status button to make the dropdown appear
    await click(".o_field_widget.o_field_state_selection .o_status");
    await animationFrame();
    expect(".o-dropdown--menu .dropdown-item").toHaveCount(3, {
        message: "there should be three options in the dropdown",
    });

    // Click on the last option, "Done"
    await click(".o-dropdown--menu .dropdown-item:last-child");
    await animationFrame();
    expect(".o-dropdown--menu").toHaveCount(0, {
        message: "there should not be a dropdown anymore",
    });
    expect(".o_field_widget.o_field_state_selection span.o_status.o_status_red").toHaveCount(0, {
        message: "should not have one red status since selection is the third, done state",
    });
    expect(".o_field_widget.o_field_state_selection span.o_status.o_status_green").toHaveCount(1, {
        message: "should have one green status since selection is the third, done state",
    });

    // save
    await click(".o_form_button_save");
    await animationFrame();
    expect(".o-dropdown--menu").toHaveCount(0, {
        message: "there should still not be a dropdown anymore",
    });
    expect(".o_field_widget.o_field_state_selection span.o_status.o_status_red").toHaveCount(0, {
        message: "should still not have one red status since selection is the third, done state",
    });
    expect(".o_field_widget.o_field_state_selection span.o_status.o_status_green").toHaveCount(1, {
        message: "should still have one green status since selection is the third, done state",
    });
});

test("Check role attribute for dropdown items", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="selection" widget="state_selection"/>
                    </group>
                </sheet>
            </form>
        `,
        resId: 1,
    });

    // Open the dropdown
    click(".o_field_widget.o_field_state_selection .o_status");
    await animationFrame();

    // Assert that the dropdown is open
    expect(".o-dropdown--menu").toHaveCount(1, { message: "there should be a dropdown" });

    // Assert that each dropdown item has role="checkbox"
    expect(queryFirst(".o-dropdown--menu .dropdown-item")).toHaveAttribute(
        "role",
        "menuitemcheckbox"
    );
});

test("StateSelectionField with readonly modifier", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `<form><field name="selection" widget="state_selection" readonly="1"/></form>`,
        resId: 1,
    });

    expect(".o_field_state_selection").toHaveClass("o_readonly_modifier");
    expect(".o_field_state_selection button").toHaveClass("o_disabled");
    expect(".dropdown-menu").not.toBeVisible();
    await click(".o_field_state_selection span.o_status");
    await animationFrame();
    expect(".dropdown-menu").not.toBeVisible();
});

test("StateSelectionField for form view with hide_label option", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <field name="selection" widget="state_selection" options="{'hide_label': False}"/>
            </form>
        `,
        resId: 1,
    });
    expect(".o_status_label").toHaveCount(1);
});

test("StateSelectionField for list view with hide_label option", async () => {
    onRpc("has_group", () => true);
    Partner._fields.graph_type = fields.Selection({
        type: "selection",
        selection: [
            ["line", "Line"],
            ["bar", "Bar"],
        ],
    });
    Partner._records[0].graph_type = "bar";
    Partner._records[1].graph_type = "line";

    await mountView({
        type: "list",
        resModel: "partner",
        arch: /* xml */ `
            <list>
                <field name="graph_type" widget="state_selection" options="{'hide_label': True}"/>
                <field name="selection" widget="state_selection" options="{'hide_label': False}"/>
            </list>
        `,
    });

    expect(".o_state_selection_cell .o_field_state_selection span.o_status").toHaveCount(10, {
        message: "should have ten status selection widgets",
    });
    const selector =
        ".o_state_selection_cell .o_field_state_selection[name=selection] span.o_status_label";
    expect(selector).toHaveCount(5, { message: "should have five label on selection widgets" });
    expect(`${selector}:contains("Done")`).toHaveCount(1, {
        message: "should have one Done status label",
    });
    expect(`${selector}:contains("Normal")`).toHaveCount(3, {
        message: "should have three Normal status label",
    });

    expect(
        ".o_state_selection_cell .o_field_state_selection[name=graph_type] span.o_status"
    ).toHaveCount(5, { message: "should have five status selection widgets" });
    expect(
        ".o_state_selection_cell .o_field_state_selection[name=graph_type] span.o_status_label"
    ).toHaveCount(0, { message: "should not have status label in selection widgets" });
});

test("StateSelectionField in editable list view", async () => {
    onRpc("has_group", () => true);
    await mountView({
        type: "list",
        resModel: "partner",
        arch: /* xml */ `
            <list editable="bottom">
                <field name="foo"/>
                <field name="selection" widget="state_selection"/>
            </list>
        `,
    });

    expect(".o_state_selection_cell .o_field_state_selection span.o_status").toHaveCount(5, {
        message: "should have five status selection widgets",
    });
    expect(
        ".o_state_selection_cell .o_field_state_selection span.o_status.o_status_red"
    ).toHaveCount(1, { message: "should have one red status" });
    expect(
        ".o_state_selection_cell .o_field_state_selection span.o_status.o_status_green"
    ).toHaveCount(1, { message: "should have one green status" });
    expect(".o-dropdown--menu").toHaveCount(0, { message: "there should not be a dropdown" });

    // Click on the status button to make the dropdown appear
    let cell = queryFirst("tbody td.o_state_selection_cell");
    await click(".o_state_selection_cell .o_field_state_selection span.o_status");
    await animationFrame();
    expect(cell.parentElement).not.toHaveClass("o_selected_row", {
        message: "should not be in edit mode since we clicked on the state selection widget",
    });
    expect(".o-dropdown--menu").toHaveCount(1, { message: "there should be a dropdown" });
    expect(".o-dropdown--menu .dropdown-item").toHaveCount(3, {
        message: "there should be three options in the dropdown",
    });

    // Click on the first option, "Normal"
    await click(".o-dropdown--menu .dropdown-item");
    await animationFrame();
    expect(".o_state_selection_cell .o_field_state_selection span.o_status").toHaveCount(5, {
        message: "should still have five status selection widgets",
    });
    expect(
        ".o_state_selection_cell .o_field_state_selection span.o_status.o_status_red"
    ).toHaveCount(0, { message: "should now have no red status" });
    expect(
        ".o_state_selection_cell .o_field_state_selection span.o_status.o_status_green"
    ).toHaveCount(1, { message: "should still have one green status" });
    expect(".o-dropdown--menu").toHaveCount(0, { message: "there should not be a dropdown" });
    expect("tr.o_selected_row").toHaveCount(0, { message: "should not be in edit mode" });

    // switch to edit mode and check the result
    cell = queryFirst("tbody td.o_state_selection_cell");
    await click(cell);
    await animationFrame();
    expect(cell.parentElement).toHaveClass("o_selected_row", {
        message: "should now be in edit mode",
    });
    expect(".o_state_selection_cell .o_field_state_selection span.o_status").toHaveCount(5, {
        message: "should still have five status selection widgets",
    });
    expect(
        ".o_state_selection_cell .o_field_state_selection span.o_status.o_status_red"
    ).toHaveCount(0, { message: "should now have no red status" });
    expect(
        ".o_state_selection_cell .o_field_state_selection span.o_status.o_status_green"
    ).toHaveCount(1, { message: "should still have one green status" });
    expect(".o-dropdown--menu").toHaveCount(0, { message: "there should not be a dropdown" });

    // Click on the status button to make the dropdown appear
    await click(".o_state_selection_cell .o_field_state_selection span.o_status");
    await animationFrame();
    expect(".o-dropdown--menu").toHaveCount(1, { message: "there should be a dropdown" });
    expect(".o-dropdown--menu .dropdown-item").toHaveCount(3, {
        message: "there should be three options in the dropdown",
    });

    // Click on another row
    const lastCell = queryAll("tbody td.o_state_selection_cell")[4];
    await click(lastCell);
    await animationFrame();
    expect(".o-dropdown--menu").toHaveCount(0, {
        message: "there should not be a dropdown anymore",
    });
    const firstCell = queryFirst("tbody td.o_state_selection_cell");
    expect(firstCell.parentElement).not.toHaveClass("o_selected_row", {
        message: "first row should not be in edit mode anymore",
    });
    expect(lastCell.parentElement).toHaveClass("o_selected_row", {
        message: "last row should be in edit mode",
    });

    // Click on the third status button to make the dropdown appear
    await click(".o_state_selection_cell .o_field_state_selection span.o_status:eq(2)");
    await animationFrame();
    expect(".o-dropdown--menu").toHaveCount(1, "there should be a dropdown".msg);
    expect(".o-dropdown--menu .dropdown-item").toHaveCount(3, {
        message: "there should be three options in the dropdown",
    });

    // Click on the last option, "Done"
    await click(".o-dropdown--menu .dropdown-item:last-child");
    await animationFrame();
    expect(".o-dropdown--menu").toHaveCount(0, {
        message: "there should not be a dropdown anymore",
    });
    expect(".o_state_selection_cell .o_field_state_selection span.o_status").toHaveCount(5, {
        message: "should still have five status selection widgets",
    });
    expect(
        ".o_state_selection_cell .o_field_state_selection span.o_status.o_status_red"
    ).toHaveCount(0, { message: "should still have no red status" });
    expect(
        ".o_state_selection_cell .o_field_state_selection span.o_status.o_status_green"
    ).toHaveCount(2, { message: "should now have two green status" });
    expect(".o-dropdown--menu").toHaveCount(0, { message: "there should not be a dropdown" });

    // save
    await click(".o_control_panel_main_buttons .o_list_button_save");
    await animationFrame();
    expect(".o_state_selection_cell .o_field_state_selection span.o_status").toHaveCount(5, {
        message: "should have five status selection widgets",
    });
    expect(
        ".o_state_selection_cell .o_field_state_selection span.o_status.o_status_red"
    ).toHaveCount(0, { message: "should have no red status" });
    expect(
        ".o_state_selection_cell .o_field_state_selection span.o_status.o_status_green"
    ).toHaveCount(2, { message: "should have two green status" });
    expect(".o-dropdown--menu").toHaveCount(0, { message: "there should not be a dropdown" });
});

test('StateSelectionField edited by the smart actions "Set kanban state as <state name>"', async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <field name="selection" widget="state_selection"/>
            </form>
        `,
        resId: 1,
    });

    expect(".o_status_red").toHaveCount(1);
    await press(["control", "k"]);
    await animationFrame();
    expect(`.o_command:contains("Set kanban state as Normal\nALT + D")`).toHaveCount(1);
    const doneItem = `.o_command:contains("Set kanban state as Done\nALT + G")`;
    expect(doneItem).toHaveCount(1);

    await click(doneItem);
    await animationFrame();
    expect(".o_status_green").toHaveCount(1);

    await press(["control", "k"]);
    await animationFrame();
    expect(`.o_command:contains("Set kanban state as Normal\nALT + D")`).toHaveCount(1);
    expect(`.o_command:contains("Set kanban state as Blocked\nALT + F")`).toHaveCount(1);
    expect(`.o_command:contains("Set kanban state as Done\nALT + G")`).toHaveCount(0);
});

test("StateSelectionField uses legend_* fields", async () => {
    Partner._fields.legend_normal = fields.Char();
    Partner._fields.legend_blocked = fields.Char();
    Partner._fields.legend_done = fields.Char();
    Partner._records[0].legend_normal = "Custom normal";
    Partner._records[0].legend_blocked = "Custom blocked";
    Partner._records[0].legend_done = "Custom done";

    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="legend_normal" invisible="1" />
                        <field name="legend_blocked" invisible="1" />
                        <field name="legend_done" invisible="1" />
                        <field name="selection" widget="state_selection"/>
                    </group>
                </sheet>
            </form>
        `,
        resId: 1,
    });

    await click(".o_status");
    await animationFrame();
    expect(queryAllTexts(".o-dropdown--menu .dropdown-item")).toEqual([
        "Custom normal",
        "Custom blocked",
        "Custom done",
    ]);

    await click(".dropdown-item .o_status");
    await animationFrame();
    await click(".o_status");
    await animationFrame();
    expect(queryAllTexts(".o-dropdown--menu .dropdown-item")).toEqual([
        "Custom normal",
        "Custom blocked",
        "Custom done",
    ]);
});

test("works when required in a readonly view", async () => {
    Partner._records[0].selection = "normal";
    Partner._records = [Partner._records[0]];
    onRpc("web_save", ({ method }) => expect.step(method));
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: /* xml */ `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="selection" widget="state_selection" required="1"/>
                    </t>
                </templates>
            </kanban>
        `,
    });
    expect(".o_status_label").toHaveCount(0);
    await click(".o_field_state_selection button");
    await animationFrame();
    await click(".dropdown-item:eq(2)");
    await animationFrame();
    expect.verifySteps(["web_save"]);
    expect(".o_field_state_selection span").toHaveClass("o_status_green");
});

test("StateSelectionField - auto save record when field toggled", async () => {
    onRpc("web_save", ({ method }) => expect.step(method));
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="selection" widget="state_selection"/>
                    </group>
                </sheet>
            </form>
        `,
        resId: 1,
    });

    await click(".o_field_widget.o_field_state_selection .o_status");
    await animationFrame();
    await click(".dropdown-menu .dropdown-item:last-child");
    await animationFrame();
    expect.verifySteps(["web_save"]);
});

test("StateSelectionField -  prevent auto save with autosave option", async () => {
    onRpc("write", ({ method }) => expect.step(method));
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="selection" widget="state_selection" options="{'autosave': False}"/>
                    </group>
                </sheet>
            </form>
        `,
        resId: 1,
    });

    await click(".o_field_widget.o_field_state_selection .o_status");
    await animationFrame();
    await click(".dropdown-menu .dropdown-item:last-child");
    await animationFrame();
    expect.verifySteps([]);
});

test("StateSelectionField - hotkey handling when there are more than 3 options available", async () => {
    Partner._fields.selection = fields.Selection({
        string: "Selection",
        selection: [
            ["normal", "Normal"],
            ["blocked", "Blocked"],
            ["done", "Done"],
            ["martin", "Martin"],
            ["martine", "Martine"],
        ],
    });
    Partner._records[0].selection = null;

    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="selection" widget="state_selection" options="{'autosave': False}"/>
                    </group>
                </sheet>
            </form>
        `,
        resId: 1,
    });

    await click(".o_field_widget.o_field_state_selection .o_status");
    await animationFrame();
    expect(".dropdown-menu .dropdown-item").toHaveCount(5, {
        message: "Five choices are displayed",
    });
    await press(["control", "k"]);
    await animationFrame();

    expect(".o_command#o_command_2").toHaveText("Set kanban state as Done\nALT + G", {
        message: "hotkey and command are present",
    });
    expect(".o_command#o_command_4").toHaveText("Set kanban state as Martine", {
        message: "no hotkey is present, but the command exists",
    });

    await click(".o_command#o_command_2");
    await animationFrame();
    expect(".o_field_state_selection .o_status").toHaveClass("o_status_green", {
        message: "green color and Done state have been set",
    });
});

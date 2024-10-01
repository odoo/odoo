import { expect, test } from "@odoo/hoot";
import { click, hover, leave, press, queryAll, queryAllTexts } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { defineModels, fields, models, mountView, onRpc } from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    foo = fields.Char({ string: "Foo" });
    id = fields.Integer({ string: "Sequence" });
    selection = fields.Selection({
        string: "Selection",
        selection: [
            ["normal", "Normal"],
            ["blocked", "Blocked"],
            ["done", "Done"],
        ],
    });

    _records = [
        {
            id: 1,
            foo: "yop",
            selection: "blocked",
        },
        {
            id: 2,
            foo: "blip",
            selection: "normal",
        },
        {
            id: 4,
            foo: "abc",
            selection: "done",
        },
        { id: 3, foo: "gnap" },
        { id: 5, foo: "blop" },
    ];
}
defineModels([Partner]);

test("PriorityField when not set", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 2,
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="selection" widget="priority" />
                    </group>
                </sheet>
            </form>`,
    });

    expect(".o_field_widget .o_priority:not(.o_field_empty)").toHaveCount(1, {
        message: "widget should be considered set, even though there is no value for this field",
    });
    expect(".o_field_widget .o_priority a.o_priority_star").toHaveCount(2, {
        message:
            "should have two stars for representing each possible value: no star, one star and two stars",
    });
    expect(".o_field_widget .o_priority a.o_priority_star.fa-star").toHaveCount(0, {
        message: "should have no full star since there is no value",
    });

    expect(".o_field_widget .o_priority a.o_priority_star.fa-star-o").toHaveCount(2, {
        message: "should have two empty stars since there is no value",
    });
});

test("PriorityField tooltip", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="selection" widget="priority"/>
                    </group>
                </sheet>
            </form>`,
        resId: 1,
    });

    // check data-tooltip attribute (used by the tooltip service)
    const stars = queryAll(".o_field_widget .o_priority a.o_priority_star");
    expect(stars[0]).toHaveAttribute("data-tooltip", "Selection: Blocked");
    expect(stars[1]).toHaveAttribute("data-tooltip", "Selection: Done");
});

test("PriorityField in form view", async () => {
    expect.assertions(8);

    onRpc("web_save", ({ args }) => {
        expect(args).toEqual([[1], { selection: "done" }]);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="selection" widget="priority" />
                    </group>
                </sheet>
            </form>`,
    });

    expect(".o_field_widget .o_priority:not(.o_field_empty)").toHaveCount(1);
    expect(".o_field_widget .o_priority a.o_priority_star").toHaveCount(2);
    expect(".o_field_widget .o_priority a.o_priority_star.fa-star").toHaveCount(1);
    expect(".o_field_widget .o_priority a.o_priority_star.fa-star-o").toHaveCount(1);

    // click on the second star in edit mode
    await click(".o_field_widget .o_priority a.o_priority_star.fa-star-o:last");
    await animationFrame();

    expect(".o_field_widget .o_priority a.o_priority_star").toHaveCount(2);
    expect(".o_field_widget .o_priority a.o_priority_star.fa-star").toHaveCount(2);
    expect(".o_field_widget .o_priority a.o_priority_star.fa-star-o").toHaveCount(0);
});

test.tags("desktop")("PriorityField hover a star in form view", async () => {
    expect.assertions(10);
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="selection" widget="priority" />
                    </group>
                </sheet>
            </form>`,
    });

    expect(".o_field_widget .o_priority:not(.o_field_empty)").toHaveCount(1);
    expect(".o_field_widget .o_priority a.o_priority_star").toHaveCount(2);
    expect(".o_field_widget .o_priority a.o_priority_star.fa-star").toHaveCount(1);
    expect(".o_field_widget .o_priority a.o_priority_star.fa-star-o").toHaveCount(1);

    // hover last star
    const star = ".o_field_widget .o_priority a.o_priority_star.fa-star-o:last";
    await hover(star);
    await animationFrame();
    expect(".o_field_widget .o_priority a.o_priority_star").toHaveCount(2);
    expect(".o_field_widget .o_priority a.o_priority_star.fa-star").toHaveCount(2, {
        message: "should temporary have two full stars since we are hovering the third value",
    });
    expect(".o_field_widget .o_priority a.o_priority_star.fa-star-o").toHaveCount(0, {
        message: "should temporary have no empty star since we are hovering the third value",
    });

    await leave(star);
    await animationFrame();

    expect(".o_field_widget .o_priority a.o_priority_star").toHaveCount(2);
    expect(".o_field_widget .o_priority a.o_priority_star.fa-star").toHaveCount(1);
    expect(".o_field_widget .o_priority a.o_priority_star.fa-star-o").toHaveCount(1);
});

test("PriorityField can write after adding a record -- kanban", async () => {
    Partner._fields.selection = fields.Selection({
        string: "Selection",
        selection: [
            ["0", 0],
            ["1", 1],
        ],
    });
    Partner._records[0].selection = "0";
    Partner._views[["form", "myquickview"]] = /* xml */ `<form/>`;
    onRpc("web_save", ({ args }) => expect.step(`web_save ${JSON.stringify(args)}`));
    await mountView({
        type: "kanban",
        resModel: "partner",
        domain: [["id", "=", 1]],
        groupBy: ["foo"],
        arch: /* xml */ `
            <kanban on_create="quick_create" quick_create_view="myquickview">
                <templates>
                    <t t-name="card">
                        <field name="selection" widget="priority"/>
                    </t>
                </templates>
            </kanban>`,
    });
    expect(".o_kanban_record .fa-star").toHaveCount(0);

    await click(".o_priority a.o_priority_star.fa-star-o");
    // wait for web_save
    await animationFrame();
    expect.verifySteps(['web_save [[1],{"selection":"1"}]']);
    expect(".o_kanban_record .fa-star").toHaveCount(1);
    await click(".o_control_panel_main_buttons .o-kanban-button-new");
    await animationFrame();
    await animationFrame();
    await click(".o_kanban_quick_create .o_kanban_add");
    await animationFrame();
    expect.verifySteps(["web_save [[],{}]"]);
    await click(".o_priority a.o_priority_star.fa-star-o");
    await animationFrame();
    expect.verifySteps([`web_save [[6],{"selection":"1"}]`]);
    expect(".o_kanban_record .fa-star").toHaveCount(2);
});

test("PriorityField in editable list view", async () => {
    onRpc("has_group", () => true);
    await mountView({
        type: "list",
        resModel: "partner",
        arch: /* xml */ `<list editable="bottom"><field name="selection" widget="priority" /></list>`,
    });

    expect(".o_data_row:first-child .o_priority:not(.o_field_empty)").toHaveCount(1);
    expect(".o_data_row:first-child .o_priority a.o_priority_star").toHaveCount(2, {
        message:
            "should have two stars for representing each possible value: no star, one star and two stars",
    });
    expect(".o_data_row:first-child .o_priority a.o_priority_star.fa-star").toHaveCount(1, {
        message: "should have one full star since the value is the second value",
    });
    expect(".o_data_row:first-child .o_priority a.o_priority_star.fa-star-o").toHaveCount(1, {
        message: "should have one empty star since the value is the second value",
    });

    // switch to edit mode and check the result
    await click("tbody td:not(.o_list_record_selector)");
    await animationFrame();

    expect(".o_data_row:first-child .o_priority a.o_priority_star").toHaveCount(2, {
        message:
            "should have two stars for representing each possible value: no star, one star and two stars",
    });
    expect(".o_data_row:first-child .o_priority a.o_priority_star.fa-star").toHaveCount(1, {
        message: "should have one full star since the value is the second value",
    });
    expect(".o_data_row:first-child .o_priority a.o_priority_star.fa-star-o").toHaveCount(1, {
        message: "should have one empty star since the value is the second value",
    });

    // save
    await click(".o_control_panel_main_buttons .o_list_button_save");
    await animationFrame();

    expect(".o_data_row:first-child .o_priority a.o_priority_star").toHaveCount(2, {
        message:
            "should have two stars for representing each possible value: no star, one star and two stars",
    });
    expect(".o_data_row:first-child .o_priority a.o_priority_star.fa-star").toHaveCount(1, {
        message: "should have one full star since the value is the second value",
    });
    expect(".o_data_row:first-child .o_priority a.o_priority_star.fa-star-o").toHaveCount(1, {
        message: "should have one empty star since the value is the second value",
    });

    // click on the first star in readonly mode
    await click(".o_priority a.o_priority_star.fa-star");
    await animationFrame();

    expect(".o_data_row:first-child .o_priority a.o_priority_star").toHaveCount(2, {
        message: "should still have two stars",
    });
    expect(".o_data_row:first-child .o_priority a.o_priority_star.fa-star").toHaveCount(0, {
        message: "should now have no full star since the value is the first value",
    });
    expect(".o_data_row:first-child .o_priority a.o_priority_star.fa-star-o").toHaveCount(2, {
        message: "should now have two empty stars since the value is the first value",
    });

    // re-enter edit mode to force re-rendering the widget to check if the value was correctly saved
    await click("tbody td:not(.o_list_record_selector)");
    await animationFrame();

    expect(".o_data_row:first-child .o_priority a.o_priority_star").toHaveCount(2, {
        message: "should still have two stars",
    });
    expect(".o_data_row:first-child .o_priority a.o_priority_star.fa-star").toHaveCount(0, {
        message: "should now have no full star since the value is the first value",
    });
    expect(".o_data_row:first-child .o_priority a.o_priority_star.fa-star-o").toHaveCount(2, {
        message: "should now have two empty stars since the value is the first value",
    });

    // Click on second star in edit mode
    await click(".o_priority a.o_priority_star.fa-star-o:last");
    await animationFrame();

    expect(".o_data_row:last-child .o_priority a.o_priority_star").toHaveCount(2, {
        message: "should still have two stars",
    });
    expect(".o_data_row:last-child .o_priority a.o_priority_star.fa-star").toHaveCount(2, {
        message: "should now have two full stars since the value is the third value",
    });
    expect(".o_data_row:last-child .o_priority a.o_priority_star.fa-star-o").toHaveCount(0, {
        message: "should now have no empty star since the value is the third value",
    });

    // save
    await click(".o_control_panel_main_buttons .o_list_button_save");
    await animationFrame();

    expect(".o_data_row:last-child .o_priority a.o_priority_star").toHaveCount(2, {
        message: "should still have two stars",
    });
    expect(".o_data_row:last-child .o_priority a.o_priority_star.fa-star").toHaveCount(2, {
        message: "should now have two full stars since the value is the third value",
    });
    expect(".o_data_row:last-child .o_priority a.o_priority_star.fa-star-o").toHaveCount(0, {
        message: "should now have no empty star since the value is the third value",
    });
});

test.tags("desktop")("PriorityField hover in editable list view", async () => {
    onRpc("has_group", () => true);
    await mountView({
        type: "list",
        resModel: "partner",
        arch: /* xml */ `<list editable="bottom"><field name="selection" widget="priority" /></list>`,
    });

    expect(".o_data_row:first-child .o_priority:not(.o_field_empty)").toHaveCount(1);
    expect(".o_data_row:first-child .o_priority a.o_priority_star").toHaveCount(2, {
        message:
            "should have two stars for representing each possible value: no star, one star and two stars",
    });
    expect(".o_data_row:first-child .o_priority a.o_priority_star.fa-star").toHaveCount(1, {
        message: "should have one full star since the value is the second value",
    });
    expect(".o_data_row:first-child .o_priority a.o_priority_star.fa-star-o").toHaveCount(1, {
        message: "should have one empty star since the value is the second value",
    });

    // hover last star
    const star = ".o_data_row:first-child .o_priority a.o_priority_star.fa-star-o:last";
    await hover(star);
    await animationFrame();

    expect(".o_data_row:first-child .o_priority a.o_priority_star").toHaveCount(2);
    expect(".o_data_row:first-child .o_priority a.o_priority_star.fa-star").toHaveCount(2, {
        message: "should temporary have two full stars since we are hovering the third value",
    });
    expect(".o_data_row:first-child .o_priority a.o_priority_star.fa-star-o").toHaveCount(0, {
        message: "should temporary have no empty star since we are hovering the third value",
    });

    await leave(star);
    await animationFrame();

    expect(".o_data_row:first-child .o_priority a.o_priority_star").toHaveCount(2);
    expect(".o_data_row:first-child .o_priority a.o_priority_star.fa-star").toHaveCount(1);
    expect(".o_data_row:first-child .o_priority a.o_priority_star.fa-star-o").toHaveCount(1);
});

test("PriorityField with readonly attribute", async () => {
    onRpc("write", () => {
        expect.step("write");
        throw new Error("should not save");
    });

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 2,
        arch: '<form><field name="selection" widget="priority" readonly="1"/></form>',
    });

    expect("span.o_priority_star.fa.fa-star-o").toHaveCount(2, {
        message: "stars of priority widget should rendered with span tag if readonly",
    });
    await hover(".o_priority_star.fa-star-o:last");
    await animationFrame();
    expect.step("hover");
    expect(".o_field_widget .o_priority a.o_priority_star.fa-star").toHaveCount(0, {
        message: "should have no full stars on hover since the field is readonly",
    });
    await click(".o_priority_star.fa-star-o:last");
    await animationFrame();
    expect.step("click");
    expect("span.o_priority_star.fa.fa-star-o").toHaveCount(2, {
        message: "should still have two stars",
    });
    expect.verifySteps(["hover", "click"]);
});

test('PriorityField edited by the smart action "Set priority..."', async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `<form><field name="selection" widget="priority"/></form>`,
        resId: 1,
    });

    expect("a.fa-star").toHaveCount(1);

    await press(["control", "k"]);
    await animationFrame();
    const idx = queryAllTexts(".o_command").indexOf("Set priority...\nALT + R");
    expect(idx).toBeGreaterThan(-1);
    await click(queryAll(".o_command")[idx]);
    await animationFrame();
    expect(queryAllTexts(".o_command")).toEqual(["Normal", "Blocked", "Done"]);
    await click("#o_command_2");
    await animationFrame();
    expect("a.fa-star").toHaveCount(2);
});

test("PriorityField - auto save record when field toggled", async () => {
    onRpc("web_save", () => expect.step("web_save"));
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="selection" widget="priority" />
                    </group>
                </sheet>
            </form>`,
    });
    await click(".o_field_widget .o_priority a.o_priority_star.fa-star-o:last");
    await animationFrame();
    expect.verifySteps(["web_save"]);
});

test("PriorityField - prevent auto save with autosave option", async () => {
    onRpc("write", () => expect.step("write"));
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="selection" widget="priority" options="{'autosave': False}"/>
                    </group>
                </sheet>
            </form>`,
    });

    await click(".o_field_widget .o_priority a.o_priority_star.fa-star-o:last");
    await animationFrame();
    expect.verifySteps([]);
});

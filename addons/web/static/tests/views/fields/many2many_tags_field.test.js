import { describe, expect, getFixture, test } from "@odoo/hoot";
import { hover, press, queryAllTexts, queryOne } from "@odoo/hoot-dom";
import { Deferred, animationFrame, runAllTimers } from "@odoo/hoot-mock";

import {
    clickFieldDropdown,
    clickFieldDropdownItem,
    clickSave,
    contains,
    defineModels,
    fieldInput,
    fields,
    makeServerError,
    mockService,
    models,
    mountView,
    onRpc,
    selectFieldDropdownItem,
} from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

class Partner extends models.Model {
    _name = "partner";

    name = fields.Char();
    foo = fields.Char({ default: "My little Foo Value" });
    turtles = fields.One2many({ relation: "turtle" });
    timmy = fields.Many2many({ relation: "partner.type", string: "pokemon" });

    _records = [
        {
            id: 1,
            name: "first record",
            foo: "yop",
            turtles: [2],
            timmy: [],
        },
        {
            id: 2,
            name: "second record",
            foo: "blip",
            timmy: [],
        },
        {
            id: 4,
            name: "aaa",
        },
    ];
}

class PartnerType extends models.Model {
    color = fields.Integer({ string: "Color index" });
    name = fields.Char();

    _records = [
        { id: 12, name: "gold", color: 2 },
        { id: 14, name: "silver", color: 5 },
    ];
}

class Turtle extends models.Model {
    _name = "turtle";

    name = fields.Char();
    turtle_bar = fields.Boolean({ default: true });
    partner_ids = fields.Many2many({ relation: "partner" });

    _records = [
        {
            id: 1,
            name: "leonardo",
            turtle_bar: true,
            partner_ids: [],
        },
        {
            id: 2,
            name: "donatello",
            turtle_bar: true,
            partner_ids: [2, 4],
        },
        {
            id: 3,
            name: "raphael",
            turtle_bar: false,
            partner_ids: [],
        },
    ];
}

defineModels([Partner, PartnerType, Turtle]);

onRpc("has_group", () => {
    return true;
});

test("Many2ManyTagsField with and without color", async () => {
    expect.assertions(14);

    Partner._fields.partner_ids = fields.Many2many({
        string: "Partner",
        relation: "partner",
    });
    Partner._fields.color = fields.Integer({ string: "Color index" });
    onRpc("web_read", ({ args, model, kwargs }) => {
        if (model === "partner.type") {
            expect(args).toEqual([[12]]);
            expect(kwargs.specification).toEqual({ display_name: {} });
        } else if (model === "partner") {
            expect(args).toEqual([[1]]);
            expect(kwargs.specification).toEqual({ display_name: {}, color: {} });
        }
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="partner_ids" widget="many2many_tags" options="{'color_field': 'color'}"/>
                <field name="timmy" widget="many2many_tags"/>
            </form>`,
    });
    await contains(".o_field_many2many_selection input").click();
    await runAllTimers();
    // Add a tag to first field
    expect("[name=partner_ids] .o_tag").toHaveCount(0);
    await contains(".o-autocomplete--dropdown-item:eq(0)").click();
    expect("[name=partner_ids] .o_tag").toHaveCount(1);

    // Show the color list
    expect(".o_colorlist").toHaveCount(0);
    await contains("[name=partner_ids] .o_tag").click();
    expect(".o_colorlist").toHaveCount(1);
    await contains(getFixture()).click();

    // Add a tag to second field
    expect("[name=timmy] .o_tag").toHaveCount(0);
    await clickFieldDropdown("timmy");
    expect("[name='timmy'] .o-autocomplete.dropdown li").toHaveCount(4, {
        message:
            "autocomplete dropdown should have 4 entries (2 values + 'Search More...' + 'Search and Edit...')",
    });
    await clickFieldDropdownItem("timmy", "gold");
    expect("[name=timmy] .o_tag").toHaveCount(1);
    expect(queryAllTexts(`.o_field_many2many_tags[name="timmy"] .badge`)).toEqual(["gold"]);

    // Show the color list
    expect(".o_colorlist").toHaveCount(0);
    await contains("[name=timmy] .o_tag").click();
    expect(".o_colorlist").toHaveCount(0);
});

test("Many2ManyTagsField with color: rendering and edition", async () => {
    expect.assertions(26);

    Partner._records[0].timmy = [12, 14];
    PartnerType._records.push({ id: 13, name: "red", color: 8 });
    onRpc(({ args, method, model, kwargs, route }) => {
        if (route === "/web/dataset/call_kw/partner/web_save") {
            var commands = args[1].timmy;
            expect(commands.length).toBe(2);
            expect(commands.map((cmd) => cmd[0]).join("-")).toBe("4-3");
            expect(commands.map((cmd) => cmd[1])).toEqual([13, 14], {
                message: "Should add 13, remove 14",
            });
        }
        if ((method === "web_read" || method === "web_save") && model === "partner.type") {
            expect(kwargs.specification).toEqual(
                { display_name: {}, color: {} },
                { message: "should read color field" }
            );
        }
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="timmy" widget="many2many_tags" options="{'color_field': 'color', 'no_create_edit': True }"/>
            </form>`,
        resId: 1,
    });
    expect(".o_field_many2many_tags .badge").toHaveCount(2);
    expect(".badge .o_tag_badge_text:eq(0)").toHaveText("gold");
    expect(".badge .o_tag_badge_text:eq(1)").toHaveText("silver");
    expect(".badge:eq(0)").toHaveClass("o_tag_color_2");
    expect(".o_field_many2many_tags .o_delete").toHaveCount(2);

    // add an other existing tag
    await contains("div[name='timmy'] .o-autocomplete.dropdown input").click();
    expect(`.dropdown-item-selected`).toHaveCount(2);
    expect(queryAllTexts`.dropdown-item-selected`).toEqual(["gold", "silver"]);
    expect(".o-autocomplete--dropdown-menu li").toHaveCount(5);
    expect(".o-autocomplete--dropdown-menu li a:eq(2)").toHaveText("red");

    await contains(".o-autocomplete--dropdown-menu li a:eq(2)").click();
    expect(".o_field_many2many_tags .badge").toHaveCount(3);
    expect(".o_field_many2many_tags .badge .o_tag_badge_text:eq(2)").toHaveText("red");
    expect(".badge:eq(2)").toHaveClass("o_tag_color_8");

    // remove tag silver
    await contains(".o_field_many2many_tags .o_delete:eq(1)").click();
    expect(".o_field_many2many_tags .badge").toHaveCount(2);
    const textContent = queryAllTexts(".o_field_many2many_tags  .dropdown-toggle .badge");
    expect(textContent).not.toInclude("silver");
    // save the record (should do the write RPC with the correct commands)
    await clickSave();

    // checkbox 'Hide in Kanban'
    const badgeElement = queryOne(".o_field_many2many_tags .badge:eq(1)"); // selects 'red' tag
    await contains(badgeElement).click();
    expect(".o_tag_popover .form-check input").toHaveCount(1);

    expect(".o_tag_popover .form-check input").not.toBeChecked();

    await contains(".o_tag_popover input[type='checkbox']").click();
    expect(badgeElement).toHaveAttribute("data-color", "0");

    await contains(badgeElement).click();
    expect(".o_tag_popover .form-check input").toBeChecked();

    await contains(".o_tag_popover input[type='checkbox']").click();

    expect(badgeElement).toHaveAttribute("data-color", "8");

    await contains(badgeElement).click();
    expect(".o_tag_popover .form-check input").not.toBeChecked();
});

test("Many2ManyTagsField in list view", async () => {
    Partner._records[0].timmy = [12, 14];

    await mountView({
        type: "list",
        resModel: "partner",
        arch: `
            <list>
                <field name="timmy" widget="many2many_tags" options="{'color_field': 'color'}"/>
                <field name="foo"/>
            </list>`,
        selectRecord: () => {
            expect.step("selectRecord");
        },
    });

    expect(".o_field_many2many_tags .badge").toHaveCount(2);
    expect(".badge.dropdown-toggle").toHaveCount(0, {
        message: "the tags should not be dropdowns",
    });

    // click on the tag: should do nothing and open the form view
    await contains(".o_field_many2many_tags .badge :nth-child(1)").click();
    expect.verifySteps(["selectRecord"]);
    await animationFrame();

    expect(".o_colorlist").toHaveCount(0);

    await contains(".o_list_record_selector:eq(1)").click();
    await contains(".o_field_many2many_tags .badge :nth-child(1)").click();
    expect.verifySteps(["selectRecord"]);
    await animationFrame();

    expect(".o_colorlist").toHaveCount(0);
});

test("Many2ManyTagsField in list view -- multi edit", async () => {
    Partner._records[0].timmy = [12, 14];

    await mountView({
        type: "list",
        resModel: "partner",
        arch: `
            <list multi_edit="1">
                <field name="timmy" widget="many2many_tags" options="{'color_field': 'color'}"/>
                <field name="foo"/>
            </list>`,
        selectRecord: () => {
            expect.step("selectRecord");
        },
    });

    expect(".o_field_many2many_tags .badge").toHaveCount(2);
    expect(".badge.dropdown-toggle").toHaveCount(0, {
        message: "the tags should not be dropdowns",
    });

    // click on the tag: should do nothing and open the form view
    await contains(".o_field_many2many_tags .badge :nth-child(1)").click();
    expect.verifySteps(["selectRecord"]);
    await animationFrame();

    expect(".o_colorlist").toHaveCount(0);

    await contains(".o_list_record_selector:eq(1)").click();
    await contains(".o_field_many2many_tags .badge :nth-child(1)").click();
    expect.verifySteps([]);
    await animationFrame();

    expect(".o_selected_row").toHaveCount(1);
    expect(".o_colorlist").toHaveCount(0);
});

test("Many2ManyTagsField view a domain", async () => {
    expect.assertions(7);

    Partner._fields.timmy = fields.Many2many({
        relation: "partner.type",
        string: "pokemon",
        domain: [["id", "<", 50]],
    });
    Partner._records[0].timmy = [12];
    PartnerType._records.push({ id: 99, name: "red", color: 8 });
    onRpc("name_search", (args) => {
        expect(args.kwargs.args).toEqual([["id", "<", 50]]);
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="timmy" widget="many2many_tags" options="{'no_create_edit': True}"/>
            </form>`,
        resId: 1,
    });

    expect(".o_field_many2many_tags .badge").toHaveCount(1);
    expect(queryAllTexts(".badge")).toEqual(["gold"]);

    await clickFieldDropdown("timmy");

    expect(".o-autocomplete--dropdown-menu li").toHaveCount(4);

    expect(".o-autocomplete--dropdown-menu li a:eq(0)").toHaveText("gold");

    await clickFieldDropdownItem("timmy", "silver");

    expect(".o_field_many2many_tags .badge").toHaveCount(2);

    expect(queryAllTexts(".badge")).toEqual(["gold", "silver"]);
});

test("use binary field as the domain", async () => {
    Partner._fields.domain = fields.Binary();
    Partner._records[0].domain = '[["id", "<", 50]]';
    Partner._records[0].timmy = [12];
    PartnerType._records.push({ id: 99, name: "red", color: 8 });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="timmy" widget="many2many_tags" domain="domain"/>
                <field name="domain" invisible="1"/>
            </form>`,
        resId: 1,
    });

    expect(".o_field_many2many_tags .badge").toHaveCount(1);
    expect(queryAllTexts(".badge")).toEqual(["gold"]);

    await clickFieldDropdown("timmy");

    expect(".o-autocomplete--dropdown-menu li").toHaveCount(4);
    expect(queryAllTexts(".o-autocomplete--dropdown-menu li")).toEqual([
        "gold",
        "silver",
        "Search More...",
        "Start typing...",
    ]);
    expect(".o-autocomplete--dropdown-menu li a:eq(0)").toHaveText("gold");

    await clickFieldDropdownItem("timmy", "silver");

    expect(".o_field_many2many_tags .badge").toHaveCount(2);
    expect(queryAllTexts(".badge")).toEqual(["gold", "silver"]);
});

test("Domain: allow python code domain in fieldInfo", async () => {
    expect.assertions(4);
    Partner._fields.timmy = fields.Many2many({
        relation: "partner.type",
        string: "pokemon",
        domain: "foo and [('color', '>', 3)] or [('color', '<', 3)]",
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="foo"/>
                <field name="timmy" widget="many2many_tags"></field>
            </form>`,
        resId: 1,
    });

    // foo set => only silver (id=5) selectable
    await clickFieldDropdown("timmy");
    expect(".o-autocomplete--dropdown-menu li").toHaveCount(3);
    expect(".o-autocomplete--dropdown-menu li a:eq(0)").toHaveText("silver");
    await clickFieldDropdownItem("timmy", "Start typing...");
    // set foo = "" => only gold (id=2) selectable
    await contains("[name=foo] input").clear();
    await clickFieldDropdown("timmy");
    expect(".o-autocomplete--dropdown-menu li").toHaveCount(3);
    expect(".o-autocomplete--dropdown-menu li a:eq(0)").toHaveText("gold");
});

test("Many2ManyTagsField in a new record", async () => {
    expect.assertions(7);
    onRpc("web_save", ({ args }) => {
        const commands = args[1].timmy;
        expect(commands.length).toBe(1);
        expect(commands[0][0]).toBe(4, { message: "generated command should be LINK TO" });
        expect(commands[0][1]).toBe(12);
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: '<form><field name="timmy" widget="many2many_tags"/></form>',
    });
    expect(".o_form_view .o_form_editable").toHaveCount(1);

    await clickFieldDropdown("timmy");
    expect("[name='timmy'] .o-autocomplete.dropdown li").toHaveCount(4);
    await clickFieldDropdownItem("timmy", "gold");

    expect(".o_field_many2many_tags .badge").toHaveCount(1);
    expect(queryAllTexts(".o_field_many2many_tags .badge")).toEqual(["gold"]);

    // save the record (should do the write RPC with the correct commands)
    await clickSave();
});

test("Many2ManyTagsField: update color", async () => {
    Partner._records[0].timmy = [12];
    PartnerType._records[0].color = 0;
    onRpc("web_save", ({ args }) => {
        expect.step(JSON.stringify(args[1]));
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="timmy" widget="many2many_tags" options="{'color_field': 'color'}"/>
            </form>`,
        resId: 1,
    });

    // First checks that default color 0 is rendered as 0 color
    const badgeNode = queryOne(".o_tag.badge");
    expect(badgeNode).toHaveAttribute("data-color", "0");

    // Update the color in readonly => write automatically
    await contains(badgeNode).click();
    await contains('.o_colorlist button[data-color="1"]').click();
    expect(badgeNode).toHaveAttribute("data-color", "1");

    // Update the color in edit => write on save with rest of the record
    await contains(badgeNode).click();
    await contains('.o_colorlist button[data-color="6"]').click();
    await animationFrame();
    expect(badgeNode).toHaveAttribute("data-color", "6");

    // TODO POST WOWL GES: commented code below is to make the m2mtags more.
    // consistent. No color change if edit => discard.
    // await clickSave();

    expect.verifySteps([
        `{"color":1}`,
        `{"color":6}`,
        //  `{"timmy":[[1,12,{"color":6}]]}`
    ]);

    /*
    badgeNode = queryOne(".o_tag.badge"); // need to refresh the reference

    // Update the color in edit without save => we don't go through RPC
    // so it's not saved and it is lost on discard.
    await clickEdit();
    await contains(badgeNode).click();
    await contains('.o_colorlist button[data-color="8"]').click();
    await animationFrame();
    expect(badgeNode).toHaveAttribute("data-color",
        "8"
    );

    await clickDiscard();

    expect(badgeNode).toHaveAttribute("data-color",
        "6"
    );

    */
});

test("Many2ManyTagsField with no_edit_color option", async () => {
    Partner._records[0].timmy = [12];

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="timmy" widget="many2many_tags" options="{'color_field': 'color', 'no_edit_color': 1}"/>
            </form>`,
        resId: 1,
    });

    // Click to try to open colorpicker
    await contains(".o_tag.badge").click();
    expect(".o_colorlist").toHaveCount(0);
});

test("Many2ManyTagsField in editable list", async () => {
    expect.assertions(4);

    Partner._records[0].timmy = [12];

    onRpc("web_read", ({ kwargs, model }) => {
        if (model === "partner.type") {
            expect(kwargs.context.take).toBe("five");
        }
    });

    await mountView({
        type: "list",
        resModel: "partner",
        context: { take: "five" },
        arch: `
            <list editable="bottom">
                <field name="timmy" widget="many2many_tags"/>
            </list>`,
    });
    expect(".o_data_row:nth-child(1) .o_field_many2many_tags .badge").toHaveCount(1);

    // edit first row
    await contains(".o_data_row:nth-child(1) .o_many2many_tags_cell").click();

    expect(
        ".o_data_row:nth-child(1) .o_many2many_tags_cell .o_field_many2many_selection"
    ).toHaveCount(1);

    // add a tag
    await selectFieldDropdownItem("timmy", "silver");

    expect(".o_data_row:nth-child(1) .o_field_many2many_tags .badge").toHaveCount(2);
});

test("Many2ManyTagsField can load more than 40 records", async () => {
    Partner._fields.partner_ids = fields.Many2many({
        string: "Partner",
        relation: "partner",
    });
    Partner._records[0].partner_ids = [];
    for (var i = 15; i < 115; i++) {
        Partner._records.push({ id: i, name: "walter" + i });
        Partner._records[0].partner_ids.push(i);
    }
    await mountView({
        type: "form",
        resModel: "partner",
        arch: '<form><field name="partner_ids" widget="many2many_tags"/></form>',
        resId: 1,
    });
    expect('.o_field_widget[name="partner_ids"] .badge').toHaveCount(100);
});

test("Many2ManyTagsField keeps focus when being edited", async () => {
    Partner._records[0].timmy = [12];
    Partner._fields.foo = fields.Char({
        default: "My little Foo Value",
        onChange: (obj) => {
            obj.timmy = [[3, 12]];
        },
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="foo"/>
                <field name="timmy" widget="many2many_tags"/>
            </form>`,
        resId: 1,
    });

    expect(".o_field_many2many_tags .badge").toHaveCount(1);

    // update foo, which will trigger an onchange and update timmy
    // -> m2mtags input should not have taken the focus
    await contains("[name=foo] input").edit("trigger onchange");
    expect(".o_field_many2many_tags .badge").toHaveCount(0);
    expect("[name=foo] input").toBeFocused();

    await selectFieldDropdownItem("timmy", "gold");
    expect(".o_field_many2many_tags .badge").toHaveCount(1);
    expect(".o_field_many2many_tags input").toBeFocused();
});

test("Many2ManyTagsField: tags title attribute", async () => {
    Turtle._records[0].partner_ids = [2];

    await mountView({
        type: "form",
        resModel: "turtle",
        resId: 1,
        arch: `
            <form>
                <sheet>
                    <field name="name"/>
                    <field name="partner_ids" widget="many2many_tags"/>
                </sheet>
            </form>`,
    });

    expect(".o_field_many2many_tags .o_tag.badge").toHaveAttribute("title", "second record");
});

test("Many2ManyTagsField: toggle colorpicker with multiple tags", async () => {
    Partner._records[0].timmy = [12, 14];
    PartnerType._records[0].color = 0;

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
                <form>
                    <field name="timmy" widget="many2many_tags" options="{'color_field': 'color'}"/>
                </form>`,
        resId: 1,
    });

    expect(".o_colorpicker").toHaveCount(0);

    // click on the badge to open colorpicker
    await contains(".o_field_many2many_tags .badge").click();
    expect(".o_colorlist").toHaveCount(1);

    await contains(".o_field_many2many_tags [title=silver]").click();
    expect(".o_colorlist").toHaveCount(1);

    await contains(".o_field_many2many_tags [title=silver]").click();
    expect(".o_colorpicker").toHaveCount(0);

    await contains(".o_field_many2many_tags [title=silver]").click();
    expect(".o_colorlist").toHaveCount(1);

    await contains(getFixture()).click();
    expect(".o_colorpicker").toHaveCount(0);
});

test("Many2ManyTagsField: toggle colorpicker multiple times", async () => {
    Partner._records[0].timmy = [12];
    PartnerType._records[0].color = 0;

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="timmy" widget="many2many_tags" options="{'color_field': 'color'}"/>
            </form>`,
        resId: 1,
    });

    expect(".o_field_many2many_tags .badge").toHaveCount(1);
    expect(".o_field_many2many_tags .badge").toHaveAttribute("data-color", "0");
    expect(".o_colorpicker").toHaveCount(0);

    // click on the badge to open colorpicker
    await contains(".o_field_many2many_tags .badge").click();

    expect(".o_colorlist").toHaveCount(1);

    // click on the badge again to close colorpicker
    await contains(".o_field_many2many_tags .badge").click();

    expect(".o_field_many2many_tags .badge").toHaveAttribute("data-color", "0");
    expect(".o_colorlist").toHaveCount(0);

    // click on the badge to open colorpicker
    await contains(".o_field_many2many_tags .badge").click();

    expect(".o_colorlist").toHaveCount(1);

    // click on the colorpicker, but not on a color
    await contains(".o_colorlist").click();

    expect(".o_field_many2many_tags .badge").toHaveAttribute("data-color", "0");
    expect(".o_colorlist").toHaveCount(1);

    await contains('.o_colorlist button[data-color="2"]').click();

    expect(".o_field_many2many_tags .badge").toHaveAttribute("data-color", "2");
    expect(".o_colorlist").toHaveCount(0);
});

test("Many2ManyTagsField: quick create a new record", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: '<form><field name="timmy" widget="many2many_tags"/></form>',
    });

    expect(".o_field_many2many_tags .badge").toHaveCount(0);

    await contains(".o_field_many2many_selection .o_input_dropdown input").edit("new", {
        confirm: false,
    });
    await runAllTimers();
    await clickFieldDropdownItem("timmy", `Create "new"`);
    expect(".o_field_many2many_tags .badge").toHaveCount(1);

    await clickSave();
    expect(".o_field_many2many_tags").toHaveText("new");
});

test("select a many2many value by pressing tab", async () => {
    PartnerType._records.push({ id: 13, name: "red", color: 8 });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: '<form><field name="timmy" widget="many2many_tags"/></form>',
    });

    expect(".o_field_many2many_tags .badge").toHaveCount(0);
    await contains(".o_field_many2many_tags input").edit("go", { confirm: false });
    await runAllTimers();
    await press("Tab");
    await animationFrame();
    expect(".o_field_many2many_tags .badge").toHaveCount(1);
    expect(".o_field_many2many_tags .badge").toHaveText("gold");

    await contains(".o_field_many2many_tags input").edit("r", { confirm: false });
    await runAllTimers();
    await press("ArrowDown");
    await press("Tab");
    await animationFrame();
    expect(".o_field_many2many_tags .badge").toHaveCount(2);
    expect(".o_field_many2many_tags .badge:eq(1)").toHaveText("red");
});

test("input and remove text without selecting any tag or option", async () => {
    PartnerType._records.push({ id: 13, name: "red", color: 8 });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: '<form><field name="timmy" widget="many2many_tags"/></form>',
    });

    expect(".o_field_many2many_tags .badge").toHaveCount(0);

    // enter some text
    await contains(".o_field_many2many_tags input").edit("go", { confirm: false });
    await runAllTimers();

    // ensure no selection
    await hover(".o-autocomplete--dropdown-item:eq(0)");
    await hover(".o_form_renderer");
    await press("Tab");

    // ensure we're not adding any value
    expect(".modal").toHaveCount(0);
    expect(".o_field_many2many_tags .badge").toHaveCount(0);

    // remove the added text to test behaviour with falsy value
    await contains(".o_field_many2many_tags input").clear({ confirm: false });
    await runAllTimers();

    await hover(".o-autocomplete--dropdown-item:eq(0)");
    await hover(".o_form_renderer");
    await press("Tab");

    expect(".modal").toHaveCount(0);
    expect(".o_field_many2many_tags .badge").toHaveCount(0);
});

test("Many2ManyTagsField in one2many with name", async () => {
    Turtle._records[0].partner_ids = [2];
    Partner._views = {
        list: '<list><field name="foo"/></list>',
    };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="turtles">
                    <list>
                        <field name="partner_ids" widget="many2many_tags"/>
                    </list>
                    <form>
                        <field name="partner_ids"/>
                    </form>
                </field>
            </form>`,
        resId: 1,
    });

    expect(queryAllTexts(".o_data_cell")).toEqual(["second record\naaa"]);

    // open the x2m form view
    await contains('.o_field_one2many[name="turtles"] .o_data_cell').click();
    expect(queryAllTexts(".modal .o_data_cell")).toEqual(["blip", "My little Foo Value"]);

    await contains(".modal button.o_form_button_cancel").click();
    expect(queryAllTexts(".o_data_cell")).toEqual(["second record\naaa"]);
});

test("many2many read, field context is properly sent", async () => {
    Partner._fields.timmy = fields.Many2many({
        relation: "partner.type",
        string: "pokemon",
        context: { hello: "world" },
    });
    Partner._records[0].timmy = [12];
    onRpc("web_read", (args) => {
        if (args.model === "partner") {
            expect.step(`${args.method} ${args.model}`);
            expect(args.kwargs.specification.timmy.context.hello).toBe("world");
        }
        if (args.model === "partner.type") {
            expect.step(`${args.method} ${args.model}`);
            expect(args.kwargs.context.hello).toBe("world");
        }
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: '<form><field name="timmy" widget="many2many_tags"/></form>',
        resId: 1,
    });

    expect.verifySteps(["web_read partner"]);
    await selectFieldDropdownItem("timmy", "silver");
    expect.verifySteps(["web_read partner.type"]);
});

test("Many2ManyTagsField: select multiple records", async () => {
    PartnerType._views = {
        list: '<list><field name="name"/></list>',
        search: '<search><field name="name"/></search>',
    };

    for (var i = 1; i <= 10; i++) {
        PartnerType._records.push({
            id: 100 + i,
            name: "Partner" + i,
        });
    }

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="timmy" widget="many2many_tags"/>
            </form>`,
    });

    await selectFieldDropdownItem("timmy", "Search More...");

    expect(".o_dialog").toHaveCount(1);
    // + 1 for the select all
    expect(".o_dialog .o_list_renderer .o_list_record_selector input").toHaveCount(
        PartnerType._records.length + 1
    );
    //multiple select tag
    await contains(".o_dialog .o_list_renderer .o_list_record_selector input").click();
    await animationFrame(); // necessary for the button to be switched to enabled.
    expect(".o_dialog .o_select_button").toBeEnabled();

    await contains(".o_dialog .o_select_button").click();
    expect("o_dialog").toHaveCount(0);
    expect('[name="timmy"] .badge').toHaveCount(PartnerType._records.length);
});

test("Many2ManyTagsField: select multiple records doesn't show already added tags", async () => {
    Partner._records[0].timmy = [12];

    PartnerType._views = {
        list: '<list><field name="name"/></list>',
        search: '<search><field name="name"/></search>',
    };

    for (var i = 1; i <= 10; i++) {
        PartnerType._records.push({
            id: 100 + i,
            name: "Partner" + i,
        });
    }

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
                <form>
                    <field name="timmy" widget="many2many_tags"/>
                </form>`,
    });

    await selectFieldDropdownItem("timmy", "Search More...");

    expect(".o_dialog .o_list_renderer .o_list_record_selector input").toHaveCount(
        PartnerType._records.length + 1
    );

    //multiple select tag
    await contains(".o_dialog .o_list_renderer .o_list_record_selector input").click();
    await animationFrame(); // necessary for the button to be switched to enabled.
    await contains(".o_dialog .o_select_button").click();
    expect('[name="timmy"] .badge').toHaveCount(PartnerType._records.length);
});

test("Many2ManyTagsField: save&new in edit mode doesn't close edit window", async () => {
    for (var i = 1; i <= 10; i++) {
        PartnerType._records.push({
            id: 100 + i,
            name: "Partner" + i,
        });
    }

    PartnerType._views = {
        list: '<list><field name="name"/></list>',
        search: '<search><field name="name"/></search>',
        form: '<form><field name="name"/></form>',
    };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
                <form>
                    <field name="name"/>
                    <field name="timmy" widget="many2many_tags"/>
                </form>`,
        resId: 1,
    });

    await contains(`div[name="timmy"] input`).edit("Ralts", { confirm: false });
    await runAllTimers();
    await clickFieldDropdownItem("timmy", "Create and edit...");
    //await testUtils.fields.many2one.createAndEdit("timmy", "Ralts");
    expect(".modal .o_form_view").toHaveCount(1);

    // Create multiple records with save & new
    await contains(".modal input").edit("Ralts");
    await contains(".modal .btn-primary:nth-child(2)").click();
    expect(".modal .o_form_view").toHaveCount(1);
    expect(".modal input:first").toHaveValue("");

    // Create another record and click save & close
    await contains(".modal input").edit("Pikachu");

    await contains(".modal .o_form_buttons_edit .btn-primary:first").click();
    expect(".modal .o_list_view").toHaveCount(0);
    expect('.o_field_many2many_tags[name="timmy"] .badge').toHaveCount(2);
});

test("Many2ManyTagsField: make tag name input field blank on Save&New", async () => {
    PartnerType._views = {
        form: '<form><field name="name"/></form>',
    };

    onRpc("onchange", (args) => expect.step(args.kwargs.context));
    await mountView({
        type: "form",
        resModel: "partner",
        arch: '<form><field name="timmy" widget="many2many_tags"/></form>',
        resId: 1,
    });

    await contains(".o_field_widget input").edit("hello", { confirm: false });
    await runAllTimers();
    await clickFieldDropdownItem("timmy", "Create and edit...");

    expect(".modal .o_form_view input").toHaveValue("hello");

    // Create record with save & new
    await contains(".modal .btn-primary:nth-child(2)").click();
    expect(".modal .o_form_view input").toHaveValue("");

    expect.verifySteps([
        { allowed_company_ids: [1], default_name: "hello", lang: "en", tz: "taht", uid: 7 },
        {
            allowed_company_ids: [1],
            lang: "en",
            tz: "taht",
            uid: 7,
        },
    ]);
});

test("Many2ManyTagsField: Save&New in many2many_tags with default_ keys in context", async () => {
    PartnerType._views = {
        form: `
            <form>
                <field name="name"/>
                <field name="color"/>
            </form>`,
    };

    onRpc("onchange", (args) => expect.step(args.kwargs.context));
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="timmy" widget="many2many_tags" context="{'default_color': 3}"/>
            </form>`,
        resId: 1,
    });

    await contains(".o_field_widget input").edit("hello", { confirm: false });
    await runAllTimers();
    await clickFieldDropdownItem("timmy", "Create and edit...");

    expect(".modal .o_field_widget[name=name] input").toHaveValue("hello");
    expect(".modal .o_field_widget[name=color] input").toHaveValue("3");

    // Create record with save & new
    await contains(".modal .btn-primary:nth-child(2)").click();
    expect(".modal .o_field_widget[name=name] input").toHaveValue("");
    expect(".modal .o_field_widget[name=color] input").toHaveValue("3");

    expect.verifySteps([
        {
            allowed_company_ids: [1],
            default_name: "hello",
            default_color: 3,
            lang: "en",
            tz: "taht",
            uid: 7,
        },
        {
            allowed_company_ids: [1],
            default_color: 3,
            lang: "en",
            tz: "taht",
            uid: 7,
        },
    ]);
});

test("Many2ManyTagsField: conditional create/delete actions", async () => {
    Turtle._records[0].partner_ids = [2];
    for (var i = 1; i <= 10; i++) {
        Partner._records.push({
            id: 100 + i,
            name: "Partner" + i,
        });
    }

    Partner._views = {
        list: '<list><field name="name"/></list>',
        search: "<search/>",
    };

    await mountView({
        type: "form",
        resModel: "turtle",
        arch: `
            <form>
                <field name="name"/>
                <field name="turtle_bar"/>
                <field name="partner_ids" options="{'create': [('turtle_bar', '=', True)], 'delete': [('turtle_bar', '=', True)]}" widget="many2many_tags"/>
            </form>`,
        resId: 1,
    });

    // turtle_bar is true -> create and delete actions are available
    expect(".o_field_many2many_tags.o_field_widget .badge .o_delete").toHaveCount(1);

    await clickFieldDropdown("partner_ids");
    await animationFrame();
    expect(
        ".o-autocomplete.dropdown li.o_m2o_start_typing a:contains(Start typing...)"
    ).toHaveCount(1);

    await clickFieldDropdownItem("partner_ids", "Search More...");

    expect(".modal .modal-footer button").toHaveCount(3);

    await contains(".modal .modal-footer .o_form_button_cancel").click();

    // type something that doesn't exist
    await contains(".o_field_many2many_tags input").edit("Something that does not exist", {
        confirm: false,
    });
    await runAllTimers();

    expect(".o-autocomplete.dropdown li.o_m2o_dropdown_option").toHaveCount(2);

    // set turtle_bar false -> create and delete actions are no longer available
    await contains('.o_field_widget[name="turtle_bar"] input:eq(0)').click();
    await animationFrame();

    // remove icon should still be there as it doesn't delete records but rather remove links
    expect(".o_field_many2many_tags.o_field_widget .badge .o_delete").toHaveCount(1);

    await clickFieldDropdown("partner_ids");
    await runAllTimers();

    // only Search More option should be available
    expect(".o-autocomplete.dropdown li.o_m2o_dropdown_option").toHaveCount(1);
    expect(
        ".o-autocomplete.dropdown li.o_m2o_dropdown_option a:contains(Search More...)"
    ).toHaveCount(1);

    await clickFieldDropdownItem("partner_ids", "Search More...");

    expect(".modal .modal-footer button").toHaveCount(2);

    await contains(".modal .modal-footer .o_form_button_cancel").click();

    // type something that does exist in multiple occurrences
    await contains(".o_field_many2many_tags input").edit("Pa", { confirm: false });
    await runAllTimers();

    // only Search More option should be available
    expect(".o-autocomplete.dropdown li.o_m2o_dropdown_option").toHaveCount(1);
    expect(".o-autocomplete.dropdown li.o_m2o_dropdown_option a:contains(Search More)").toHaveCount(
        1
    );
});

test("failing many2one quick create in a Many2ManyTagsField", async () => {
    expect.assertions(5);

    PartnerType._views = {
        form: `
            <form>
                <field name="name"/>
                <field name="color"/>
            </form>`,
    };
    onRpc("name_create", () => {
        throw makeServerError({ type: "ValidationError" });
    });
    onRpc("web_save", (args) => {
        expect(args.args[1]).toEqual({
            color: 8,
            name: "new partner",
        });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: '<form><field name="timmy" widget="many2many_tags"/></form>',
    });

    expect(".o_field_many2many_tags .badge").toHaveCount(0);

    // try to quick create a record
    await contains(".o_field_many2many_tags input").edit("new partner", { confirm: false });
    await runAllTimers();
    await clickFieldDropdownItem("timmy", `Create "new partner"`);

    // as the quick create failed, a dialog should be open to 'slow create' the record
    expect(".modal .o_form_view").toHaveCount(1);
    expect(".modal .o_field_widget[name=name] input").toHaveValue("new partner");

    await contains(".modal .o_field_widget[name=color] input").edit(8);
    await contains(".modal footer .o_form_buttons_edit button").click();

    expect(".o_field_many2many_tags .badge").toHaveCount(1);
});

test("navigation in tags (mode 'readonly')", async () => {
    // keep a single line with 2 badges
    Partner._records = Partner._records.slice(0, 1);
    Partner._records[0].timmy = [12, 14];
    Turtle._records[1].partner_ids = [];

    await mountView({
        type: "list",
        resModel: "partner",
        arch: `
            <list editable="bottom">
                <field name="timmy" widget="many2many_tags"/>
            </list>`,
    });
    expect(".o_searchview_input").toBeFocused();

    await press("ArrowDown");
    await press("ArrowDown");

    expect("tr.o_data_row input[type=checkbox]").toBeFocused();

    await press("ArrowRight");

    expect("tr.o_data_row td[name=timmy]").toBeFocused();
});

test("navigation in tags (mode 'edit')", async () => {
    // keep a single line with 2 badges
    Partner._records = Partner._records.slice(0, 1);
    Partner._records[0].timmy = [12, 14];
    Turtle._records[1].partner_ids = [];

    await mountView({
        type: "list",
        resModel: "partner",
        arch: `
            <list editable="bottom">
                <field name="timmy" widget="many2many_tags"/>
                <field name="name"/>
            </list>`,
    });

    await contains("tr.o_data_row:eq(0) .o_many2many_tags_cell").click();

    expect("tr.o_data_row:eq(0) .o_field_many2many_tags .badge").toHaveCount(2);

    expect("tr.o_data_row:eq(0) [name=timmy] .o-autocomplete--input").toBeFocused();

    // press left to focus the rightmost facet
    await press("ArrowLeft");

    expect("tr.o_data_row:eq(0) [name=timmy] .badge:nth-child(2)").toBeFocused();

    // press left to focus the leftmost facet
    await press("ArrowLeft");

    expect("tr.o_data_row:eq(0) [name=timmy] .badge:nth-child(1)").toBeFocused();

    // press left to focus the input
    await press("ArrowLeft");

    expect("tr.o_data_row:eq(0) [name=timmy] .o-autocomplete--input").toBeFocused();
    // press left to focus the leftmost facet
    await press("ArrowRight");

    expect("tr.o_data_row:eq(0) [name=timmy] .badge:nth-child(1)").toBeFocused();
    expect("tr.o_data_row:eq(0) .o_field_many2many_tags .badge").toHaveCount(2);
    expect(queryAllTexts(".o_field_many2many_tags .badge")).toEqual(["gold", "silver"]);

    await press("BackSpace");
    await animationFrame();

    expect("tr.o_data_row:eq(0) .o_field_many2many_tags .badge").toHaveCount(1);
    expect(queryAllTexts(".o_field_many2many_tags .badge")).toEqual(["silver"]);
    expect("tr.o_data_row:eq(0) .o-autocomplete--input").toHaveCount(1);
});

test("Many2ManyTagsField with placeholder", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: '<form><field name="timmy" widget="many2many_tags" placeholder="Placeholder"/></form>',
    });

    expect(".o_field_widget[name='timmy'] input").toHaveAttribute("placeholder", "Placeholder");

    await selectFieldDropdownItem("timmy", "gold");

    expect(".o_field_widget[name='timmy'] input").toHaveAttribute("placeholder", "");
});

test("Many2ManyTagsField supports 'create' props to be a Boolean", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `<form><field name="timmy" widget="many2many_tags" placeholder="Placeholder" options="{'create': False }"/></form>`,
    });

    await contains(".o_field_many2many_tags input").click();
    expect(".o_field_many2many_tags .o-autocomplete--dropdown-menu").toHaveText(
        "gold\nsilver\nSearch More..."
    );
});

test("save a record with an empty many2many_tags required", async () => {
    expect.assertions(3);
    mockService("notification", {
        add: (message, params) => {
            expect(message.toString()).toBe("<ul><li>pokemon</li></ul>");
            expect(params).toEqual({ title: "Invalid fields: ", type: "danger" });
        },
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: '<form><field name="timmy" widget="many2many_tags" required="1"/></form>',
    });

    await clickSave();
    expect("[name='timmy'].o_field_invalid").toHaveCount(1);
});

test("set a required many2many_tags and save directly", async () => {
    let def;
    onRpc(async (args) => {
        expect.step(args.method);
        if (args.method === "web_read") {
            await def;
        }
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: '<form><field name="timmy" widget="many2many_tags" required="1"/></form>',
    });
    mockService("notification", {
        add: () => expect.step("notification"),
    });

    expect.verifySteps(["get_views", "onchange"]);

    expect(".o_tag").toHaveCount(0);

    def = new Deferred();
    await clickFieldDropdown("timmy");
    await clickFieldDropdownItem("timmy", "gold");
    expect(".o_tag").toHaveCount(1);
    expect(".o_tag").toHaveText("", {
        message: "The tag is displayed, but the web read is not finished yet",
    });

    expect.verifySteps(["name_search", "web_read"]);

    await clickSave();
    expect("[name='timmy']").not.toHaveClass("o_field_invalid");

    expect.verifySteps([]);

    def.resolve();
    await animationFrame();
    expect(".o_tag").toHaveText("gold");

    expect.verifySteps(["web_save"]);
});

test("Many2ManyTagsField with option 'no_quick_create' set to true", async () => {
    PartnerType._views = {
        form: `<form><field name="name"/><field name="color"/></form>`,
    };
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="timmy" widget="many2many_tags" options="{'no_quick_create': 1}"/>
            </form>`,
    });

    expect(".o_tag").toHaveCount(0);
    await contains(".o_field_many2many_tags .o-autocomplete--input").edit("new tag", {
        confirm: false,
    });
    await runAllTimers();
    expect(".o-autocomplete.dropdown li.o_m2o_dropdown_option").toHaveCount(1);
    expect(".o-autocomplete.dropdown li.o_m2o_dropdown_option").toHaveClass(
        "o_m2o_dropdown_option_create_edit"
    );
    await clickFieldDropdownItem("timmy", "Create and edit...");
    expect(".modal").toHaveCount(1);
    expect(".modal .o_field_widget[name=name] input").toHaveValue("new tag");
    await contains(".modal .o_form_button_save").click();
    expect(".o_tag").toHaveCount(1);
    expect(".o_tag").toHaveText("new tag");
});

test("Many2ManyTagsField keep the linked records after discard of the quick create dialog", async () => {
    PartnerType._views = {
        form: `<form><field name="name"/><field name="color"/></form>`,
    };
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="timmy" widget="many2many_tags" options="{'no_quick_create': 1}"/>
            </form>`,
    });

    expect(".o_tag").toHaveCount(0);
    await contains(".o_field_many2many_tags .o-autocomplete--input").edit("new tag", {
        confirm: false,
    });
    await runAllTimers();
    await clickFieldDropdownItem("timmy", "Create and edit...");
    await contains(".modal .o_form_button_save").click();
    expect(".o_tag").toHaveCount(1);
    await contains(".o_field_many2many_tags .o-autocomplete--input").edit("tago", {
        confirm: false,
    });
    await runAllTimers();
    await clickFieldDropdownItem("timmy", "Create and edit...");
    await contains(".modal .o_form_button_cancel").click();
    expect(".o_tag").toHaveCount(1);
});

test("Many2ManyTagsField with option 'no_create' set to true", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `<form><field name="timmy" widget="many2many_tags" options="{'no_create': 1}"/></form>`,
    });

    await contains(".o_field_many2many_tags .o-autocomplete--input").edit("new tag", {
        confirm: false,
    });
    await runAllTimers();
    expect(".o-autocomplete.dropdown li.o_m2o_dropdown_option").toHaveCount(0);
    expect(".o-autocomplete.dropdown li.o_m2o_no_result").toHaveCount(1);
});

test("Many2ManyTagsField with attribute 'can_create' set to false", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `<form><field name="timmy" widget="many2many_tags" can_create="0"/></form>`,
    });

    await contains(".o_field_many2many_tags .o-autocomplete--input").edit("new tag", {
        confirm: false,
    });
    await runAllTimers();
    expect(".o-autocomplete.dropdown li.o_m2o_dropdown_option").toHaveCount(0);
});

test("Many2ManyTagsField with arch context in form view", async () => {
    onRpc("name_search", async (args) => {
        const result = await args.parent();
        if (args.kwargs.context.append_coucou) {
            expect.step("name search with context given");
            for (const res of result) {
                res[1] += " coucou";
            }
        }
        return result;
    });
    onRpc("web_read", async (args) => {
        const result = await args.parent();
        if (args.kwargs.context.append_coucou) {
            expect.step("read with context given");
            result[0].display_name += " coucou";
        }
        return result;
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `<form><field name="timmy" widget="many2many_tags" context="{ 'append_coucou': True }"/></form>`,
    });

    await selectFieldDropdownItem("timmy", "gold coucou");

    expect.verifySteps(["name search with context given", "read with context given"]);
    expect(".o_field_tags").toHaveText("gold coucou");
});

test("Many2ManyTagsField with arch context in list view", async () => {
    onRpc("name_search", async (args) => {
        const result = await args.parent();
        if (args.kwargs.context.append_coucou) {
            expect.step("name search with context given");
            for (const res of result) {
                res[1] += " coucou";
            }
        }
        return result;
    });
    onRpc("web_read", async (args) => {
        const result = await args.parent();
        if (args.kwargs.context.append_coucou) {
            expect.step("read with context given");
            result[0].display_name += " coucou";
        }
        return result;
    });
    await mountView({
        type: "list",
        resModel: "partner",
        arch: `<list editable="top"><field name="timmy" widget="many2many_tags" context="{ 'append_coucou': True }"/></list>`,
    });

    await contains("[name=timmy]").click();
    await selectFieldDropdownItem("timmy", "gold coucou");

    expect.verifySteps(["name search with context given", "read with context given"]);
    expect(".o_field_tags:eq(0)").toHaveText("gold coucou");
});

test("Many2ManyTagsField doesn't use virtualId for 'name_search'", async () => {
    onRpc("name_search", ({ kwargs }) => {
        expect.step("name_search");
        // no virtualId in domain
        expect(kwargs.args).toEqual([]);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `<form>
            <field name="turtles" widget="many2many_tags"/>
            <field name="turtles">
                <list>
                    <field name="name"/>
                </list>
                <form>
                    <field name="name"/>
                </form>
            </field>
        </form>`,
    });
    await contains(".o_field_x2many_list_row_add a").click();
    expect(".modal").toHaveCount(1);

    await contains(".modal [name='name'] input").edit("yop");
    await contains(".modal .o_form_button_save").click();
    expect(".modal").toHaveCount(0);
    expect("[name='turtles'] .o_tag_badge_text").toHaveCount(2);
    expect("[name='turtles'] .o_data_row").toHaveCount(2);

    await contains("[name='turtles'] input").click();
    expect.verifySteps(["name_search"]);
});

test("Many2ManyTagsField selected records still pickable and not duplicable", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <list>
                <field name="turtles" widget="many2many_tags"/>
            </list>
        `,
    });

    // Check that records are correctly displayed in the dropdown
    await contains("div[name='turtles']").click();
    await contains("input[id=turtles_0]").click();
    expect("a.dropdown-item:eq(0)").toHaveText("leonardo");

    // Check that selecting a record adds the corresponding tag
    await contains("a.dropdown-item:eq(0)").click();
    expect(".o_tag").toHaveCount(1);
    expect(".o_tag:eq(0)").toHaveText("leonardo");

    // Check that a selected record is still shown in the dropdown
    await contains("input[id=turtles_0]").click();
    expect("a.dropdown-item:eq(0)").toHaveText("leonardo");

    // Check that selecting an already selected record doesn't duplicate it
    await contains("a.dropdown-item:eq(0)").click();
    expect(".o_tag").toHaveCount(1);

    // Check that deleting a record which was selected twice doens't leave one occurence
    await contains("a.o_delete").click();
    expect(".o_tag").toHaveCount(0);
});

test("Many2ManyTagsField with edit_tags option", async () => {
    expect.assertions(4);

    PartnerType._views = {
        form: `<form><field name="name"/><field name="color"/></form>`,
    };
    Partner._records[0].timmy = [12];

    onRpc("get_formview_id", ({ args }) => {
        expect(args[0]).toEqual([12], {
            message: "should call get_formview_id with correct id",
        });
        return false;
    });
    onRpc("partner.type", "web_save", ({ args }) => {
        expect(args[1]).toEqual({ name: "new" });
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="timmy" widget="many2many_tags" options="{'edit_tags': 1}"/>
            </form>`,
        resId: 1,
    });

    // Click to try to open form view dialog
    expect(".o_dialog").toHaveCount(0);
    await contains(".o_tag.badge").click();
    expect(".o_dialog").toHaveCount(1);

    // Edit name of tag
    await fieldInput("name").edit("new");
    await clickSave();
});

test("Many2ManyTagsField with edit_tags option overrides color edition", async () => {
    expect.assertions(4);

    PartnerType._views = {
        form: `<form><field name="name"/><field name="color"/></form>`,
    };
    Partner._records[0].timmy = [12];

    onRpc("get_formview_id", ({ args }) => {
        expect(args[0]).toEqual([12], {
            message: "should call get_formview_id with correct id",
        });
        return false;
    });
    onRpc("partner.type", "web_save", ({ args }) => {
        expect(args[1]).toEqual({ name: "new" });
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="timmy" widget="many2many_tags" options="{'edit_tags': 1, 'color_field': 'color'}"/>
            </form>`,
        resId: 1,
    });

    // Click to try to open form view dialog
    expect(".o_dialog").toHaveCount(0);
    await contains(".o_tag.badge").click();
    expect(".o_dialog").toHaveCount(1);

    // Edit name of tag
    await fieldInput("name").edit("new");
    await clickSave();
});

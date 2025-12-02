import { describe, expect, test } from "@odoo/hoot";
import { press, queryAllTexts, queryOne } from "@odoo/hoot-dom";
import { animationFrame, runAllTimers } from "@odoo/hoot-mock";
import { getOrigin } from "@web/core/utils/urls";

import {
    clickSave,
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

class Partner extends models.Model {
    name = fields.Char({ string: "Displayed name" });
    _records = [
        { id: 1, name: "first record" },
        { id: 2, name: "second record" },
        { id: 4, name: "aaa" },
    ];
}

class Turtle extends models.Model {
    name = fields.Char({ string: "Displayed name" });
    partner_ids = fields.Many2many({ string: "Partner", relation: "partner" });
    _records = [
        { id: 1, name: "leonardo", partner_ids: [] },
        { id: 2, name: "donatello", partner_ids: [2, 4] },
        { id: 3, name: "raphael" },
    ];
}

onRpc("has_group", () => true);

defineModels([Partner, Turtle]);

test("widget many2many_tags_avatar", async () => {
    await mountView({
        type: "form",
        resModel: "turtle",
        arch: `
            <form>
                <sheet>
                    <field name="partner_ids" widget="many2many_tags_avatar"/>
                </sheet>
            </form>`,
        resId: 1,
    });
    expect(queryAllTexts("[name='partner_ids'] .o_tag")).toEqual([]);
    expect("[name='partner_ids'] .o_input_dropdown input").toHaveValue("");

    await contains("[name='partner_ids'] .o_input_dropdown input").fill("first record");
    await runAllTimers();
    expect(queryAllTexts("[name='partner_ids'] .o_tag")).toEqual(["first record"]);
    expect("[name='partner_ids'] .o_input_dropdown input").toHaveValue("");

    await contains("[name='partner_ids'] .o_input_dropdown input").fill("abc");
    await runAllTimers();
    expect(queryAllTexts("[name='partner_ids'] .o_tag")).toEqual(["first record", "abc"]);
    expect("[name='partner_ids'] .o_input_dropdown input").toHaveValue("");
});

test("widget many2many_tags_avatar img src", async () => {
    await mountView({
        type: "form",
        resModel: "turtle",
        arch: `
            <form>
                <sheet>
                    <field name="partner_ids" widget="many2many_tags_avatar"/>
                </sheet>
            </form>`,
        resId: 2,
    });

    expect(".o_field_many2many_tags_avatar.o_field_widget .o_avatar img").toHaveCount(2);
    expect(
        `.o_field_many2many_tags_avatar.o_field_widget .o_avatar:nth-child(1) img[data-src='${getOrigin()}/web/image/partner/2/avatar_128']`
    ).toHaveCount(1);
});

test("widget many2many_tags_avatar in list view", async () => {
    for (let id = 5; id <= 15; id++) {
        Partner._records.push({
            id,
            name: `record ${id}`,
        });
    }

    Turtle._records.push({
        id: 4,
        name: "crime master gogo",
        partner_ids: [1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14],
    });
    Turtle._records[0].partner_ids = [1];
    Turtle._records[1].partner_ids = [1, 2, 4, 5, 6, 7];
    Turtle._records[2].partner_ids = [1, 2, 4, 5, 7];

    await mountView({
        type: "list",
        resModel: "turtle",
        arch: `
            <list editable="bottom">
                <field name="partner_ids" widget="many2many_tags_avatar"/>
            </list>`,
    });
    expect(
        `.o_data_row:nth-child(1) .o_field_many2many_tags_avatar .o_avatar img.o_m2m_avatar[data-src='${getOrigin()}/web/image/partner/1/avatar_128']`
    ).toHaveCount(1);
    expect(
        ".o_data_row .o_many2many_tags_avatar_cell .o_field_many2many_tags_avatar:eq(0)"
    ).toHaveText("first record");
    expect(
        ".o_data_row:nth-child(2) .o_field_many2many_tags_avatar .o_avatar:not(.o_m2m_avatar_empty) img"
    ).toHaveCount(4);
    expect(
        ".o_data_row:nth-child(3) .o_field_many2many_tags_avatar .o_avatar:not(.o_m2m_avatar_empty) img"
    ).toHaveCount(5);
    expect(
        ".o_data_row:nth-child(2) .o_field_many2many_tags_avatar .o_m2m_avatar_empty"
    ).toHaveCount(1);
    expect(
        ".o_data_row:nth-child(2) .o_field_many2many_tags_avatar .o_m2m_avatar_empty"
    ).toHaveText("+2");
    expect(
        `.o_data_row:nth-child(2) .o_field_many2many_tags_avatar .o_avatar:nth-child(1) img.o_m2m_avatar[data-src='${getOrigin()}/web/image/partner/1/avatar_128']`
    ).toHaveCount(1);
    expect(
        `.o_data_row:nth-child(2) .o_field_many2many_tags_avatar .o_avatar:nth-child(2) img.o_m2m_avatar[data-src='${getOrigin()}/web/image/partner/2/avatar_128']`
    ).toHaveCount(1);
    expect(
        `.o_data_row:nth-child(2) .o_field_many2many_tags_avatar .o_avatar:nth-child(3) img.o_m2m_avatar[data-src='${getOrigin()}/web/image/partner/4/avatar_128']`
    ).toHaveCount(1);
    expect(
        `.o_data_row:nth-child(2) .o_field_many2many_tags_avatar .o_avatar:nth-child(4) img.o_m2m_avatar[data-src='${getOrigin()}/web/image/partner/5/avatar_128']`
    ).toHaveCount(1);
    expect(
        ".o_data_row:nth-child(3) .o_field_many2many_tags_avatar .o_m2m_avatar_empty"
    ).toHaveCount(0);
    expect(
        ".o_data_row:nth-child(4) .o_field_many2many_tags_avatar .o_avatar:not(.o_m2m_avatar_empty) img"
    ).toHaveCount(4);
    expect(
        ".o_data_row:nth-child(4) .o_field_many2many_tags_avatar .o_m2m_avatar_empty"
    ).toHaveCount(1);
    expect(
        ".o_data_row:nth-child(4) .o_field_many2many_tags_avatar .o_m2m_avatar_empty"
    ).toHaveText("+9");

    // check data-tooltip attribute (used by the tooltip service)
    const tag = queryOne(
        ".o_data_row:nth-child(2) .o_field_many2many_tags_avatar .o_m2m_avatar_empty"
    );
    expect(tag).toHaveAttribute("data-tooltip-template", "web.TagsList.Tooltip");
    const tooltipInfo = JSON.parse(tag.dataset["tooltipInfo"]);
    expect(tooltipInfo.tags.map((tag) => tag.text).join(" ")).toBe("record 6 record 7", {
        message: "shows a tooltip on hover",
    });

    await contains(".o_data_row .o_many2many_tags_avatar_cell:eq(0)").click();
    await contains(
        ".o_data_row .o_many2many_tags_avatar_cell:eq(0) .o-autocomplete--input"
    ).click();
    await contains(".o-autocomplete--dropdown-item:eq(1)").click();
    await contains(".o_control_panel_main_buttons .o_list_button_save").click();
    expect(".o_data_row:eq(0) .o_field_many2many_tags_avatar .o_avatar img").toHaveCount(2);

    // Edit first row
    await contains(".o_data_row:nth-child(1) .o_data_cell").click();

    // Only the first row should have tags with delete buttons.
    expect(".o_data_row:nth-child(1) .o_field_tags span .o_delete").toHaveCount(2);
    expect(".o_data_row:nth-child(2) .o_field_tags span .o_delete").toHaveCount(0);
    expect(".o_data_row:nth-child(3) .o_field_tags span .o_delete").toHaveCount(0);
    expect(".o_data_row:nth-child(4) .o_field_tags span .o_delete").toHaveCount(0);
});

test("widget many2many_tags_avatar list view - don't crash on keyboard navigation", async () => {
    await mountView({
        type: "list",
        resModel: "turtle",
        arch: /*xml*/ `
                <list editable="bottom">
                    <field name="partner_ids" widget="many2many_tags_avatar"/>
                </list>
            `,
    });

    // Edit second row
    await contains(".o_data_row:nth-child(2) .o_data_cell").click();

    // Pressing left arrow should focus on the right-most (second) tag.
    await press("arrowleft");
    expect(".o_data_row:nth-child(2) .o_field_tags span:nth-child(2):first").toBeFocused();

    // Pressing left arrow again should not crash and should focus on the first tag.
    await press("arrowleft");
    expect(".o_data_row:nth-child(2) .o_field_tags span:nth-child(1):first").toBeFocused();
});

test("widget many2many_tags_avatar in kanban view", async () => {
    expect.assertions(21);

    for (let id = 5; id <= 15; id++) {
        Partner._records.push({
            id,
            name: `record ${id}`,
        });
    }

    Turtle._records.push({
        id: 4,
        name: "crime master gogo",
        partner_ids: [1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14],
    });
    Turtle._records[0].partner_ids = [1];
    Turtle._records[1].partner_ids = [1, 2, 4];
    Turtle._records[2].partner_ids = [1, 2, 4, 5];
    Turtle._views = {
        form: '<form><field name="name"/></form>',
    };
    Partner._views = {
        list: '<list><field name="name"/></list>',
    };

    await mountView({
        type: "kanban",
        resModel: "turtle",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="name"/>
                        <footer>
                            <field name="partner_ids" widget="many2many_tags_avatar"/>
                        </footer>
                    </t>
                </templates>
            </kanban>`,
        selectRecord(recordId) {
            expect(recordId).toBe(1, {
                message: "should call its selectRecord prop with the clicked record",
            });
        },
    });
    expect(".o_kanban_record:eq(0) .o_field_many2many_tags_avatar .o_quick_assign").toHaveCount(1);

    expect(
        ".o_kanban_record:nth-child(2) .o_field_many2many_tags_avatar .o_avatar img"
    ).toHaveCount(3);
    expect(
        ".o_kanban_record:nth-child(3) .o_field_many2many_tags_avatar .o_avatar img"
    ).toHaveCount(2);
    expect(
        `.o_kanban_record:nth-child(3) .o_field_many2many_tags_avatar .o_avatar:nth-child(1 of .o_tag) img.o_m2m_avatar[data-src='${getOrigin()}/web/image/partner/5/avatar_128']`
    ).toHaveCount(1);
    expect(
        `.o_kanban_record:nth-child(3) .o_field_many2many_tags_avatar .o_avatar:nth-child(2 of .o_tag) img.o_m2m_avatar[data-src='${getOrigin()}/web/image/partner/4/avatar_128']`
    ).toHaveCount(1);
    expect(
        ".o_kanban_record:nth-child(3) .o_field_many2many_tags_avatar .o_m2m_avatar_empty"
    ).toHaveCount(1);
    expect(
        ".o_kanban_record:nth-child(3) .o_field_many2many_tags_avatar .o_m2m_avatar_empty"
    ).toHaveText("+2");

    expect(
        ".o_kanban_record:nth-child(4) .o_field_many2many_tags_avatar .o_avatar img"
    ).toHaveCount(2);
    expect(
        ".o_kanban_record:nth-child(4) .o_field_many2many_tags_avatar .o_m2m_avatar_empty"
    ).toHaveCount(1);
    expect(
        ".o_kanban_record:nth-child(4) .o_field_many2many_tags_avatar .o_m2m_avatar_empty"
    ).toHaveText("9+");
    expect(".o_field_many2many_tags_avatar .o_field_many2many_selection").toHaveCount(0);
    await contains(".o_kanban_record:nth-child(3) .o_quick_assign", { visible: false }).click();
    await animationFrame();
    expect(".o-overlay-container input").toBeFocused();
    expect(".o-overlay-container .o_tag").toHaveCount(4);
    // delete inside the popover
    await contains(".o-overlay-container .o_tag .o_delete:eq(0)", {
        visible: false,
        displayed: true,
    }).click();
    expect(".o-overlay-container .o_tag").toHaveCount(3);
    expect(".o_kanban_record:nth-child(3) .o_tag").toHaveCount(3);
    // select first non selected input
    await contains(".o-overlay-container .o-autocomplete--dropdown-item:eq(4)").click();
    expect(".o-overlay-container .o_tag").toHaveCount(4);
    expect(".o_kanban_record:nth-child(3) .o_tag").toHaveCount(2);
    // load more
    await contains(".o-overlay-container .o_m2o_dropdown_option_search_more").click();
    // first non already selected item
    await contains(".o_dialog .o_list_table .o_data_row .o_data_cell:eq(3)").click();
    expect(".o-overlay-container .o_tag").toHaveCount(5);
    expect(".o_kanban_record:nth-child(3) .o_tag").toHaveCount(2);
    expect(
        `.o_kanban_record:nth-child(2) img.o_m2m_avatar[data-src='${getOrigin()}/web/image/partner/4/avatar_128']`
    ).toHaveCount(1);
    await contains(".o_kanban_record .o_field_many2many_tags_avatar img.o_m2m_avatar").click();
});

test("widget many2many_tags_avatar add/remove tags in kanban view", async () => {
    onRpc("web_save", ({ args }) => {
        const command = args[1].partner_ids[0];
        expect.step(`web_save: ${command[0]}-${command[1]}`);
    });
    await mountView({
        type: "kanban",
        resModel: "turtle",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="name"/>
                        <footer>
                            <field name="partner_ids" widget="many2many_tags_avatar"/>
                        </footer>
                    </t>
                </templates>
            </kanban>`,
    });
    await contains(".o_kanban_record:eq(0) .o_quick_assign", { visible: false }).click();
    // add and directly remove an item
    await contains(".o_popover .o-autocomplete--dropdown-item:eq(0)").click();
    await contains(".o_popover .o_tag .o_delete", { visible: false }).click();
    expect.verifySteps(["web_save: 4-1", "web_save: 3-1"]);
});

test("widget many2many_tags_avatar delete tag", async () => {
    await mountView({
        type: "form",
        resModel: "turtle",
        resId: 2,
        arch: `
            <form>
                <sheet>
                    <field name="partner_ids" widget="many2many_tags_avatar"/>
                </sheet>
            </form>`,
    });

    expect(".o_field_many2many_tags_avatar.o_field_widget .o_tag").toHaveCount(2);

    await contains(".o_field_many2many_tags_avatar.o_field_widget .o_tag .o_delete", {
        visible: false,
    }).click();
    expect(".o_field_many2many_tags_avatar.o_field_widget .o_tag").toHaveCount(1);

    await clickSave();
    expect(".o_field_many2many_tags_avatar.o_field_widget .o_tag").toHaveCount(1);
});

test("widget many2many_tags_avatar quick add tags and close in kanban view with keyboard navigation", async () => {
    await mountView({
        type: "kanban",
        resModel: "turtle",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="name"/>
                        <footer>
                            <field name="partner_ids" widget="many2many_tags_avatar"/>
                        </footer>
                    </t>
                </templates>
            </kanban>`,
    });
    await contains(".o_kanban_record:eq(0) .o_quick_assign", { visible: false }).click();
    // add and directly close the dropdown
    await press("Tab");
    await press("Enter");
    await animationFrame();
    expect(".o_kanban_record:eq(0) .o_field_many2many_tags_avatar .o_tag").toHaveCount(1);
    expect(".o_kanban_record:eq(0) .o_field_many2many_tags_avatar .o_popover").toHaveCount(0);
});

test("widget many2many_tags_avatar in kanban view missing access rights", async () => {
    expect.assertions(1);
    await mountView({
        type: "kanban",
        resModel: "turtle",
        arch: `
            <kanban edit="0" create="0">
                <templates>
                    <t t-name="card">
                        <field name="name"/>
                        <footer>
                            <field name="partner_ids" widget="many2many_tags_avatar"/>
                        </footer>
                    </t>
                </templates>
            </kanban>`,
    });

    expect(".o_kanban_record:eq(0) .o_field_many2many_tags_avatar .o_quick_assign").toHaveCount(0);
});

test("Many2ManyTagsAvatarField: make sure that the arch context is passed to the form view call", async () => {
    Partner._views = {
        form: `<form><field name="name"/></form>`,
    };
    onRpc("onchange", (args) => {
        if (args.model === "partner" && args.kwargs.context.append_coucou === "test_value") {
            expect.step("onchange with context given");
        }
    });

    await mountView({
        type: "list",
        resModel: "turtle",
        arch: `<list editable="top">
                <field name="partner_ids" widget="many2many_tags_avatar" context="{ 'append_coucou': 'test_value' }"/>
            </list>`,
    });

    await contains("div[name=partner_ids]").click();
    await contains(`div[name="partner_ids"] input`).edit("A new partner", { confirm: false });
    await runAllTimers();
    await contains(".o_m2o_dropdown_option_create_edit").click();

    expect(".modal .o_form_view").toHaveCount(1);
    expect.verifySteps(["onchange with context given"]);
});

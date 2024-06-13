import { describe, expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import {
    contains,
    defineActions,
    defineEmbeddedActions,
    defineModels,
    fields,
    getService,
    models,
    mountWithCleanup,
    onRpc,
    webModels,
    toggleSearchBarMenu,
    toggleMenuItem,
} from "@web/../tests/web_test_helpers";

import { browser } from "@web/core/browser/browser";
import { WebClient } from "@web/webclient/webclient";
import { router } from "@web/core/browser/router";
import { runAllTimers } from "@odoo/hoot-mock";

describe.current.tags("desktop");

const { ResCompany, ResPartner, ResUsers } = webModels;

class Partner extends models.Model {
    _rec_name = "display_name";

    display_name = fields.Char();
    foo = fields.Char();
    m2o = fields.Many2one({ relation: "partner" });
    o2m = fields.One2many({ relation: "partner" });

    _records = [
        { id: 1, display_name: "First record", foo: "yop", m2o: 3, o2m: [2, 3] },
        { id: 2, display_name: "Second record", foo: "blip", m2o: 3, o2m: [1, 4, 5] },
        { id: 3, display_name: "Third record", foo: "gnap", m2o: 1, o2m: [] },
        { id: 4, display_name: "Fourth record", foo: "plop", m2o: 1, o2m: [] },
        { id: 5, display_name: "Fifth record", foo: "zoup", m2o: 1, o2m: [] },
    ];
    _views = {
        "form,false": `
            <form>
                <header>
                    <button name="object" string="Call method" type="object"/>
                    <button name="4" string="Execute action" type="action"/>
                </header>
                <group>
                    <field name="display_name"/>
                    <field name="foo"/>
                </group>
            </form>`,
        "form,74": `
            <form>
                <sheet>
                    <div class="oe_button_box" name="button_box">
                        <button class="oe_stat_button" type="action" name="1" icon="fa-star" context="{'default_partner': id}">
                            <field string="Partners" name="o2m" widget="statinfo"/>
                        </button>
                    </div>
                    <field name="display_name"/>
                </sheet>
            </form>`,
        "kanban,1": `
            <kanban>
                <templates>
                    <t t-name="kanban-box">
                        <div class="oe_kanban_global_click">
                            <field name="foo"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
        "list,false": `<tree><field name="foo"/></tree>`,
        "pivot,false": `<pivot/>`,
        "search,false": `<search><field name="foo" string="Foo"/></search>`,
    };
}

class Pony extends models.Model {
    name = fields.Char();

    _records = [
        { id: 4, name: "Twilight Sparkle" },
        { id: 6, name: "Applejack" },
        { id: 9, name: "Fluttershy" },
    ];
    _views = {
        "list,false": `<tree><field name="name"/></tree>`,
        "kanban,false": `<kanban>
                            <templates>
                                <t t-name="kanban-box">
                                    <div class="oe_kanban_global_click">
                                        <field name="name"/>
                                    </div>
                                </t>
                            </templates>
                        </kanban>`,
        "form,false": `<form><field name="name"/></form>`,
        "search,false": `<search>
                            <filter name="my_filter" string="My filter" domain="[['name', '=', 'Applejack']]"/>
                        </search>`,
    };
}

defineModels([Partner, Pony, ResCompany, ResPartner, ResUsers]);

defineActions([
    {
        id: 1,
        xml_id: "action_1",
        name: "Partners Action 1",
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[1, "kanban"]],
    },
    {
        id: 2,
        xml_id: "action_2",
        name: "Partners",
        res_model: "partner",
        mobile_view_mode: "kanban",
        type: "ir.actions.act_window",
        views: [
            [false, "list"],
            [1, "kanban"],
            [false, "form"],
        ],
    },
    {
        id: 3,
        xml_id: "action_3",
        name: "Favorite Ponies",
        res_model: "pony",
        type: "ir.actions.act_window",
        views: [
            [false, "list"],
            [false, "kanban"],
            [false, "form"],
        ],
    },
]);

defineEmbeddedActions([
    {
        id: 2,
        xml_id: "embedded_action_2",
        name: "Embedded Action 2",
        parent_res_model: "partner",
        type: "ir.embedded.actions",
        parent_action_id: 1,
        action_id: 3,
    },
    {
        id: 3,
        name: "Embedded Action 3",
        parent_res_model: "partner",
        type: "ir.embedded.actions",
        parent_action_id: 1,
        python_method: "do_python_method",
    },
]);

test("can display embedded actions linked to the current action", async () => {
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    browser.localStorage.clear();
    expect(".o_control_panel").toHaveCount(1, { message: "should have rendered a control panel" });
    expect(".o_kanban_view").toHaveCount(1, { message: "should have rendered a kanban view" });
    expect(".o_control_panel_navigation > button > i.fa-sliders").toHaveCount(1, {
        message: "should display the toggle embedded button",
    });
    await contains(".o_control_panel_navigation > button > i.fa-sliders").click();
    expect(".o_embedded_actions").toHaveCount(1, { message: "should display the embedded" });
    expect(".o_embedded_actions_buttons_wrapper > button > span").toHaveText("Partners Action 1", {
        message:
            "The first embedded action should be the parent one and should be shown by default",
    });
});

test("can toggle visibility of embedded actions", async () => {
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    browser.localStorage.clear();
    await contains(".o_control_panel_navigation > button > i.fa-sliders").click();
    await contains(".o_embedded_actions_buttons_wrapper .dropdown").click();
    expect(".o_popover.dropdown-menu .dropdown-item").toHaveCount(4, {
        message: "Three embedded actions should be displayed in the dropdown + button 'Save View'",
    });
    expect(".dropdown-menu .dropdown-item.selected").toHaveCount(1, {
        message: "only one embedded action should be selected",
    });
    await contains(
        ".o_popover.dropdown-menu .dropdown-item > div > span:contains('Embedded Action 2')"
    ).click();
    expect(".o_embedded_actions_buttons_wrapper > button").toHaveCount(3, {
        message: "Should have 2 embedded actions in the embedded + the dropdown button",
    });
});

test("can click on a embedded action and execute the corresponding action (with xml_id)", async () => {
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    browser.localStorage.clear();
    await contains(".o_control_panel_navigation > button > i.fa-sliders").click();
    await contains(".o_embedded_actions_buttons_wrapper .dropdown").click();
    await contains(
        ".o_popover.dropdown-menu .dropdown-item > div > span:contains('Embedded Action 2')"
    ).click();
    await contains(
        ".o_embedded_actions_buttons_wrapper > button > span:contains('Embedded Action 2')"
    ).click();
    await runAllTimers();
    expect(router.current.action).toBe(3, {
        message: "the current action should be the one of the embedded action previously clicked",
    });
    expect(".o_list_view").toHaveCount(1, { message: "the view should be a list view" });
    expect(".o_embedded_actions").toHaveCount(1, { message: "the embedded should stay open" });
    expect(".o_embedded_actions_buttons_wrapper > button.active").toHaveText("Embedded Action 2", {
        message: "The second embedded action should be active",
    });
});

test("can click on a embedded action and execute the corresponding action (with python_method)", async () => {
    await mountWithCleanup(WebClient);
    onRpc("do_python_method", () => {
        return {
            id: 4,
            name: "Favorite Ponies from python action",
            res_model: "pony",
            type: "ir.actions.act_window",
            views: [[false, "kanban"]],
        };
    });
    await getService("action").doAction(1);
    browser.localStorage.clear();
    await contains(".o_control_panel_navigation > button > i.fa-sliders").click();
    await contains(".o_embedded_actions_buttons_wrapper .dropdown").click();
    await contains(
        ".o_popover.dropdown-menu .dropdown-item > div > span:contains('Embedded Action 3')"
    ).click();
    await contains(
        ".o_embedded_actions_buttons_wrapper > button > span:contains('Embedded Action 3')"
    ).click();
    await runAllTimers();
    expect(router.current.action).toBe(4, {
        message: "the current action should be the one of the embedded action previously clicked",
    });
    expect(".o_kanban_view").toHaveCount(1, { message: "the view should be a kanban view" });
    expect(".o_embedded_actions").toHaveCount(1, { message: "the embedded should stay open" });
    expect(".o_embedded_actions_buttons_wrapper > button.active").toHaveText("Embedded Action 3", {
        message: "The third embedded action should be active",
    });
});

test("breadcrumbs are updated when clicking on embeddeds", async () => {
    await mountWithCleanup(WebClient);
    onRpc("do_python_method", () => {
        return {
            id: 4,
            name: "Favorite Ponies from python action",
            res_model: "pony",
            type: "ir.actions.act_window",
            views: [[false, "kanban"]],
        };
    });
    await getService("action").doAction(1);
    browser.localStorage.clear();
    await contains(".o_control_panel_navigation > button > i.fa-sliders").click();
    await contains(".o_embedded_actions_buttons_wrapper .dropdown").click();
    await contains(
        ".o_popover.dropdown-menu .dropdown-item > div > span:contains('Embedded Action 2')"
    ).click();
    await contains(
        ".o_popover.dropdown-menu .dropdown-item > div > span:contains('Embedded Action 3')"
    ).click();
    expect(".o_control_panel .breadcrumb-item").toHaveCount(0);
    expect(".o_control_panel .o_breadcrumb .active").toHaveText("Partners Action 1");
    await contains(
        ".o_embedded_actions_buttons_wrapper > button > span:contains('Embedded Action 2')"
    ).click();
    await runAllTimers();
    expect(router.current.action).toBe(3, {
        message: "the current action should be the one of the embedded action previously clicked",
    });
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners Action 1",
        "Favorite Ponies",
    ]);
    await contains(
        ".o_embedded_actions_buttons_wrapper > button > span:contains('Embedded Action 3')"
    ).click();
    await runAllTimers();
    expect(router.current.action).toBe(4, {
        message: "the current action should be the one of the embedded action previously clicked",
    });
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Partners Action 1",
        "Favorite Ponies from python action",
    ]);
});

test("a view coming from a embedded can be saved in the embedded actions", async () => {
    onRpc("create", ({ args }) => {
        expect(args[0][0].name).toBe("Custom Embedded Action 2");
        return [4, args[0][0].name]; // Fake new embedded action id
    });
    onRpc("create_or_replace", ({ args }) => {
        expect(args[0].domain).toBe(`[["name", "=", "Applejack"]]`);
        expect(args[0].embedded_action_id).toBe(4);
        expect(args[0].user_id).toBe(false);
        return 5; // Fake new filter id
    });
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    browser.localStorage.clear();
    await contains(".o_control_panel_navigation > button > i.fa-sliders").click();
    await contains(".o_embedded_actions_buttons_wrapper .dropdown").click();
    await contains(
        ".o_popover.dropdown-menu .dropdown-item > div > span:contains('Embedded Action 2')"
    ).click();
    await contains(
        ".o_embedded_actions_buttons_wrapper > button > span:contains('Embedded Action 2')"
    ).click();
    await runAllTimers();
    expect(router.current.action).toBe(3, {
        message: "the current action should be the one of the embedded action previously clicked",
    });
    expect(".o_list_view").toHaveCount(1, { message: "the view should be a list view" });
    await contains("button.o_switch_view.o_kanban").click();
    expect(".o_kanban_view").toHaveCount(1, { message: "the view should be a kanban view" });
    await toggleSearchBarMenu();
    await toggleMenuItem("My filter");
    await toggleSearchBarMenu();
    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(1, {
        message: "There should be one record",
    });
    await contains(".o_embedded_actions_buttons_wrapper .dropdown").click();
    await contains(".o_save_current_view ").click();
    await contains("input.form-check-input").click();
    await contains(".o_save_favorite ").click();
    expect(".o_embedded_actions_buttons_wrapper > button").toHaveCount(4, {
        message: "Should have 2 embedded actions in the embedded + the dropdown button",
    });
});

import { describe, expect, test, beforeEach } from "@odoo/hoot";
import { queryAllTexts, waitFor } from "@odoo/hoot-dom";
import {
    contains,
    defineActions,
    defineModels,
    fields,
    getService,
    models,
    mountWithCleanup,
    onRpc,
    toggleMenuItem,
    toggleSearchBarMenu,
    webModels,
    getKwArgs,
} from "@web/../tests/web_test_helpers";

import { animationFrame, mockTouch, runAllTimers } from "@odoo/hoot-mock";
import { browser } from "@web/core/browser/browser";
import { router, routerBus } from "@web/core/browser/router";
import { rpcBus } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { WebClient } from "@web/webclient/webclient";

describe.current.tags("desktop");

const { ResCompany, ResPartner, ResUsers, ResUsersSettings: WebResUsersSettings } = webModels;

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
        form: `
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
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        list: `<list><field name="foo"/></list>`,
        search: `<search><field name="foo" string="Foo"/></search>`,
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
        list: `<list>
                            <field name="name"/>
                            <button name="action_test" type="object" string="Action Test" column_invisible="not context.get('display_button')"/>
                        </list>`,
        kanban: `<kanban>
                            <templates>
                                <t t-name="card">
                                    <field name="name"/>
                                </t>
                            </templates>
                        </kanban>`,
        form: `<form><field name="name"/></form>`,
        search: `<search>
                            <filter name="my_filter" string="My filter" domain="[['name', '=', 'Applejack']]"/>
                        </search>`,
    };
}

class ResUsersSettings extends WebResUsersSettings {
    /** @param {number[]} id */
    get_embedded_actions_settings(id) {
        /** @type {import("mock_models").ResUsersSettingsEmbeddedAction} */
        const ResUsersSettingsEmbeddedAction = this.env["res.users.settings.embedded.action"];
        return ResUsersSettingsEmbeddedAction.embedded_action_settings_format(id);
    }

    /**
     * @param {number} action_id
     * @param {number} res_id
     * @param {number} vals
     */
    set_embedded_actions_setting(id, action_id, res_id, vals) {
        const kwargs = getKwArgs(arguments, "id", "action_id", "res_id", "vals");
        id = kwargs.id;
        action_id = kwargs.action_id;
        res_id = kwargs.res_id;
        vals = kwargs.vals;

        /** @type {import("mock_models").ResUsersSettingsEmbeddedAction} */
        const ResUsersSettingsEmbeddedAction = this.env["res.users.settings.embedded.action"];

        let [embeddedSettings] = ResUsersSettingsEmbeddedAction.search_read([
            ["user_setting_id", "=", id],
            ["action_id", "=", action_id],
            ["res_id", "=", res_id],
        ]);
        for (const [field, value] of Object.entries(vals)) {
            if (["embedded_actions_order", "embedded_actions_visibility"].includes(field)) {
                vals[field] = value
                    .map((action_id) => (action_id === false ? "false" : String(action_id)))
                    .join(",");
            }
        }
        if (!embeddedSettings) {
            embeddedSettings = ResUsersSettingsEmbeddedAction.create({
                action_id,
                res_id,
                ...vals,
            });
        } else {
            ResUsersSettingsEmbeddedAction.write(embeddedSettings.id, vals);
        }
    }
}

class ResUsersSettingsEmbeddedAction extends models.ServerModel {
    _name = "res.users.settings.embedded.action";

    /** @param {number[]} ids */
    embedded_action_settings_format(ids) {
        const embeddedSettings = {};
        for (const embeddedSettingsRecord of this.browse(ids)) {
            embeddedSettings[
                `${embeddedSettingsRecord.action_id}+${embeddedSettingsRecord.resId || ""}`
            ] = {
                embedded_actions_order: embeddedSettingsRecord.embedded_actions_order
                    ? embeddedSettingsRecord.embedded_actions_order
                          .split(",")
                          .map((action_id) => (action_id === "false" ? false : parseInt(action_id)))
                    : [],
                embedded_actions_visibility: embeddedSettingsRecord.embedded_actions_visibility
                    ? embeddedSettingsRecord.embedded_actions_visibility
                          .split(",")
                          .map((action_id) => (action_id === "false" ? false : parseInt(action_id)))
                    : [],
                embedded_visibility: embeddedSettingsRecord.embedded_visibility,
            };
        }
        return embeddedSettings;
    }
}

class IrActionsAct_Window extends models.ServerModel {
    _name = "ir.actions.act_window";

    _records = [{ id: 1 }, { id: 4 }];
}

defineModels([
    Partner,
    Pony,
    ResCompany,
    ResPartner,
    ResUsers,
    ResUsersSettings,
    ResUsersSettingsEmbeddedAction,
    IrActionsAct_Window,
]);

const actions = [
    {
        id: 1,
        xml_id: "action_1",
        name: "Partners Action 1",
        res_model: "partner",
        views: [[1, "kanban"]],
    },
    {
        id: 2,
        xml_id: "action_2",
        name: "Partners",
        res_model: "partner",
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
        views: [
            [false, "list"],
            [false, "kanban"],
            [false, "form"],
        ],
    },
    {
        id: 4,
        xml_id: "action_4",
        name: "Ponies",
        res_model: "pony",
        views: [
            [false, "list"],
            [false, "kanban"],
            [false, "form"],
        ],
    },
    {
        id: 102,
        xml_id: "embedded_action_2",
        name: "Embedded Action 2",
        parent_res_model: "partner",
        type: "ir.embedded.actions",
        parent_action_id: 1,
        action_id: 3,
        context: {
            display_button: true,
        },
    },
    {
        id: 103,
        name: "Embedded Action 3",
        parent_res_model: "partner",
        type: "ir.embedded.actions",
        parent_action_id: 1,
        python_method: "do_python_method",
    },
    {
        id: 104,
        name: "Custom Embedded Action 4",
        type: "ir.embedded.actions",
        user_id: user.userId,
        parent_action_id: 4,
        action_id: 4,
    },
];

defineActions(actions);

beforeEach(() => {
    user.updateUserSettings("id", 1); // workaround to populate the user settings
    user.updateUserSettings("embedded_actions_config_ids", {}); // workaround to populate the embedded user settings
});

test("can display embedded actions linked to the current action", async () => {
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    expect(".o_control_panel").toHaveCount(1, { message: "should have rendered a control panel" });
    expect(".o_kanban_view").toHaveCount(1, { message: "should have rendered a kanban view" });
    expect(".o_control_panel_navigation > button > i.fa-sliders").toHaveCount(1, {
        message: "should display the toggle embedded button",
    });
    await contains(".o_control_panel_navigation > button > i.fa-sliders").click();
    expect(".o_embedded_actions").toHaveCount(1, { message: "should display the embedded" });
    expect(".o_embedded_actions > button > span").toHaveText("Partners Action 1", {
        message:
            "The first embedded action should be the parent one and should be shown by default",
    });
    expect(user.settings.embedded_actions_config_ids).toEqual({
        "1+": {
            embedded_actions_order: [],
            embedded_actions_visibility: [false],
            embedded_visibility: true,
            res_model: "partner",
        },
    });
});

test("can toggle visibility of embedded actions", async () => {
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    await contains(".o_control_panel_navigation > button > i.fa-sliders").click();
    await waitFor(".o_popover.dropdown-menu");
    expect(".o_popover.dropdown-menu .dropdown-item").toHaveCount(4, {
        message: "Three embedded actions should be displayed in the dropdown + button 'Save View'",
    });
    expect(".dropdown-menu .dropdown-item.selected").toHaveCount(1, {
        message: "only one embedded action should be selected",
    });
    await contains(
        ".o_popover.dropdown-menu .dropdown-item > div > span:contains('Embedded Action 2')"
    ).click();
    expect(".o_embedded_actions > button").toHaveCount(3, {
        message: "Should have 2 embedded actions in the embedded + the dropdown button",
    });
    expect(user.settings.embedded_actions_config_ids).toEqual({
        "1+": {
            embedded_actions_order: [],
            embedded_actions_visibility: [false, 102],
            embedded_visibility: true,
            res_model: "partner",
        },
    });
});

test("can click on a embedded action and execute the corresponding action (with xml_id)", async () => {
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    await contains(".o_control_panel_navigation > button > i.fa-sliders").click();
    await waitFor(".o_popover.dropdown-menu");
    await contains(
        ".o_popover.dropdown-menu .dropdown-item > div > span:contains('Embedded Action 2')"
    ).click();
    await contains(".o_embedded_actions > button > span:contains('Embedded Action 2')").click();
    await runAllTimers();
    expect(router.current.action).toBe(3, {
        message: "the current action should be the one of the embedded action previously clicked",
    });
    expect(".o_list_view").toHaveCount(1, { message: "the view should be a list view" });
    expect(".o_embedded_actions").toHaveCount(1, { message: "the embedded should stay open" });
    expect(".o_embedded_actions > button.active").toHaveText("Embedded Action 2", {
        message: "The second embedded action should be active",
    });
});

test("can click on a embedded action and execute the corresponding action (with python_method)", async () => {
    await mountWithCleanup(WebClient);
    onRpc("do_python_method", () => ({
        id: 4,
        name: "Favorite Ponies from python action",
        res_model: "pony",
        type: "ir.actions.act_window",
        views: [[false, "kanban"]],
    }));
    await getService("action").doAction(1);
    await contains(".o_control_panel_navigation > button > i.fa-sliders").click();
    await waitFor(".o_popover.dropdown-menu");
    await contains(
        ".o_popover.dropdown-menu .dropdown-item > div > span:contains('Embedded Action 3')"
    ).click();
    await contains(".o_embedded_actions > button > span:contains('Embedded Action 3')").click();
    await runAllTimers();
    expect(router.current.action).toBe(4, {
        message: "the current action should be the one of the embedded action previously clicked",
    });
    expect(".o_kanban_view").toHaveCount(1, { message: "the view should be a kanban view" });
    expect(".o_embedded_actions").toHaveCount(1, { message: "the embedded should stay open" });
    expect(".o_embedded_actions > button.active").toHaveText("Embedded Action 3", {
        message: "The third embedded action should be active",
    });
});

test("breadcrumbs are updated when clicking on embeddeds", async () => {
    await mountWithCleanup(WebClient);
    onRpc("do_python_method", () => ({
        id: 4,
        name: "Favorite Ponies from python action",
        res_model: "pony",
        type: "ir.actions.act_window",
        views: [[false, "kanban"]],
    }));
    await getService("action").doAction(1);
    await contains(".o_control_panel_navigation > button > i.fa-sliders").click();
    await waitFor(".o_popover.dropdown-menu");
    await contains(
        ".o_popover.dropdown-menu .dropdown-item > div > span:contains('Embedded Action 2')"
    ).click();
    await contains(
        ".o_popover.dropdown-menu .dropdown-item > div > span:contains('Embedded Action 3')"
    ).click();
    expect(".o_control_panel .breadcrumb-item").toHaveCount(0);
    expect(".o_control_panel .o_breadcrumb .active").toHaveText("Partners Action 1");
    expect(browser.location.href).toBe("https://www.hoot.test/odoo/action-1");
    await contains(".o_embedded_actions > button > span:contains('Embedded Action 2')").click();
    await runAllTimers();
    expect(browser.location.href).toBe("https://www.hoot.test/odoo/action-3");
    expect(router.current.action).toBe(3, {
        message: "the current action should be the one of the embedded action previously clicked",
    });
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual(["Favorite Ponies"]);
    await contains(".o_embedded_actions > button > span:contains('Embedded Action 3')").click();
    await runAllTimers();
    expect(browser.location.href).toBe("https://www.hoot.test/odoo/action-4");
    expect(router.current.action).toBe(4, {
        message: "the current action should be the one of the embedded action previously clicked",
    });
    expect(queryAllTexts(".breadcrumb-item, .o_breadcrumb .active")).toEqual([
        "Favorite Ponies from python action",
    ]);
});

test("a view coming from a embedded can be saved in the embedded actions", async () => {
    onRpc("create", ({ args }) => {
        const values = args[0][0];
        expect(values.name).toBe("Custom Embedded Action 2");
        expect(values.action_id).toBe(3);
        expect(values).not.toInclude("python_method");
        return [4, values.name]; // Fake new embedded action id
    });
    onRpc("create_filter", ({ args }) => {
        expect(args[0].domain).toBe(`[["name", "=", "Applejack"]]`);
        expect(args[0].embedded_action_id).toBe(4);
        expect(args[0].user_ids).toEqual([]);
        return [5]; // Fake new filter id
    });
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    await contains(".o_control_panel_navigation > button > i.fa-sliders").click();
    await waitFor(".o_popover.dropdown-menu");
    await contains(
        ".o_popover.dropdown-menu .dropdown-item > div > span:contains('Embedded Action 2')"
    ).click();
    await contains(".o_embedded_actions > button > span:contains('Embedded Action 2')").click();
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
    await contains(".o_embedded_actions .dropdown").click();
    await contains(".o_save_current_view ").click();
    await contains("input.form-check-input").click();
    await contains(".o_save_favorite ").click();
    expect(".o_embedded_actions > button").toHaveCount(4, {
        message: "Should have 2 embedded actions in the embedded + the dropdown button",
    });
    expect(user.settings.embedded_actions_config_ids).toEqual({
        "1+": {
            embedded_actions_order: [false, 102, 103, 4],
            embedded_actions_visibility: [false, 102, 4],
            embedded_visibility: true,
            res_model: "partner",
        },
    });
});

test("a view coming from a embedded with python_method can be saved in the embedded actions", async () => {
    onRpc(({ args, method }) => {
        let values;
        if (method === "create") {
            values = args[0][0];
            expect(values.name).toBe("Custom Embedded Action 3");
            expect(values.python_method).toBe("do_python_method");
            expect(values).not.toInclude("action_id");
            return [4, values.name]; // Fake new embedded action id
        } else if (method === "create_filter") {
            values = args[0][0];
            expect(args[0].domain).toBe(`[["name", "=", "Applejack"]]`);
            expect(args[0].embedded_action_id).toBe(4);
            expect(args[0].user_ids).toEqual([]);
            return 5; // Fake new filter id
        } else if (method === "do_python_method") {
            return {
                id: 4,
                name: "Favorite Ponies from python action",
                res_model: "pony",
                type: "ir.actions.act_window",
                views: [
                    [false, "list"],
                    [false, "kanban"],
                ],
            };
        }
    });
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    await contains(".o_control_panel_navigation > button > i.fa-sliders").click();
    await waitFor(".o_popover.dropdown-menu");
    await contains(
        ".o_popover.dropdown-menu .dropdown-item > div > span:contains('Embedded Action 3')"
    ).click();
    await contains(".o_embedded_actions > button > span:contains('Embedded Action 3')").click();
    await runAllTimers();
    expect(router.current.action).toBe(4, {
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
    await contains(".o_embedded_actions .dropdown").click();
    await contains(".o_save_current_view ").click();
    await contains("input.form-check-input").click();
    await contains(".o_save_favorite ").click();
    expect(".o_embedded_actions > button").toHaveCount(4, {
        message: "Should have 2 embedded actions in the embedded + the dropdown button",
    });
    expect(user.settings.embedded_actions_config_ids).toEqual({
        "1+": {
            embedded_actions_order: [false, 102, 103, 4],
            embedded_actions_visibility: [false, 103, 4],
            embedded_visibility: true,
            res_model: "partner",
        },
    });
});

test("the embedded actions should not be displayed when switching view", async () => {
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    await contains(".o_control_panel_navigation > button > i.fa-sliders").click();
    await waitFor(".o_popover.dropdown-menu");
    await contains(
        ".o_popover.dropdown-menu .dropdown-item > div > span:contains('Embedded Action 2')"
    ).click();
    await contains(".o_embedded_actions > button > span:contains('Embedded Action 2')").click();
    await contains(".o_control_panel_navigation > button > i.fa-sliders").click();
    await contains("button.o_switch_view.o_kanban").click();
    expect(".o_embedded_actions").toHaveCount(0, {
        message: "The embedded actions menu should not be displayed",
    });
});

test("User can move the main (first) embedded action", async () => {
    mockTouch(true);
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    await contains(".o_control_panel_navigation > button > i.fa-sliders").click();
    await waitFor(".o_popover.dropdown-menu");
    await contains(
        ".o_popover.dropdown-menu .dropdown-item > div > span:contains('Embedded Action 2')"
    ).click();
    await contains(".o_embedded_actions > button:first-child").dragAndDrop(
        ".o_embedded_actions > button:nth-child(2)"
    );
    expect(".o_embedded_actions > button:nth-child(2) > span").toHaveText("Partners Action 1", {
        message: "Main embedded action should've been moved to 2nd position",
    });
    expect(user.settings.embedded_actions_config_ids).toEqual({
        "1+": {
            embedded_actions_order: [102, false, 103],
            embedded_actions_visibility: [false, 102],
            embedded_visibility: true,
            res_model: "partner",
        },
    });
});

test("User can unselect the main (first) embedded action", async () => {
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    await contains(".o_control_panel_navigation > button > i.fa-sliders").click();
    await waitFor(".o_popover.dropdown-menu");
    const dropdownItem =
        ".o_popover.dropdown-menu .dropdown-item > div > span:contains('Partners Action 1')";
    expect(dropdownItem).not.toHaveClass("text-muted", {
        message: "Main embedded action should not be displayed in muted",
    });
    await contains(dropdownItem).click();
    expect(dropdownItem).not.toHaveClass("selected", {
        message: "Main embedded action should be unselected",
    });
    expect(user.settings.embedded_actions_config_ids).toEqual({
        "1+": {
            embedded_actions_order: [],
            embedded_actions_visibility: [],
            embedded_visibility: true,
            res_model: "partner",
        },
    });
});

test("User should be redirected to the first embedded action set in user settings", async () => {
    // set embedded action 2 in first
    user.updateUserSettings("embedded_actions_config_ids", {
        "1+": {
            embedded_actions_visibility: [102],
            embedded_visibility: false,
            embedded_actions_order: [102, false, 103],
        },
    });
    await mountWithCleanup(WebClient);
    await getService("action").doActionButton({
        name: 1,
        type: "action",
    });
    await contains(".o_control_panel_navigation > button > i.fa-sliders").click();
    expect(".o_embedded_actions > button:first-child").toHaveClass("active", {
        message: "First embedded action in order should have the 'active' class",
    });
    expect(".o_embedded_actions > button:first-child > span").toHaveText("Embedded Action 2", {
        message: "First embedded action in order should be 'Embedded Action 2'",
    });
    expect(".o_last_breadcrumb_item > span").toHaveText("Favorite Ponies", {
        message: "'Favorite Ponies' view should be loaded",
    });
    expect(".o_list_renderer .btn-link").toHaveCount(3, {
        message:
            "The button should be displayed since `display_button` is true in the context of the embedded action 2",
    });
});

test("execute a regular action from an embedded action", async () => {
    Pony._views["form"] = `
        <form>
            <button type="action" name="2" string="Execute another action"/>
            <field name="name"/>
        </form>`;
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    expect(".o_kanban_view").toHaveCount(1);

    await contains(".o_control_panel_navigation button .fa-sliders").click();
    expect(".o_control_panel .o_embedded_actions button:not(.dropdown-toggle)").toHaveCount(1);

    await waitFor(".o_popover.dropdown-menu");
    await contains(".dropdown-menu .dropdown-item span:contains('Embedded Action 2')").click();
    expect(".o_control_panel .o_embedded_actions button:not(.dropdown-toggle)").toHaveCount(2);

    await contains(".o_control_panel .o_embedded_actions button:eq(1)").click();
    expect(".o_list_view").toHaveCount(1);

    await contains(".o_data_row .o_data_cell").click();
    expect(".o_form_view").toHaveCount(1);

    await contains(".o_form_view button[type=action]").click();
    expect(".o_control_panel .o_embedded_actions").toHaveCount(0);
});

test("custom embedded action loaded first", async () => {
    // set embedded action 4 in first
    user.updateUserSettings("embedded_actions_config_ids", {
        "4+": {
            embedded_actions_visibility: [104],
            embedded_visibility: false,
            embedded_actions_order: [104, false],
        },
    });
    await mountWithCleanup(WebClient);
    await getService("action").doActionButton({
        name: 4,
        type: "action",
    });
    expect(".o_list_view").toHaveCount(1);
    await contains(".o_control_panel_navigation > button > i.fa-sliders").click();
    expect(".o_embedded_actions > button:first-child").toHaveClass("active", {
        message: "First embedded action in order should have the 'active' class",
    });
    expect(".o_embedded_actions > button:first-child > span").toHaveText(
        "Custom Embedded Action 4",
        {
            message: "First embedded action in order should be 'Embedded Action 4'",
        }
    );
    expect(".o_last_breadcrumb_item > span").toHaveText("Ponies", {
        message: "'Favorite Ponies' view should be loaded",
    });
});

test("test get_embedded_actions_settings rpc args", async () => {
    onRpc("res.users.settings", "get_embedded_actions_settings", ({ args, kwargs }) => {
        expect(args.length).toBe(1, {
            message: "Should have one positional argument, which is the id of the user setting.",
        });
        expect(args[0]).toBe(1, { message: "The id of the user setting should be 1." });
        expect(kwargs.context.res_id).toBe(5, {
            message: "The context should contain the res_id passed to the action.",
        });
        expect(kwargs.context.res_model).toBe("partner", {
            message: "The context should contain the res_model passed to the action.",
        });
        expect.step("get_embedded_actions_settings");
    });
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1, {
        additionalContext: { active_id: 5 },
    });
    await contains(".o_control_panel_navigation > button > i.fa-sliders").click();
    expect.verifySteps(["get_embedded_actions_settings"]);
});

test("an action containing embedded actions should reload if the page is refreshed", async () => {
    onRpc("create", ({ args }) => {
        const values = args[0][0];
        expect(values.name).toBe("Custom Partners Action 1");
        expect(values.action_id).toBe(1);
        // Add the created embedded action to the actions list so that the mock server knows it when reloading (/web/action/load)
        defineActions([
            ...actions,
            {
                id: 4,
                name: "Custom Partners Action 1",
                parent_res_model: values.parent_res_model,
                type: "ir.embedded.actions",
                parent_action_id: 1,
                action_id: values.action_id,
            },
        ]);
        return [4, values.name]; // Fake new embedded action id
    });
    onRpc(
        "create_filter",
        () => [5] // Fake new filter id
    );

    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    // First, we create a new (custom) embedded action based on the current one
    await contains(".o_control_panel_navigation > button > i.fa-sliders").click();
    await waitFor(".o_popover.dropdown-menu");
    await contains(".o_save_current_view ").click();
    await contains(".o_save_favorite ").click();
    expect(".o_embedded_actions > button").toHaveCount(3, {
        message: "Should have 2 embedded actions in the embedded + the dropdown button",
    });

    // Emulate a hard refresh of the page
    rpcBus.trigger("CLEAR-CACHES", "/web/action/load");
    routerBus.trigger("ROUTE_CHANGE");
    await animationFrame();

    // Check that the created embedded action is still there, as the reload should be done
    expect(".o_embedded_actions > button").toHaveCount(3, {
        message:
            "After refresh, we should still have 2 embedded actions in the embedded + the dropdown button",
    });
});

import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import { Deferred, animationFrame } from "@odoo/hoot-mock";
import { Component, onMounted, xml } from "@odoo/owl";
import {
    contains,
    defineActions,
    defineMenus,
    defineModels,
    editSearch,
    fields,
    getService,
    models,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    validateSearch,
} from "@web/../tests/web_test_helpers";

import { browser } from "@web/core/browser/browser";
import { router } from "@web/core/browser/router";
import { registry } from "@web/core/registry";
import { redirect } from "@web/core/utils/urls";
import { WebClient } from "@web/webclient/webclient";

describe.current.tags("desktop");

const actionRegistry = registry.category("actions");

defineActions([
    {
        id: 3,
        xml_id: "action_3",
        name: "Partners",
        res_model: "partner",
        views: [
            [false, "list"],
            [1, "kanban"],
            [false, "form"],
        ],
    },
    {
        id: 4,
        xml_id: "action_4",
        name: "Partners Action 4",
        res_model: "partner",
        views: [
            [1, "kanban"],
            [2, "list"],
            [false, "form"],
        ],
    },
    {
        id: 8,
        xml_id: "action_8",
        name: "Favorite Ponies",
        res_model: "pony",
        views: [
            [false, "list"],
            [false, "form"],
        ],
    },
    {
        id: 1001,
        tag: "__test__client__action__",
        target: "main",
        type: "ir.actions.client",
        params: { description: "Id 1" },
    },
    {
        id: 1002,
        tag: "__test__client__action__",
        target: "main",
        type: "ir.actions.client",
        params: { description: "Id 2" },
    },
]);

defineMenus([
    { id: 0 }, // prevents auto-loading the first action
    { id: 1, actionID: 1001 },
    { id: 2, actionID: 1002 },
]);

class Partner extends models.Model {
    name = fields.Char();
    foo = fields.Char();
    parent_id = fields.Many2one({ relation: "partner" });
    child_ids = fields.One2many({ relation: "partner", relation_field: "parent_id" });

    _records = [
        { id: 1, name: "First record", foo: "yop" },
        { id: 2, name: "Second record", foo: "blip" },
        { id: 3, name: "Third record", foo: "gnap" },
        { id: 4, name: "Fourth record", foo: "plop" },
        { id: 5, name: "Fifth record", foo: "zoup" },
    ];
    _views = {
        "kanban,1": /* xml */ `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>
        `,
        "list,2": /* xml */ `
            <list>
                <field name="foo" />
            </list>
        `,
        form: /* xml */ `
            <form>
                <header>
                    <button name="object" string="Call method" type="object"/>
                    <button name="4" string="Execute action" type="action"/>
                </header>
                <group>
                    <field name="display_name"/>
                    <field name="foo"/>
                </group>
            </form>
        `,
        search: /* xml */ `
            <search>
                <field name="foo" string="Foo" />
            </search>
        `,
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
        list: `<list><field name="name"/></list>`,
        form: `<form><field name="name"/></form>`,
    };
}

class User extends models.Model {
    _name = "res.users";
    has_group() {
        return true;
    }
}

defineModels([Partner, Pony, User]);

class TestClientAction extends Component {
    static template = xml`
        <div class="test_client_action">
            ClientAction_<t t-esc="props.action.params?.description"/>
        </div>
    `;
    static props = ["*"];

    setup() {
        onMounted(() => {
            this.env.config.setDisplayName(`Client action ${this.props.action.id}`);
        });
    }
}

onRpc("has_group", () => true);

beforeEach(() => {
    actionRegistry.add("__test__client__action__", TestClientAction);
    patchWithCleanup(browser.location, {
        origin: "http://example.com",
    });
    redirect("/odoo");
});

test(`basic action as App`, async () => {
    await mountWithCleanup(WebClient);
    expect(browser.location.href).toBe("http://example.com/odoo");
    expect(router.current).toEqual({});

    await contains(`.o_navbar_apps_menu button`).click();
    await contains(`.o-dropdown-item:eq(2)`).click();
    await animationFrame();
    await animationFrame();
    expect(router.current.action).toBe(1002);
    expect(browser.location.href).toBe("http://example.com/odoo/action-1002");
    expect(`.test_client_action`).toHaveText("ClientAction_Id 2");
    expect(`.o_menu_brand`).toHaveText("App2");
});

test(`do action keeps menu in url`, async () => {
    await mountWithCleanup(WebClient);
    expect(browser.location.href).toBe("http://example.com/odoo");
    expect(router.current).toEqual({});

    await contains(`.o_navbar_apps_menu button`).click();
    await contains(`.o-dropdown-item:eq(2)`).click();
    await animationFrame();
    await animationFrame();
    expect(browser.location.href).toBe("http://example.com/odoo/action-1002");
    expect(router.current.action).toBe(1002);
    expect(`.test_client_action`).toHaveText("ClientAction_Id 2");
    expect(`.o_menu_brand`).toHaveText("App2");

    await getService("action").doAction(1001, { clearBreadcrumbs: true });
    await animationFrame();
    expect(browser.location.href).toBe("http://example.com/odoo/action-1001");
    expect(router.current.action).toBe(1001);
    expect(`.test_client_action`).toHaveText("ClientAction_Id 1");
    expect(`.o_menu_brand`).toHaveText("App2");
});

test(`actions can push state`, async () => {
    class ClientActionPushes extends Component {
        static template = xml`
            <div class="test_client_action" t-on-click="_actionPushState">
                ClientAction_<t t-esc="props.params and props.params.description"/>
            </div>
        `;
        static props = ["*"];

        _actionPushState() {
            router.pushState({ arbitrary: "actionPushed" });
        }
    }
    actionRegistry.add("client_action_pushes", ClientActionPushes);

    await mountWithCleanup(WebClient);
    expect(browser.location.href).toBe("http://example.com/odoo");
    expect(browser.history.length).toBe(1);
    expect(router.current).toEqual({});

    await getService("action").doAction("client_action_pushes");
    await animationFrame();
    expect(browser.location.href).toBe("http://example.com/odoo/client_action_pushes");
    expect(browser.history.length).toBe(2);
    expect(router.current.action).toBe("client_action_pushes");
    expect(router.current.menu_id).toBe(undefined);

    await contains(`.test_client_action`).click();
    await animationFrame();
    expect(browser.location.href).toBe(
        "http://example.com/odoo/client_action_pushes?arbitrary=actionPushed"
    );
    expect(browser.history.length).toBe(3);
    expect(router.current.action).toBe("client_action_pushes");
    expect(router.current.arbitrary).toBe("actionPushed");
});

test(`actions override previous state`, async () => {
    class ClientActionPushes extends Component {
        static template = xml`
            <div class="test_client_action" t-on-click="_actionPushState">
                ClientAction_<t t-esc="props.params and props.params.description"/>
            </div>
        `;
        static props = ["*"];

        _actionPushState() {
            router.pushState({ arbitrary: "actionPushed" });
        }
    }
    actionRegistry.add("client_action_pushes", ClientActionPushes);

    await mountWithCleanup(WebClient);
    expect(browser.location.href).toBe("http://example.com/odoo");
    expect(browser.history.length).toBe(1);
    expect(router.current).toEqual({});

    await getService("action").doAction("client_action_pushes");
    await animationFrame(); // wait for pushState because it's unrealistic to click before it
    await contains(`.test_client_action`).click();
    await animationFrame();
    expect(browser.location.href).toBe(
        "http://example.com/odoo/client_action_pushes?arbitrary=actionPushed"
    );
    expect(browser.history.length).toBe(3); // Two history entries
    expect(router.current.action).toBe("client_action_pushes");
    expect(router.current.arbitrary).toBe("actionPushed");

    await getService("action").doAction(1001);
    await animationFrame();
    expect(browser.location.href).toBe("http://example.com/odoo/action-1001", {
        message: "client_action_pushes removed from url because action 1001 is in target main",
    });
    expect(browser.history.length).toBe(4);
    expect(router.current.action).toBe(1001);
    expect(router.current.arbitrary).toBe(undefined);
});

test(`actions override previous state from menu click`, async () => {
    class ClientActionPushes extends Component {
        static template = xml`
            <div class="test_client_action" t-on-click="_actionPushState">
                ClientAction_<t t-esc="props.params and props.params.description"/>
            </div>
        `;
        static props = ["*"];

        _actionPushState() {
            router.pushState({ arbitrary: "actionPushed" });
        }
    }
    actionRegistry.add("client_action_pushes", ClientActionPushes);

    await mountWithCleanup(WebClient);
    expect(browser.location.href).toBe("http://example.com/odoo");
    expect(router.current).toEqual({});

    await getService("action").doAction("client_action_pushes");
    await contains(`.test_client_action`).click();
    await contains(`.o_navbar_apps_menu button`).click();
    await contains(`.o-dropdown-item:eq(2)`).click();
    await animationFrame();
    await animationFrame();
    expect(browser.location.href).toBe("http://example.com/odoo/action-1002");
    expect(router.current.action).toBe(1002);
});

test(`action in target new do not push state`, async () => {
    defineActions([
        {
            id: 2001,
            tag: "__test__client__action__",
            target: "new",
            type: "ir.actions.client",
            params: { description: "Id 1" },
        },
    ]);

    patchWithCleanup(browser.history, {
        pushState() {
            throw new Error("should not push state");
        },
    });

    await mountWithCleanup(WebClient);
    expect(browser.location.href).toBe("http://example.com/odoo");
    expect(browser.history.length).toBe(1);

    await getService("action").doAction(2001);
    expect(`.modal .test_client_action`).toHaveCount(1);

    await animationFrame();
    expect(browser.location.href).toBe("http://example.com/odoo", {
        message: "url did not change",
    });
    expect(browser.history.length).toBe(1, { message: "did not create a history entry" });
    expect(router.current).toEqual({});
});

test(`properly push state`, async () => {
    await mountWithCleanup(WebClient);
    expect(browser.location.href).toBe("http://example.com/odoo");
    expect(browser.history.length).toBe(1);

    await getService("action").doAction(4);
    await animationFrame();
    expect(browser.location.href).toBe("http://example.com/odoo/action-4");
    expect(browser.history.length).toBe(2);
    expect(router.current).toEqual({
        action: 4,
        actionStack: [
            {
                action: 4,
                displayName: "Partners Action 4",
                view_type: "kanban",
            },
        ],
    });

    await getService("action").doAction(8);
    await animationFrame();
    expect(browser.location.href).toBe("http://example.com/odoo/action-4/action-8");
    expect(browser.history.length).toBe(3);
    expect(router.current).toEqual({
        action: 8,
        actionStack: [
            {
                action: 4,
                displayName: "Partners Action 4",
                view_type: "kanban",
            },
            {
                action: 8,
                displayName: "Favorite Ponies",
                view_type: "list",
            },
        ],
    });

    await contains(`tr .o_data_cell:first`).click();
    await animationFrame();
    expect(browser.location.href).toBe("http://example.com/odoo/action-4/action-8/4");
    expect(browser.history.length).toBe(4);
    expect(router.current).toEqual({
        action: 8,
        actionStack: [
            {
                action: 4,
                displayName: "Partners Action 4",
                view_type: "kanban",
            },
            {
                action: 8,
                displayName: "Favorite Ponies",
                view_type: "list",
            },
            {
                action: 8,
                displayName: "Twilight Sparkle",
                resId: 4,
                view_type: "form",
            },
        ],
        resId: 4,
    });
});

test(`push state after action is loaded, not before`, async () => {
    const def = new Deferred();
    onRpc("get_views", () => def);

    await mountWithCleanup(WebClient);
    expect(browser.location.href).toBe("http://example.com/odoo");
    expect(browser.history.length).toBe(1);

    getService("action").doAction(4);
    await animationFrame();
    await animationFrame();

    expect(browser.location.href).toBe("http://example.com/odoo");
    expect(browser.history.length).toBe(1);
    expect(router.current).toEqual({});

    def.resolve();
    await animationFrame();
    await animationFrame();
    expect(browser.location.href).toBe("http://example.com/odoo/action-4");
    expect(browser.history.length).toBe(2);
    expect(router.current).toEqual({
        action: 4,
        actionStack: [
            {
                action: 4,
                displayName: "Partners Action 4",
                view_type: "kanban",
            },
        ],
    });
});

test(`do not push state when action fails`, async () => {
    onRpc("read", () => Promise.reject());

    await mountWithCleanup(WebClient);
    expect(browser.location.href).toBe("http://example.com/odoo");
    expect(browser.history.length).toBe(1);

    await getService("action").doAction(8);
    await animationFrame();
    expect(browser.location.href).toBe("http://example.com/odoo/action-8");
    expect(browser.history.length).toBe(2);
    expect(router.current).toEqual({
        action: 8,
        actionStack: [
            {
                action: 8,
                displayName: "Favorite Ponies",
                view_type: "list",
            },
        ],
    });

    await contains(`tr.o_data_row:first`).click();
    // we make sure here that the list view is still in the dom
    expect(`.o_list_view`).toHaveCount(1, {
        message: "there should still be a list view in dom",
    });

    await animationFrame(); // wait for possible debounced pushState
    expect(browser.location.href).toBe("http://example.com/odoo/action-8");
    expect(browser.history.length).toBe(2);
    expect(router.current).toEqual({
        action: 8,
        actionStack: [
            {
                action: 8,
                displayName: "Favorite Ponies",
                view_type: "list",
            },
        ],
    });
});

test(`view_type is in url when not the default one`, async () => {
    await mountWithCleanup(WebClient);
    expect(browser.location.href).toBe("http://example.com/odoo");
    expect(browser.history.length).toBe(1);

    await getService("action").doAction(3);
    await animationFrame();
    expect(browser.location.href).toBe("http://example.com/odoo/action-3");
    expect(browser.history.length).toBe(2);
    expect(router.current).toEqual({
        action: 3,
        actionStack: [
            {
                action: 3,
                displayName: "Partners",
                view_type: "list",
            },
        ],
    });
    expect(`.breadcrumb`).toHaveCount(0);

    await getService("action").doAction(3, { viewType: "kanban" });
    await animationFrame();
    expect(browser.location.href).toBe("http://example.com/odoo/action-3?view_type=kanban");
    expect(browser.history.length).toBe(3, { message: "created a history entry" });
    expect(`.breadcrumb`).toHaveCount(1, {
        message: "created a breadcrumb entry",
    });
    expect(router.current).toEqual({
        action: 3,
        view_type: "kanban", // view_type is on the state when it's not the default one
        actionStack: [
            {
                action: 3,
                displayName: "Partners",
                view_type: "list",
            },
            {
                action: 3,
                displayName: "Partners",
                view_type: "kanban",
            },
        ],
    });
});

test(`switchView pushes the stat but doesn't add to the breadcrumbs`, async () => {
    await mountWithCleanup(WebClient);
    expect(browser.location.href).toBe("http://example.com/odoo");
    expect(browser.history.length).toBe(1);

    await getService("action").doAction(3);
    await animationFrame();
    expect(browser.location.href).toBe("http://example.com/odoo/action-3");
    expect(browser.history.length).toBe(2);
    expect(router.current).toEqual({
        action: 3,
        actionStack: [
            {
                action: 3,
                displayName: "Partners",
                view_type: "list",
            },
        ],
    });
    expect(`.breadcrumb`).toHaveCount(0);

    await getService("action").switchView("kanban");
    await animationFrame();
    expect(browser.location.href).toBe("http://example.com/odoo/action-3?view_type=kanban");
    expect(browser.history.length).toBe(3, { message: "created a history entry" });
    expect(`.breadcrumb`).toHaveCount(0, { message: "didn't create a breadcrumb entry" });
    expect(router.current).toEqual({
        action: 3,
        view_type: "kanban", // view_type is on the state when it's not the default one
        actionStack: [
            {
                action: 3,
                displayName: "Partners",
                view_type: "kanban",
            },
        ],
    });
});

test(`properly push globalState`, async () => {
    await mountWithCleanup(WebClient);
    expect(browser.location.href).toBe("http://example.com/odoo");
    expect(browser.history.length).toBe(1);

    await getService("action").doAction(4);
    await animationFrame();
    expect(browser.location.href).toBe("http://example.com/odoo/action-4");
    expect(browser.history.length).toBe(2);
    expect(router.current).toEqual({
        action: 4,
        actionStack: [
            {
                action: 4,
                displayName: "Partners Action 4",
                view_type: "kanban",
            },
        ],
    });

    // add element on the search Model
    await editSearch("blip");
    await validateSearch();
    expect(queryAllTexts(".o_facet_value")).toEqual(["blip"]);

    //open record
    await contains(".o_kanban_record").click();

    // Add the globalState on the state before leaving the kanban
    expect(router.current).toEqual({
        action: 4,
        actionStack: [
            {
                action: 4,
                displayName: "Partners Action 4",
                view_type: "kanban",
            },
        ],
        globalState: {
            searchModel: `{"nextGroupId":2,"nextGroupNumber":1,"nextId":2,"query":[{"searchItemId":1,"autocompleteValue":{"label":"blip","operator":"ilike","value":"blip"}}],"searchItems":{"1":{"type":"field","fieldName":"foo","fieldType":"char","description":"Foo","groupId":1,"id":1}},"searchPanelInfo":{"className":"","viewTypes":["kanban","list"],"loaded":false,"shouldReload":true},"sections":[]}`,
        },
    });

    // pushState is defered
    await animationFrame();
    expect(".o_form_view").toHaveCount(1);
    expect(browser.location.href).toBe("http://example.com/odoo/action-4/2");
    expect(router.current).toEqual({
        action: 4,
        actionStack: [
            {
                action: 4,
                displayName: "Partners Action 4",
                view_type: "kanban",
            },
            {
                action: 4,
                displayName: "Second record",
                resId: 2,
                view_type: "form",
            },
        ],
        resId: 2,
    });

    // came back using the browser
    browser.history.back(); // Click on back button
    await animationFrame();

    // The search Model should be restored
    expect(queryAllTexts(".o_facet_value")).toEqual(["blip"]);
    expect(browser.location.href).toBe("http://example.com/odoo/action-4");

    // The global state is restored on the state
    expect(router.current).toEqual({
        action: 4,
        actionStack: [
            {
                action: 4,
                displayName: "Partners Action 4",
                view_type: "kanban",
            },
        ],
        globalState: {
            searchModel: `{"nextGroupId":2,"nextGroupNumber":1,"nextId":2,"query":[{"searchItemId":1,"autocompleteValue":{"label":"blip","operator":"ilike","value":"blip"}}],"searchItems":{"1":{"type":"field","fieldName":"foo","fieldType":"char","description":"Foo","groupId":1,"id":1}},"searchPanelInfo":{"className":"","viewTypes":["kanban","list"],"loaded":false,"shouldReload":true},"sections":[]}`,
        },
    });
});

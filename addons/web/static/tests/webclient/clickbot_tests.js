/** @odoo-module **/

import { registry } from "@web/core/registry";
import { createWebClient } from "./helpers";
import { makeDeferred, patchWithCleanup } from "@web/../tests/helpers/utils";
import { browser } from "@web/core/browser/browser";
import { ListRenderer } from "@web/views/list/list_renderer";
import { onWillStart, onWillUpdateProps } from "@odoo/owl";

let serverData;
let clickEverywhereDef;

QUnit.module("clickbot", (hooks) => {
    hooks.beforeEach(async function () {
        serverData = {
            models: {
                foo: {
                    fields: {
                        foo: { string: "Foo", type: "char" },
                        bar: { string: "Bar", type: "boolean" },
                        date: { string: "Some Date", type: "date" },
                    },
                    records: [
                        {
                            id: 1,
                            bar: true,
                            foo: "yop",
                            date: "2017-01-25",
                        },
                        {
                            id: 2,
                            bar: true,
                            foo: "blip",
                        },
                        {
                            id: 3,
                            bar: true,
                            foo: "gnap",
                        },
                        {
                            id: 4,
                            bar: false,
                            foo: "blip",
                        },
                    ],
                },
            },
            views: {
                "foo,false,search": `
                    <search>
                        <filter string="Not Bar" name="not bar" domain="[['bar','=',False]]"/>
                        <filter string="Date" name="date" date="date"/>
                    </search>`,
                "foo,false,list": `
                    <list>
                        <field name="foo" />
                    </list>`,
                "foo,false,kanban": `
                    <kanban class="o_kanban_test">
                        <templates><t t-name="kanban-box">
                            <div>
                                <field name="foo"/>
                            </div>
                        </t></templates>
                    </kanban>`,
            },
            actions: {
                1001: {
                    id: 1001,
                    name: "App1",
                    res_model: "foo",
                    type: "ir.actions.act_window",
                    views: [
                        [false, "list"],
                        [false, "kanban"],
                    ],
                    xml_id: "app1",
                },
                1002: {
                    id: 1002,
                    name: "App2 Menu 1",
                    res_model: "foo",
                    type: "ir.actions.act_window",
                    views: [[false, "kanban"]],
                    xml_id: "app2_menu1",
                },
                1022: {
                    id: 1022,
                    name: "App2 Menu 2",
                    res_model: "foo",
                    type: "ir.actions.act_window",
                    views: [[false, "list"]],
                    xml_id: "app2_menu2",
                },
            },
            menus: {
                root: { id: "root", children: [1, 2], name: "root", appID: "root" },
                1: { id: 1, children: [], name: "App1", appID: 1, actionID: 1001, xmlid: "app1" },
                2: {
                    id: 2,
                    children: [3, 4],
                    name: "App2",
                    appID: 2,
                    actionID: 1002,
                    xmlid: "app2",
                },
                3: {
                    id: 3,
                    children: [],
                    name: "menu 1",
                    appID: 2,
                    actionID: 1002,
                    xmlid: "app2_menu1",
                },
                4: {
                    id: 4,
                    children: [],
                    name: "menu 2",
                    appID: 2,
                    actionID: 1022,
                    xmlid: "app2_menu1",
                },
            },
        };
        registry.category("command_categories").add("view_switcher", {});
    });
    QUnit.skip("clickbot clickeverywhere test", async (assert) => {
        patchWithCleanup(browser, {
            console: {
                log: (msg) => {
                    assert.step(msg);
                    if (msg === "test successful") {
                        clickEverywhereDef.resolve();
                    }
                },
                error: (msg) => {
                    assert.step(msg);
                    clickEverywhereDef.resolve();
                },
            },
        });
        await createWebClient({ serverData });
        clickEverywhereDef = makeDeferred();
        window.clickEverywhere();
        await clickEverywhereDef;
        assert.verifySteps([
            "Clicking on: apps menu toggle button",
            "Testing app menu: app1",
            "Testing menu App1 app1",
            'Clicking on: menu item "App1"',
            "Clicking on: Control Panel menu",
            "Testing 2 filters",
            'Clicking on: filter "Not Bar"',
            'Clicking on: filter "Date"',
            'Clicking on: filter option "October"',
            "Testing view switch: kanban",
            "Clicking on: kanban view switcher",
            "Clicking on: Control Panel menu",
            "Testing 2 filters",
            'Clicking on: filter "Not Bar"',
            'Clicking on: filter "Date"',
            'Clicking on: filter option "October"',
            "Clicking on: apps menu toggle button",
            "Testing app menu: app2",
            "Testing menu App2 app2",
            'Clicking on: menu item "App2"',
            "Clicking on: Control Panel menu",
            "Testing 2 filters",
            'Clicking on: filter "Not Bar"',
            'Clicking on: filter "Date"',
            'Clicking on: filter option "October"',
            "Testing menu menu 1 app2_menu1",
            'Clicking on: menu item "menu 1"',
            "Clicking on: Control Panel menu",
            "Testing 2 filters",
            'Clicking on: filter "Not Bar"',
            'Clicking on: filter "Date"',
            'Clicking on: filter option "October"',
            "Testing menu menu 2 app2_menu1",
            'Clicking on: menu item "menu 2"',
            "Clicking on: Control Panel menu",
            "Testing 2 filters",
            'Clicking on: filter "Not Bar"',
            'Clicking on: filter "Date"',
            'Clicking on: filter option "October"',
            "Clicking on: apps menu toggle button",
            "Successfully tested 2 apps",
            "Successfully tested 2 menus",
            "Successfully tested 0 modals",
            "Successfully tested 10 filters",
            "test successful",
        ]);
    });

    QUnit.test("clickbot test waiting rpc after clicking filter", async (assert) => {
        let clickBotStarted = false;
        serverData.actions = {
            1001: {
                id: 1,
                name: "App1",
                res_model: "foo",
                type: "ir.actions.act_window",
                views: [[false, "list"]],
            },
        };
        serverData.menus = {
            root: { id: "root", children: [1], name: "root", appID: "root" },
            1: { id: 1, children: [], name: "App1", appID: 1, actionID: 1001, xmlid: "app1" },
        };
        patchWithCleanup(browser, {
            console: {
                log: (msg) => {
                    if (msg === "test successful") {
                        assert.step(msg);
                        clickEverywhereDef.resolve();
                    }
                },
                error: () => {
                    clickEverywhereDef.resolve();
                },
            },
        });
        await createWebClient({
            serverData,
            mockRPC: async function (route, args) {
                if (args.method === "web_search_read") {
                    if (clickBotStarted) {
                        assert.step("web_search_read called");
                        await new Promise((r) => setTimeout(r, 1000));
                        assert.step("response");
                    }
                }
            },
        });
        clickBotStarted = true;

        clickEverywhereDef = makeDeferred();
        window.clickEverywhere();
        await clickEverywhereDef;
        assert.verifySteps([
            "web_search_read called", // click on the App
            "response",
            "web_search_read called", // click on the Filter
            "response",
            "web_search_read called", // click on the Second Filter
            "response",
            "test successful",
        ]);
    });

    QUnit.test("clickbot test waiting render after clicking filter", async (assert) => {
        let clickBotStarted = false;
        serverData.actions = {
            1001: {
                id: 1,
                name: "App1",
                res_model: "foo",
                type: "ir.actions.act_window",
                views: [[false, "list"]],
            },
        };
        serverData.menus = {
            root: { id: "root", children: [1], name: "root", appID: "root" },
            1: { id: 1, children: [], name: "App1", appID: 1, actionID: 1001, xmlid: "app1" },
        };
        patchWithCleanup(browser, {
            console: {
                log: (msg) => {
                    if (msg === "test successful") {
                        assert.step(msg);
                        clickEverywhereDef.resolve();
                    }
                },
                error: () => {
                    clickEverywhereDef.resolve();
                },
            },
        });
        patchWithCleanup(ListRenderer.prototype, {
            setup() {
                super.setup(...arguments);
                onWillStart(async () => {
                    if (clickBotStarted) {
                        assert.step("onWillStart called");
                        await new Promise((r) => setTimeout(r, 1000));
                        assert.step("response");
                    }
                });
                onWillUpdateProps(async () => {
                    if (clickBotStarted) {
                        assert.step("onWillUpdateProps called");
                        await new Promise((r) => setTimeout(r, 1000));
                        assert.step("response");
                    }
                });
            },
        });
        await createWebClient({ serverData });
        clickBotStarted = true;

        clickEverywhereDef = makeDeferred();
        window.clickEverywhere();
        await clickEverywhereDef;
        assert.verifySteps([
            "onWillStart called", // click on APP
            "response",
            "onWillUpdateProps called", // click on filter
            "response",
            "onWillUpdateProps called", // click on second filter
            "response",
            "test successful",
        ]);
    });

    QUnit.skip("clickbot clickeverywhere menu modal", async (assert) => {
        serverData.views["foo,false,form"] = `
            <form>
                <field name="foo"/>
            </form>
        `;
        serverData.actions["1099"] = {
            id: 1099,
            name: "Modal",
            res_model: "foo",
            type: "ir.actions.act_window",
            views: [[false, "form"]],
            view_mode: "form",
            target: "new",
        };
        serverData.menus = {
            root: { id: "root", children: [1, 2], name: "root", appID: "root" },
            1: { id: 1, children: [], name: "App1", appID: 1, actionID: 1001, xmlid: "app1" },
            2: {
                id: 2,
                children: [],
                name: "App Modal",
                appID: 2,
                actionID: 1099,
                xmlid: "test.modal",
            },
        };
        patchWithCleanup(browser, {
            console: {
                log: (msg) => {
                    assert.step(msg);
                    if (msg === "test successful") {
                        clickEverywhereDef.resolve();
                    }
                },
                error: (msg) => {
                    assert.step(msg);
                    clickEverywhereDef.resolve();
                },
            },
        });
        await createWebClient({ serverData });
        clickEverywhereDef = makeDeferred();
        window.clickEverywhere();
        await clickEverywhereDef;
        assert.verifySteps([
            "Clicking on: apps menu toggle button",
            "Testing app menu: app1",
            "Testing menu App1 app1",
            'Clicking on: menu item "App1"',
            "Clicking on: Control Panel menu",
            "Testing 2 filters",
            'Clicking on: filter "Not Bar"',
            'Clicking on: filter "Date"',
            'Clicking on: filter option "October"',
            "Testing view switch: kanban",
            "Clicking on: kanban view switcher",
            "Clicking on: Control Panel menu",
            "Testing 2 filters",
            'Clicking on: filter "Not Bar"',
            'Clicking on: filter "Date"',
            'Clicking on: filter option "October"',
            "Clicking on: apps menu toggle button",
            "Testing app menu: test.modal",
            "Testing menu App Modal test.modal",
            'Clicking on: menu item "App Modal"',
            "Modal detected: App Modal test.modal",
            "Clicking on: modal close button",
            "Clicking on: apps menu toggle button",
            "Successfully tested 2 apps",
            "Successfully tested 0 menus",
            "Successfully tested 1 modals",
            "Successfully tested 4 filters",
            "test successful",
        ]);
    });
});

/** @odoo-module **/

import { registry } from "@web/core/registry";
import { createWebClient } from "./helpers";
import {
    getFixture,
    makeDeferred,
    nextTick,
    patchDate,
    patchWithCleanup,
} from "@web/../tests/helpers/utils";
import { browser } from "@web/core/browser/browser";
import { ListRenderer } from "@web/views/list/list_renderer";
import { onWillStart, onWillUpdateProps } from "@odoo/owl";
import { errorService } from "@web/core/errors/error_service";
import { makeServerError } from "@web/../tests/helpers/mock_server";

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
                    xmlid: "app2_menu2",
                },
            },
        };
        registry.category("command_categories").add("view_switcher", {});
    });
    QUnit.test("clickbot clickeverywhere test", async (assert) => {
        patchDate(2017, 9, 8, 15, 35, 11); // October 8 2017, 15:35:11
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
            "Testing 2 filters",
            'Clicking on: filter "Not Bar"',
            'Clicking on: filter "Date"',
            'Clicking on: filter option "October"',
            "Testing view switch: kanban",
            "Clicking on: kanban view switcher",
            "Testing 2 filters",
            'Clicking on: filter "Not Bar"',
            'Clicking on: filter "Date"',
            'Clicking on: filter option "October"',
            "Clicking on: apps menu toggle button",
            "Testing app menu: app2",
            "Testing menu App2 app2",
            'Clicking on: menu item "App2"',
            "Testing 2 filters",
            'Clicking on: filter "Not Bar"',
            'Clicking on: filter "Date"',
            'Clicking on: filter option "October"',
            "Testing menu menu 1 app2_menu1",
            'Clicking on: menu item "menu 1"',
            "Testing 2 filters",
            'Clicking on: filter "Not Bar"',
            'Clicking on: filter "Date"',
            'Clicking on: filter option "October"',
            "Testing menu menu 2 app2_menu2",
            'Clicking on: menu item "menu 2"',
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

    QUnit.test("clickbot clickeverywhere test (with dropdown menu)", async (assert) => {
        serverData.menus.root.children = [2];
        serverData.menus[2].children = [5];
        serverData.menus[5] = {
            id: 5,
            children: [3, 4],
            name: "a dropdown",
            appID: 2,
            xmlid: "app2_dropdown_menu",
        };

        patchDate(2017, 9, 8, 15, 35, 11); // October 8 2017, 15:35:11
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
        await nextTick();
        assert.containsOnce(
            getFixture(),
            ".o_menu_sections .o-dropdown .dropdown-toggle:contains(a dropdown)"
        );
        clickEverywhereDef = makeDeferred();
        window.clickEverywhere();
        await clickEverywhereDef;
        assert.verifySteps([
            "Clicking on: apps menu toggle button",
            "Testing app menu: app2",
            "Testing menu App2 app2",
            'Clicking on: menu item "App2"',
            "Testing 2 filters",
            'Clicking on: filter "Not Bar"',
            'Clicking on: filter "Date"',
            'Clicking on: filter option "October"',
            "Clicking on: menu toggler",
            "Testing menu menu 1 app2_menu1",
            'Clicking on: menu item "menu 1"',
            "Testing 2 filters",
            'Clicking on: filter "Not Bar"',
            'Clicking on: filter "Date"',
            'Clicking on: filter option "October"',
            "Clicking on: menu toggler",
            "Testing menu menu 2 app2_menu2",
            'Clicking on: menu item "menu 2"',
            "Testing 2 filters",
            'Clicking on: filter "Not Bar"',
            'Clicking on: filter "Date"',
            'Clicking on: filter option "October"',
            "Clicking on: apps menu toggle button",
            "Successfully tested 1 apps",
            "Successfully tested 2 menus",
            "Successfully tested 0 modals",
            "Successfully tested 6 filters",
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

    QUnit.test("clickbot show rpc error when an error dialog is detected", async (assert) => {
        patchDate(2024, 3, 10, 0, 0, 0);
        let clickBotStarted = false;
        registry.category("services").add("error", errorService);
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
                error: (msg) => {
                    assert.step(msg.toString());
                    clickEverywhereDef.resolve();
                },
            },
        });
        let id = 1;
        await createWebClient({
            serverData,
            mockRPC: async function (route, args) {
                if (args.method === "web_search_read") {
                    if (clickBotStarted) {
                        if (id === 3) {
                            // click on the Second Filter
                            throw makeServerError({
                                message:
                                    "This is a server Error, it should be displayed in an error dialog",
                            });
                        }
                        id++;
                    }
                }
            },
        });
        clickBotStarted = true;

        clickEverywhereDef = makeDeferred();
        window.clickEverywhere();
        await clickEverywhereDef;
        await nextTick();
        assert.verifySteps([
            'A RPC in error was detected, maybe it\'s related to the error dialog : {"data":{"id":6,"jsonrpc":"2.0","method":"call","params":{"model":"foo","method":"web_search_read","args":[],"kwargs":{"specification":{"foo":{}},"offset":0,"order":"","limit":80,"context":{"lang":"en","uid":7,"tz":"taht","bin_size":true},"count_limit":10001,"domain":["|",["bar","=",false],"&",["date",">=","2024-04-01"],["date","<=","2024-04-30"]]}}},"settings":{"silent":false},"error":{"name":"RPC_ERROR","type":"server","code":200,"data":{"name":"odoo.exceptions.UserError","debug":"traceback","arguments":[],"context":{}},"exceptionName":"odoo.exceptions.UserError","message":"This is a server Error, it should be displayed in an error dialog","errorEvent":{"isTrusted":true}}}',
            "Error while testing App1 app1",
            'Error: Error dialog detected<header class="modal-header"><h4 class="modal-title text-break">Odoo Error</h4><button type="button" class="btn-close" aria-label="Close" tabindex="-1"></button></header><footer class="modal-footer justify-content-around justify-content-md-start flex-wrap gap-1 w-100" style="order:2"><button class="btn btn-primary o-default-button">Close</button><button class="btn btn-secondary"><i class="fa fa-clipboard mr8"></i>Copy error to clipboard</button></footer><main class="modal-body"><div role="alert"><p class="text-prewrap"><p><b>An error occurred</b></p><p>Please use the copy button to report the error to your support service.</p></p><button class="btn btn-link">See details</button></div></main>',
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

    QUnit.test("clickbot clickeverywhere menu modal", async (assert) => {
        patchDate(2017, 9, 8, 15, 35, 11); // October 8 2017, 15:35:11
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
            "Testing 2 filters",
            'Clicking on: filter "Not Bar"',
            'Clicking on: filter "Date"',
            'Clicking on: filter option "October"',
            "Testing view switch: kanban",
            "Clicking on: kanban view switcher",
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

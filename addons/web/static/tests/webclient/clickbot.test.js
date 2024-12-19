import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { animationFrame, Deferred, mockDate, runAllTimers, tick } from "@odoo/hoot-mock";
import {
    defineActions,
    defineMenus,
    defineModels,
    fields,
    makeMockServer,
    makeServerError,
    models,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

import { onWillStart, onWillUpdateProps } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { ListRenderer } from "@web/views/list/list_renderer";
import { WebClient } from "@web/webclient/webclient";
import { SUCCESS_SIGNAL } from "@web/webclient/clickbot/clickbot";

class Foo extends models.Model {
    foo = fields.Char();
    bar = fields.Boolean();
    date = fields.Date();

    _records = [
        { id: 1, bar: true, foo: "yop", date: "2017-01-25" },
        { id: 2, bar: true, foo: "blip" },
        { id: 3, bar: true, foo: "gnap" },
        { id: 4, bar: false, foo: "blip" },
    ];

    _views = {
        search: /* xml */ `
            <search>
                <filter string="Not Bar" name="not bar" domain="[['bar','=',False]]"/>
                <filter string="Date" name="date" date="date"/>
            </search>
        `,
        list: /* xml */ `
            <list>
                <field name="foo" />
            </list>
        `,
        kanban: /* xml */ `
            <kanban class="o_kanban_test">
                <templates><t t-name="card">
                    <field name="foo"/>
                </t></templates>
            </kanban>
        `,
    };
}

describe.current.tags("desktop");

defineModels([Foo]);

beforeEach(() => {
    defineActions([
        {
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
        {
            id: 1002,
            name: "App2 Menu 1",
            res_model: "foo",
            type: "ir.actions.act_window",
            views: [[false, "kanban"]],
            xml_id: "app2_menu1",
        },
        {
            id: 1022,
            name: "App2 Menu 2",
            res_model: "foo",
            type: "ir.actions.act_window",
            views: [[false, "list"]],
            xml_id: "app2_menu2",
        },
    ]);
    defineMenus([
        {
            id: "root",
            children: [
                { id: 1, children: [], name: "App1", appID: 1, actionID: 1001, xmlid: "app1" },
                {
                    id: 2,
                    children: [
                        {
                            id: 3,
                            children: [],
                            name: "menu 1",
                            appID: 2,
                            actionID: 1002,
                            xmlid: "app2_menu1",
                        },
                        {
                            id: 4,
                            children: [],
                            name: "menu 2",
                            appID: 2,
                            actionID: 1022,
                            xmlid: "app2_menu2",
                        },
                    ],
                    name: "App2",
                    appID: 2,
                    actionID: 1002,
                    xmlid: "app2",
                },
            ],
            name: "root",
            appID: "root",
        },
    ]);
});

test("clickbot clickeverywhere test", async () => {
    onRpc("has_group", () => true);
    mockDate("2017-10-08T15:35:11.000");
    const clickEverywhereDef = new Deferred();
    patchWithCleanup(browser, {
        console: {
            log: (msg) => {
                expect.step(msg);
                if (msg === SUCCESS_SIGNAL) {
                    clickEverywhereDef.resolve();
                }
            },
            error: (msg) => {
                expect.step(msg);
                clickEverywhereDef.resolve();
            },
        },
    });
    const webClient = await mountWithCleanup(WebClient);
    patchWithCleanup(odoo, {
        __WOWL_DEBUG__: { root: webClient },
    });
    window.clickEverywhere();
    await clickEverywhereDef;
    expect.verifySteps([
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
        "Successfully tested 2 apps",
        "Successfully tested 2 menus",
        "Successfully tested 0 modals",
        "Successfully tested 10 filters",
        SUCCESS_SIGNAL,
    ]);
});

test("clickbot clickeverywhere test (with dropdown menu)", async () => {
    onRpc("has_group", () => true);
    mockDate("2017-10-08T15:35:11.000");
    const clickEverywhereDef = new Deferred();
    patchWithCleanup(browser, {
        console: {
            log: (msg) => {
                expect.step(msg);
                if (msg === SUCCESS_SIGNAL) {
                    clickEverywhereDef.resolve();
                }
            },
            error: (msg) => {
                expect.step(msg);
                clickEverywhereDef.resolve();
            },
        },
    });
    const server = await makeMockServer();
    // Replace all default menus and setting new one
    server.menus = [
        {
            id: "root",
            children: [
                {
                    id: 2,
                    children: [
                        {
                            id: 5,
                            children: [
                                {
                                    id: 3,
                                    children: [],
                                    name: "menu 1",
                                    appID: 2,
                                    actionID: 1002,
                                    xmlid: "app2_menu1",
                                },
                                {
                                    id: 4,
                                    children: [],
                                    name: "menu 2",
                                    appID: 2,
                                    actionID: 1022,
                                    xmlid: "app2_menu2",
                                },
                            ],
                            name: "a dropdown",
                            appID: 2,
                            xmlid: "app2_dropdown_menu",
                        },
                    ],
                    name: "App2",
                    appID: 2,
                    actionID: 1002,
                    xmlid: "app2",
                },
            ],
            name: "root",
            appID: "root",
        },
    ];
    const webClient = await mountWithCleanup(WebClient);
    patchWithCleanup(odoo, {
        __WOWL_DEBUG__: { root: webClient },
    });
    await runAllTimers();
    await animationFrame();
    expect(".o_menu_sections .dropdown-toggle").toHaveText("a dropdown");
    window.clickEverywhere();
    await clickEverywhereDef;
    expect.verifySteps([
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
        "Successfully tested 1 apps",
        "Successfully tested 2 menus",
        "Successfully tested 0 modals",
        "Successfully tested 6 filters",
        SUCCESS_SIGNAL,
    ]);
});

test("clickbot test waiting rpc after clicking filter", async () => {
    onRpc("has_group", () => true);
    const clickEverywhereDef = new Deferred();
    let clickBotStarted = false;
    patchWithCleanup(browser, {
        console: {
            log: (msg) => {
                if (msg === SUCCESS_SIGNAL) {
                    expect.step(msg);
                    clickEverywhereDef.resolve();
                }
            },
            error: () => {
                clickEverywhereDef.resolve();
            },
        },
    });
    onRpc("web_search_read", async () => {
        if (clickBotStarted) {
            expect.step("web_search_read called");
            await tick();
            expect.step("response");
        }
    });
    const server = await makeMockServer();
    server.actions["1001"] = {
        id: 1,
        name: "App1",
        res_model: "foo",
        type: "ir.actions.act_window",
        views: [[false, "list"]],
    };
    // Replace all default menus and setting new one
    server.menus = [
        {
            id: "root",
            children: [
                { id: 1, children: [], name: "App1", appID: 1, actionID: 1001, xmlid: "app1" },
            ],
            name: "root",
            appID: "root",
        },
    ];
    const webClient = await mountWithCleanup(WebClient);
    patchWithCleanup(odoo, {
        __WOWL_DEBUG__: { root: webClient },
    });
    await runAllTimers();
    await animationFrame();
    clickBotStarted = true;
    window.clickEverywhere();
    await clickEverywhereDef;
    expect.verifySteps([
        "web_search_read called", // click on the App
        "response",
        "web_search_read called", // click on the Filter
        "response",
        "web_search_read called", // click on the Second Filter
        "response",
        SUCCESS_SIGNAL,
    ]);
});

test("clickbot show rpc error when an error dialog is detected", async () => {
    expect.errors(1);
    onRpc("has_group", () => true);
    mockDate("2024-04-10T00:00:00.000");
    const clickEverywhereDef = new Deferred();
    let clickBotStarted = false;
    let id = 1;
    patchWithCleanup(browser, {
        console: {
            log: (msg) => {
                if (msg === "test successful") {
                    expect.step(msg);
                    clickEverywhereDef.resolve();
                }
            },
            error: (msg) => {
                // Replace msg with null id as JSON-RPC ids are not reset between two tests
                expect.step(msg.toString().replace(/"id":\d+,/, `"id":null,`));
                clickEverywhereDef.resolve();
            },
        },
    });
    onRpc("web_search_read", async () => {
        if (clickBotStarted) {
            if (id === 3) {
                // click on the Second Filter
                throw makeServerError({
                    message: "This is a server Error, it should be displayed in an error dialog",
                    type: "Programming error",
                });
            }
            id++;
        }
    });
    const server = await makeMockServer();
    server.actions["1001"] = {
        id: 1,
        name: "App1",
        res_model: "foo",
        type: "ir.actions.act_window",
        views: [[false, "list"]],
    };
    // Replace all default menus and setting new one
    server.menus = [
        {
            id: "root",
            children: [
                { id: 1, children: [], name: "App1", appID: 1, actionID: 1001, xmlid: "app1" },
            ],
            name: "root",
            appID: "root",
        },
    ];
    const webClient = await mountWithCleanup(WebClient);
    patchWithCleanup(odoo, {
        __WOWL_DEBUG__: { root: webClient },
    });
    await runAllTimers();
    await animationFrame();
    clickBotStarted = true;
    window.clickEverywhere();
    await clickEverywhereDef;
    await tick();
    expect.verifySteps([
        'A RPC in error was detected, maybe it\'s related to the error dialog : {"data":{"id":null,"jsonrpc":"2.0","method":"call","params":{"model":"foo","method":"web_search_read","args":[],"kwargs":{"specification":{"foo":{}},"offset":0,"order":"","limit":80,"context":{"lang":"en","tz":"taht","uid":7,"allowed_company_ids":[1],"bin_size":true},"count_limit":10001,"domain":["|",["bar","=",false],"&",["date",">=","2024-04-01"],["date","<=","2024-04-30"]]}}},"settings":{"silent":false},"error":{"name":"RPC_ERROR","type":"server","code":0,"data":{"name":"odoo.exceptions.Programming error","debug":"traceback","arguments":[],"context":{}},"exceptionName":"odoo.exceptions.Programming error","subType":"server","message":"This is a server Error, it should be displayed in an error dialog","id":51,"model":"foo","errorEvent":{"isTrusted":true}}}',
        "Error while testing App1 app1",
        'Error: Error dialog detected<header class="modal-header"><h4 class="modal-title text-break flex-grow-1">Oops!</h4><button type="button" class="btn-close" aria-label="Close" tabindex="-1"></button></header><main class="modal-body"><div role="alert"><p class="text-prewrap"> Something went wrong... If you really are stuck, share the report with your friendly support service </p><button class="btn btn-link p-0">See technical details</button></div></main><footer class="modal-footer justify-content-around justify-content-md-start flex-wrap gap-1 w-100"><button class="btn btn-primary o-default-button">Close</button></footer>',
    ]);
});

test("clickbot test waiting render after clicking filter", async () => {
    onRpc("has_group", () => true);
    const clickEverywhereDef = new Deferred();
    let clickBotStarted = false;
    patchWithCleanup(browser, {
        console: {
            log: (msg) => {
                if (msg === SUCCESS_SIGNAL) {
                    expect.step(msg);
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
                    expect.step("onWillStart called");
                    await runAllTimers();
                    expect.step("response");
                }
            });
            onWillUpdateProps(async () => {
                if (clickBotStarted) {
                    expect.step("onWillUpdateProps called");
                    await runAllTimers();
                    expect.step("response");
                }
            });
        },
    });
    const server = await makeMockServer();
    server.actions["1001"] = {
        id: 1,
        name: "App1",
        res_model: "foo",
        type: "ir.actions.act_window",
        views: [[false, "list"]],
    };
    // Replace all default menus and setting new one
    server.menus = [
        {
            id: "root",
            children: [
                { id: 1, children: [], name: "App1", appID: 1, actionID: 1001, xmlid: "app1" },
            ],
            name: "root",
            appID: "root",
        },
    ];
    const webClient = await mountWithCleanup(WebClient);
    patchWithCleanup(odoo, {
        __WOWL_DEBUG__: { root: webClient },
    });
    await runAllTimers();
    await animationFrame();
    clickBotStarted = true;
    window.clickEverywhere();
    await clickEverywhereDef;
    expect.verifySteps([
        "onWillStart called", // click on APP
        "response",
        "onWillUpdateProps called", // click on filter
        "response",
        "onWillUpdateProps called", // click on second filter
        "response",
        SUCCESS_SIGNAL,
    ]);
});

test("clickbot clickeverywhere menu modal", async () => {
    onRpc("has_group", () => true);
    mockDate("2017-10-08T15:35:11.000");
    Foo._views.form = /* xml */ `
        <form>
            <field name="foo"/>
        </form>
    `;
    const clickEverywhereDef = new Deferred();
    patchWithCleanup(browser, {
        console: {
            log: (msg) => {
                expect.step(msg);
                if (msg === SUCCESS_SIGNAL) {
                    clickEverywhereDef.resolve();
                }
            },
            error: (msg) => {
                expect.step(msg);
                clickEverywhereDef.resolve();
            },
        },
    });
    const server = await makeMockServer();
    server.actions["1099"] = {
        id: 1099,
        name: "Modal",
        res_model: "foo",
        type: "ir.actions.act_window",
        views: [[false, "form"]],
        view_mode: "form",
        target: "new",
    };
    server.menus = [
        {
            id: "root",
            children: [
                { id: 1, children: [], name: "App1", appID: 1, actionID: 1001, xmlid: "app1" },
                {
                    id: 2,
                    children: [],
                    name: "App Modal",
                    appID: 2,
                    actionID: 1099,
                    xmlid: "test.modal",
                },
            ],
            name: "root",
            appID: "root",
        },
    ];
    const webClient = await mountWithCleanup(WebClient);
    patchWithCleanup(odoo, {
        __WOWL_DEBUG__: { root: webClient },
    });
    window.clickEverywhere();
    await clickEverywhereDef;
    expect.verifySteps([
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
        "Successfully tested 2 apps",
        "Successfully tested 0 menus",
        "Successfully tested 1 modals",
        "Successfully tested 4 filters",
        SUCCESS_SIGNAL,
    ]);
});

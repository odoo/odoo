import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { animationFrame, mockDate, runAllTimers, tick } from "@odoo/hoot-mock";
import {
    defineActions,
    defineMenus,
    defineModels,
    fields,
    makeServerError,
    models,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

import { onWillStart, onWillUpdateProps } from "@odoo/owl";

import { ListRenderer } from "@web/views/list/list_renderer";
import { Clickbot, FAILURE_SIGNAL, SUCCESS_SIGNAL } from "@web/webclient/clickbot/clickbot";
import { WebClient } from "@web/webclient/webclient";

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
        form: /* xml */ `
            <form>
                <field name="foo" />
            </form>
        `,
    };
}

describe.current.tags("desktop");

defineModels([Foo]);

beforeEach(() => {
    onRpc("has_group", () => true);
    defineActions([
        {
            id: 1001,
            name: "App1",
            res_model: "foo",
            views: [
                [false, "list"],
                [false, "kanban"],
                [false, "form"],
            ],
            xml_id: "app1",
        },
        {
            id: 1002,
            name: "App2 Menu 1",
            res_model: "foo",
            views: [
                [false, "kanban"],
                [false, "form"],
            ],
            xml_id: "app2_menu1",
        },
        {
            id: 1022,
            name: "App2 Menu 2",
            res_model: "foo",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            xml_id: "app2_menu2",
        },
    ]);
});

test("clickbot clickeverywhere test", async () => {
    onRpc("has_group", () => true);
    mockDate("2017-10-08T15:35:11.000");
    const { promise, resolve } = Promise.withResolvers();
    patchWithCleanup(console, {
        log: (msg) => {
            expect.step(msg);
            if (msg === SUCCESS_SIGNAL) {
                resolve();
            }
        },
        error: (msg) => {
            expect.step(msg);
            resolve();
        },
    });

    patchWithCleanup(performance, {
        now: () => 43554.39999999106,
    });

    defineMenus([
        { id: 1, name: "App1", appID: 1, actionID: 1001, xmlid: "app1" },
        {
            id: 2,
            children: [
                {
                    id: 3,
                    name: "menu 1",
                    appID: 2,
                    actionID: 1002,
                    xmlid: "app2_menu1",
                },
                {
                    id: 4,
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
    ]);
    const webClient = await mountWithCleanup(WebClient);
    new Clickbot(webClient.env, { logger: true }).start();
    await promise;
    expect.verifySteps([
        "Starting ClickEverywhere test",
        "Testing app: App1 (app1)",
        "Testing menu App1 (app1)",
        "Clicking on: list view's new button",
        "Clicking on: go back to list view (from new record form view)",
        "Clicking on: open form view from list",
        "Clicking on: go back to list view (from record view)",
        "Testing 2 filters",
        'Clicking on: filter "Not Bar"',
        'Clicking on: filter "Date"',
        'Clicking on: filter "Date (October)"',
        "Testing view switch: kanban",
        "Clicking on: kanban view switcher",
        "Clicking on: kanban view's new button",
        "Clicking on: go back to kanban view (from new record form view)",
        "Testing 2 filters",
        'Clicking on: filter "Not Bar"',
        'Clicking on: filter "Date"',
        'Clicking on: filter "Date (October)"',
        "Testing app: App2 (app2)",
        "Testing menu menu 1 (app2_menu1)",
        "Clicking on: kanban view's new button",
        "Clicking on: go back to kanban view (from new record form view)",
        "Clicking on: open form view from kanban",
        "Clicking on: go back to kanban view (from record view)",
        "Testing 2 filters",
        'Clicking on: filter "Not Bar"',
        'Clicking on: filter "Date"',
        'Clicking on: filter "Date (October)"',
        "Testing menu menu 2 (app2_menu2)",
        "Clicking on: list view's new button",
        "Clicking on: go back to list view (from new record form view)",
        "Clicking on: open form view from list",
        "Clicking on: go back to list view (from record view)",
        "Testing 2 filters",
        'Clicking on: filter "Not Bar"',
        'Clicking on: filter "Date"',
        'Clicking on: filter "Date (October)"',
        "Test took 0 seconds",
        "Tested 2 apps",
        "Tested 3 menus",
        "Tested 4 views",
        "Tested 3 form views",
        "Tested 4 new record views",
        "Tested 0 modals",
        "Tested 8 filters",
        SUCCESS_SIGNAL,
    ]);
});

test("only one app", async () => {
    onRpc("has_group", () => true);
    mockDate("2017-10-08T15:35:11.000");
    const { promise, resolve } = Promise.withResolvers();
    patchWithCleanup(localStorage, {
        removeItem(key) {
            const savedState = super.getItem(key);
            expect.step("savedState: " + savedState);
            return super.removeItem(key);
        },
    });
    patchWithCleanup(console, {
        log: (msg) => {
            expect.step(msg);
            if (msg === SUCCESS_SIGNAL) {
                resolve();
            }
        },
        error: (msg) => {
            expect.step(msg);
            resolve();
        },
    });
    patchWithCleanup(performance, {
        now: () => 43554.39999999106,
    });
    defineMenus([
        { id: 1, name: "App1", appID: 1, actionID: 1001, xmlid: "app1" },
        {
            id: 2,
            children: [
                {
                    id: 3,
                    name: "menu 1",
                    appID: 2,
                    actionID: 1002,
                    xmlid: "app2_menu1",
                },
                {
                    id: 4,
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
    ]);
    const webClient = await mountWithCleanup(WebClient);
    new Clickbot(webClient.env, { xmlId: "app1", logger: true }).start();
    await promise;
    expect.verifySteps([
        "Starting ClickEverywhere test",
        "Testing app: App1 (app1)",
        "Testing menu App1 (app1)",
        "Clicking on: list view's new button",
        "Clicking on: go back to list view (from new record form view)",
        "Clicking on: open form view from list",
        "Clicking on: go back to list view (from record view)",
        "Testing 2 filters",
        'Clicking on: filter "Not Bar"',
        'Clicking on: filter "Date"',
        'Clicking on: filter "Date (October)"',
        "Testing view switch: kanban",
        "Clicking on: kanban view switcher",
        "Clicking on: kanban view's new button",
        "Clicking on: go back to kanban view (from new record form view)",
        "Testing 2 filters",
        'Clicking on: filter "Not Bar"',
        'Clicking on: filter "Date"',
        'Clicking on: filter "Date (October)"',
        "Test took 0 seconds",
        "Tested 1 apps",
        "Tested 1 menus",
        "Tested 2 views",
        "Tested 1 form views",
        "Tested 2 new record views",
        "Tested 0 modals",
        "Tested 4 filters",
        SUCCESS_SIGNAL,
        'savedState: {"logger":true,"studioCount":0,"testedApps":["app1"],"testedMenus":["app1"],"testedFilters":4,"testedModals":0,"testedViews":2,"testedFormsViews":1,"testedNewRecord":2,"appIndex":0,"menuIndex":0,"errorMenuCount":0,"startTime":43554.39999999106,"xmlId":"app1"}',
    ]);
});

test("clickbot clickeverywhere test (with dropdown menu)", async () => {
    onRpc("has_group", () => true);
    mockDate("2017-10-08T15:35:11.000");
    const { promise, resolve } = Promise.withResolvers();
    patchWithCleanup(console, {
        log: (msg) => {
            expect.step(msg);
            if (msg === SUCCESS_SIGNAL) {
                resolve();
            }
        },
        error: (msg) => {
            expect.step(msg);
            resolve();
        },
    });
    patchWithCleanup(performance, {
        now: () => 43554.39999999106,
    });
    defineMenus(
        [
            {
                id: 2,
                children: [
                    {
                        id: 5,
                        children: [
                            {
                                id: 3,
                                name: "menu 1",
                                appID: 2,
                                actionID: 1002,
                                xmlid: "app2_menu1",
                            },
                            {
                                id: 4,
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
        { mode: "replace" }
    );
    const webClient = await mountWithCleanup(WebClient);
    await runAllTimers();
    await animationFrame();
    expect(".o_menu_sections .dropdown-toggle").toHaveText("a dropdown");
    new Clickbot(webClient.env, { logger: true }).start();
    await promise;
    expect.verifySteps([
        "Starting ClickEverywhere test",
        "Testing app: App2 (app2)",
        "Testing menu menu 1 (app2_menu1)",
        "Clicking on: kanban view's new button",
        "Clicking on: go back to kanban view (from new record form view)",
        "Clicking on: open form view from kanban",
        "Clicking on: go back to kanban view (from record view)",
        "Testing 2 filters",
        'Clicking on: filter "Not Bar"',
        'Clicking on: filter "Date"',
        'Clicking on: filter "Date (October)"',
        "Testing menu menu 2 (app2_menu2)",
        "Clicking on: list view's new button",
        "Clicking on: go back to list view (from new record form view)",
        "Clicking on: open form view from list",
        "Clicking on: go back to list view (from record view)",
        "Testing 2 filters",
        'Clicking on: filter "Not Bar"',
        'Clicking on: filter "Date"',
        'Clicking on: filter "Date (October)"',
        "Test took 0 seconds",
        "Tested 1 apps",
        "Tested 2 menus",
        "Tested 2 views",
        "Tested 2 form views",
        "Tested 2 new record views",
        "Tested 0 modals",
        "Tested 4 filters",
        SUCCESS_SIGNAL,
    ]);
});

test("clickbot test waiting rpc after clicking filter", async () => {
    const { promise, resolve } = Promise.withResolvers();
    let clickBotStarted = false;
    patchWithCleanup(console, {
        log: (msg) => {
            if (msg === SUCCESS_SIGNAL) {
                expect.step(msg);
                resolve();
            }
        },
        error: () => {
            resolve();
        },
    });
    onRpc("web_search_read", async () => {
        if (clickBotStarted) {
            expect.step("web_search_read called");
            await tick();
            expect.step("response");
        }
    });
    defineActions(
        [
            {
                id: 1,
                res_model: "foo",
                views: [
                    [false, "list"],
                    [false, "form"],
                ],
            },
        ],
        { mode: "replace" }
    );
    defineMenus([
        {
            id: 1,
            actionID: 1,
            xmlid: "app1",
        },
    ]);
    const webClient = await mountWithCleanup(WebClient);
    await runAllTimers();
    await animationFrame();
    clickBotStarted = true;
    new Clickbot(webClient.env, { logger: true }).start();
    await promise;
    expect.verifySteps([
        "web_search_read called", // click on the App
        "response",
        "web_search_read called", // came back to the list view from the new record form view
        "response",
        "web_search_read called", // came back to the list view from the form view
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
    const { promise, resolve } = Promise.withResolvers();
    let clickBotStarted = false;
    let id = 1;

    patchWithCleanup(performance, {
        now: () => 43554.39999999106,
    });

    patchWithCleanup(console, {
        log: (msg) => {
            expect.step(msg);
            if (msg === SUCCESS_SIGNAL) {
                resolve();
            }
        },
        error: (msg) => {
            if (msg === FAILURE_SIGNAL) {
                expect.step(msg);
                resolve();
            } else {
                // Replace msg with null id as JSON-RPC ids are not reset between two tests
                expect.step(
                    msg
                        .toString()
                        .replaceAll(/"id":\d+,/g, `"id":null,`)
                        // Since the traceback is displayed in the dialog, we change the content of the balises "p.text-info" and "pre"
                        // containing the traceback / date / url linked to the running environnement
                        .replace(
                            /<p\b[^>]*class="d-block small text-info"[^>]*>[\s\S]*?<\/p>/i,
                            '<p class="d-block small text-info">ERROR INFO</p>'
                        )
                        .replace(/<pre\b[^>]*>[\s\S]*?<\/pre>/i, "<pre>TRACEBACK</pre>")
                );
            }
        },
    });
    onRpc("web_search_read", () => {
        if (clickBotStarted) {
            if (id === 5) {
                id++;
                // click on the Second Filter
                throw makeServerError({
                    message: "This is a server Error, it should be displayed in an error dialog",
                    type: "Programming error",
                });
            }
            id++;
        }
    });
    defineMenus([
        {
            id: 1,
            name: "App1",
            appID: 1,
            actionID: 1001,
            xmlid: "app1",
        },
        {
            id: 2,
            name: "App2",
            appID: 2,
            actionID: 1002,
            xmlid: "app2",
        },
    ]);
    const webClient = await mountWithCleanup(WebClient);
    await runAllTimers();
    await animationFrame();
    clickBotStarted = true;
    new Clickbot(webClient.env, { logger: true }).start();
    await promise;
    await tick();

    const expectedRpcData = JSON.stringify({
        data: {
            id: null,
            jsonrpc: "2.0",
            method: "call",
            params: {
                model: "foo",
                method: "web_search_read",
                args: [],
                kwargs: {
                    specification: { foo: {} },
                    offset: 0,
                    order: "",
                    limit: 80,
                    context: {
                        lang: "en",
                        tz: "taht",
                        uid: 7,
                        allowed_company_ids: [1],
                        bin_size: true,
                    },
                    count_limit: 10001,
                    domain: [
                        "|",
                        ["bar", "=", false],
                        "&",
                        ["date", ">=", "2024-04-01"],
                        ["date", "<=", "2024-04-30"],
                    ],
                },
            },
        },
        settings: { silent: false },
        error: {
            name: "RPC_ERROR",
            type: "server",
            code: 0,
            data: {
                name: "odoo.exceptions.Programming error",
                debug: "traceback",
                arguments: [],
                context: {},
                message: "This is a server Error, it should be displayed in an error dialog",
            },
            exceptionName: "odoo.exceptions.Programming error",
            subType: "server",
            message: "This is a server Error, it should be displayed in an error dialog",
            model: "foo",
            errorEvent: { isTrusted: true },
        },
    });
    const expectedModalHtml = /* xml */ `
        <header class="modal-header">
            <h4 class="modal-title text-wrap text-break fs-3 flex-grow-1">Oops!</h4>
            <button type="button" class="btn-close position-sm-absolute top-0 end-0" title="Close" aria-label="Close" tabindex="-1" data-available-offline=""></button>
        </header>
        <main class="modal-body">
            <div role="alert">
                <p> Something went wrong... If you really are stuck, share the report with your friendly support service </p>
                <details>
                    <summary class="mb-1 link-info"><span>See technical details</span><span class="ms-1 text-400 small">(10/Apr/2024 00:00:03)</span></summary>
                    <div class="text-bg-100 clearfix mt-2 position-relative o_error_detail pb-2">
                        <button class="btn position-absolute top-0 end-0 pt-2 btn-link link-body-emphasis" data-available-offline=""><span class="fa fa-clipboard"></span></button>
                        <div class="ps-1 pt-1 ps-md-3 pt-md-3">
                            <p class="m-0"><b>Odoo Server Error</b></p>
                            <p class="d-block small text-info">ERROR INFO</p>
                            <code>RPC_ERROR</code>
                            <code class="d-block">This is a server Error, it should be displayed in an error dialog</code>
                            <pre>TRACEBACK</pre>
                        </div>
                    </div>
                </details>
            </div>
        </main>
        <footer class="modal-footer d-empty-none justify-content-around justify-content-md-start flex-wrap gap-2 w-100">
            <button class="btn btn-primary o-default-button" data-available-offline="">Close</button>
        </footer>`
        .trim()
        .replaceAll(/>[\n\s]+</gm, "><");

    expect.verifyErrors(["This is a server Error"]);
    expect.verifySteps([
        "Starting ClickEverywhere test",
        "Testing app: App1 (app1)",
        "Testing menu App1 (app1)",
        "Clicking on: list view's new button",
        "Clicking on: go back to list view (from new record form view)",
        "Clicking on: open form view from list",
        "Clicking on: go back to list view (from record view)",
        "Testing 2 filters",
        'Clicking on: filter "Not Bar"',
        'Clicking on: filter "Date"',
        'Clicking on: filter "Date (April)"',
        `Error found:
 - Current testing app is App1 (app1)
 - Current testing menu is App1 (app1)
 - Current testing view is list
 - Current testing filter is Date (April)
The error is :
Error dialog detected when waiting for clicking on filter "Date (April)" : ${expectedModalHtml}
A RPC in error was detected, maybe it's related to the error dialog : ${expectedRpcData}`,
        "Testing app: App2 (app2)",
        "Testing menu App2 (app2)",
        "Clicking on: kanban view's new button",
        "Clicking on: go back to kanban view (from new record form view)",
        "Clicking on: open form view from kanban",
        "Clicking on: go back to kanban view (from record view)",
        "Testing 2 filters",
        'Clicking on: filter "Not Bar"',
        'Clicking on: filter "Date"',
        'Clicking on: filter "Date (April)"',
        "Test took 0 seconds",
        "Tested 2 apps",
        "Tested 2 menus",
        "Error found while testing 1 menus",
        "Tested 1 views",
        "Tested 2 form views",
        "Tested 2 new record views",
        "Tested 0 modals",
        "Tested 4 filters",
        FAILURE_SIGNAL,
    ]);
});

test("clickbot test waiting render after clicking filter", async () => {
    onRpc("has_group", () => true);
    const { promise, resolve } = Promise.withResolvers();
    let clickBotStarted = false;
    patchWithCleanup(console, {
        log: (msg) => {
            if (msg === SUCCESS_SIGNAL) {
                expect.step(msg);
                resolve();
            }
        },
        error: () => {
            resolve();
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
    defineActions([
        {
            id: 1,
            res_model: "foo",
            views: [[false, "list"]],
        },
    ]);
    defineMenus([
        {
            id: 1,
            actionID: 1001,
            xmlid: "app1",
        },
    ]);
    const webClient = await mountWithCleanup(WebClient);
    await runAllTimers();
    await animationFrame();
    clickBotStarted = true;
    new Clickbot(webClient.env, { logger: true }).start();
    await promise;
    expect.verifySteps([
        "onWillStart called", // click on APP
        "response",
        "onWillStart called", // open new recordForm View
        "response",
        "onWillStart called", // open Form View
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
    const { promise, resolve } = Promise.withResolvers();
    patchWithCleanup(console, {
        log: (msg) => {
            expect.step(msg);
            if (msg === SUCCESS_SIGNAL) {
                resolve();
            }
        },
        error: (msg) => {
            expect.step(msg);
            resolve();
        },
    });
    patchWithCleanup(performance, {
        now: () => 43554.39999999106,
    });
    defineActions([
        {
            id: 1099,
            name: "Modal",
            res_model: "foo",
            views: [[false, "form"]],
            view_mode: "form",
            target: "new",
        },
    ]);
    defineMenus([
        {
            id: 1,
            name: "App1",
            actionID: 1001,
            xmlid: "app1",
        },
        {
            id: 2,
            name: "App Modal",
            actionID: 1099,
            xmlid: "test.modal",
        },
    ]);
    const webClient = await mountWithCleanup(WebClient);
    new Clickbot(webClient.env, { logger: true }).start();
    await promise;
    expect.verifySteps([
        "Starting ClickEverywhere test",
        "Testing app: App1 (app1)",
        "Testing menu App1 (app1)",
        "Clicking on: list view's new button",
        "Clicking on: go back to list view (from new record form view)",
        "Clicking on: open form view from list",
        "Clicking on: go back to list view (from record view)",
        "Testing 2 filters",
        'Clicking on: filter "Not Bar"',
        'Clicking on: filter "Date"',
        'Clicking on: filter "Date (October)"',
        "Testing view switch: kanban",
        "Clicking on: kanban view switcher",
        "Clicking on: kanban view's new button",
        "Clicking on: go back to kanban view (from new record form view)",
        "Testing 2 filters",
        'Clicking on: filter "Not Bar"',
        'Clicking on: filter "Date"',
        'Clicking on: filter "Date (October)"',
        "Testing app: App Modal (test.modal)",
        "Testing menu App Modal (test.modal)",
        "Modal detected: App Modal (test.modal)",
        "Clicking on: modal close button",
        "Test took 0 seconds",
        "Tested 2 apps",
        "Tested 2 menus",
        "Tested 2 views",
        "Tested 1 form views",
        "Tested 2 new record views",
        "Tested 1 modals",
        "Tested 4 filters",
        SUCCESS_SIGNAL,
    ]);
});

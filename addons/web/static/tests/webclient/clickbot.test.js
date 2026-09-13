// @ts-check

import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import {
    animationFrame,
    Deferred,
    mockDate,
    runAllTimers,
    tick,
} from "@odoo/hoot-mock";
import { onWillStart, onWillUpdateProps } from "@odoo/owl";
import {
    contains,
    defineActions,
    defineMenus,
    defineModels,
    fields,
    makeServerError,
    models,
    mountWebClient,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { session } from "@web/session";
import { ListRenderer } from "@web/views/list/list_renderer";
import { SUCCESS_SIGNAL } from "@web/webclient/clickbot/clickbot";

const RPC_ERROR_MARKER =
    "A RPC in error was detected, maybe it's related to the error dialog : ";

/**
 * @param {string} jsonString
 * @returns {string}
 */
function canonicalJson(jsonString) {
    return JSON.stringify(JSON.parse(jsonString), (key, value) =>
        value && typeof value === "object" && !Array.isArray(value)
            ? Object.fromEntries(
                  Object.keys(value)
                      .sort()
                      .map((k) => [k, value[k]]),
              )
            : value,
    );
}

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
        search: `
            <search>
                <filter string="Not Bar" name="not bar" domain="[['bar','=',False]]"/>
                <filter string="Date" name="date" date="date"/>
            </search>
        `,
        list: `
            <list>
                <field name="foo" />
            </list>
        `,
        kanban: `
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
    onRpc("has_group", () => true);
    defineActions([
        {
            id: 1001,
            name: "App1",
            res_model: "foo",
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
            views: [[false, "kanban"]],
            xml_id: "app2_menu1",
        },
        {
            id: 1022,
            name: "App2 Menu 2",
            res_model: "foo",
            views: [[false, "list"]],
            xml_id: "app2_menu2",
        },
    ]);
});

for (const pinned of [false, true]) {
    test(`clickbot clickeverywhere test (pinned=${pinned})`, async () => {
        onRpc("has_group", () => true);
        mockDate("2017-10-08T15:35:11.000");
        const clickEverywhereDef = new Deferred();
        patchWithCleanup(browser, {
            console: {
                ...browser.console,
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
        if (pinned) {
            patchWithCleanup(session, {
                homemenu_default_config: { pinned: ["app1", "app2"] },
            });
        }
        const webClient = await mountWebClient();
        patchWithCleanup(odoo, {
            __WOWL_DEBUG__: { root: webClient },
        });
        if (pinned) {
            await webClient.env.services.home_menu.toggle(true);
            expect(".o_pinned_apps .o_app").toHaveCount(2);
        }
        window.clickEverywhere();
        await clickEverywhereDef;
        expect.verifySteps([
            "Testing app menu: app1",
            "Testing menu App1 app1",
            'Clicking on: menu item "App1"',
            "Clicking on: search bar menu dropdown",
            "Testing 2 filters",
            'Clicking on: filter "Not Bar"',
            'Clicking on: filter "Date"',
            'Clicking on: filter option "October"',
            "Testing view switch: kanban",
            "Clicking on: kanban view switcher",
            "Clicking on: search bar menu dropdown",
            "Testing 2 filters",
            'Clicking on: filter "Not Bar"',
            'Clicking on: filter "Date"',
            'Clicking on: filter option "October"',
            "Clicking on: home menu toggle button",
            "Testing app menu: app2",
            "Testing menu App2 app2",
            'Clicking on: menu item "App2"',
            "Clicking on: search bar menu dropdown",
            "Testing 2 filters",
            'Clicking on: filter "Not Bar"',
            'Clicking on: filter "Date"',
            'Clicking on: filter option "October"',
            "Testing menu menu 1 app2_menu1",
            'Clicking on: menu item "menu 1"',
            "Clicking on: search bar menu dropdown",
            "Testing 2 filters",
            'Clicking on: filter "Not Bar"',
            'Clicking on: filter "Date"',
            'Clicking on: filter option "October"',
            "Testing menu menu 2 app2_menu2",
            'Clicking on: menu item "menu 2"',
            "Clicking on: search bar menu dropdown",
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
}

test("only one app", async () => {
    onRpc("has_group", () => true);
    mockDate("2017-10-08T15:35:11.000");
    const clickEverywhereDef = new Deferred();
    patchWithCleanup(browser.localStorage, {
        removeItem(key) {
            const savedState = (super.getItem(key) || "").replace(
                /"startedAt":\d+/,
                '"startedAt":<ts>',
            );
            expect.step("savedState: " + savedState);
            return super.removeItem(key);
        },
    });
    patchWithCleanup(browser, {
        console: {
            ...browser.console,
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
    const webClient = await mountWebClient();
    patchWithCleanup(odoo, {
        __WOWL_DEBUG__: { root: webClient },
    });
    window.clickEverywhere("app1");
    await clickEverywhereDef;
    expect.verifySteps([
        "Testing app menu: app1",
        "Testing menu App1 app1",
        'Clicking on: menu item "App1"',
        "Clicking on: search bar menu dropdown",
        "Testing 2 filters",
        'Clicking on: filter "Not Bar"',
        'Clicking on: filter "Date"',
        'Clicking on: filter option "October"',
        "Testing view switch: kanban",
        "Clicking on: kanban view switcher",
        "Clicking on: search bar menu dropdown",
        "Testing 2 filters",
        'Clicking on: filter "Not Bar"',
        'Clicking on: filter "Date"',
        'Clicking on: filter option "October"',
        "Successfully tested 1 apps",
        "Successfully tested 0 menus",
        "Successfully tested 0 modals",
        "Successfully tested 4 filters",
        SUCCESS_SIGNAL,
        'savedState: {"light":false,"startedAt":<ts>,"studioCount":0,"testedApps":["app1"],"testedMenus":["app1"],"testedFilters":4,"testedModals":0,"appIndex":0,"menuIndex":0,"subMenuIndex":0,"xmlId":"app1","app":"app1"}',
    ]);
});

test("clickbot clickeverywhere test (with dropdown menu)", async () => {
    onRpc("has_group", () => true);
    mockDate("2017-10-08T15:35:11.000");
    const clickEverywhereDef = new Deferred();
    patchWithCleanup(browser, {
        console: {
            ...browser.console,
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
        { mode: "replace" },
    );
    const webClient = await mountWebClient();
    patchWithCleanup(odoo, {
        __WOWL_DEBUG__: { root: webClient },
    });
    await contains(".o_home_menu .o_app").click();
    await runAllTimers();
    await waitFor(".o_menu_sections .dropdown-toggle");
    expect(".o_menu_sections .dropdown-toggle").toHaveText("a dropdown");
    window.clickEverywhere();
    await clickEverywhereDef;
    expect.verifySteps([
        "Clicking on: home menu toggle button",
        "Testing app menu: app2",
        "Testing menu App2 app2",
        'Clicking on: menu item "App2"',
        "Clicking on: search bar menu dropdown",
        "Testing 2 filters",
        'Clicking on: filter "Not Bar"',
        'Clicking on: filter "Date"',
        'Clicking on: filter option "October"',
        "Clicking on: menu toggler",
        "Testing menu menu 1 app2_menu1",
        'Clicking on: menu item "menu 1"',
        "Clicking on: search bar menu dropdown",
        "Testing 2 filters",
        'Clicking on: filter "Not Bar"',
        'Clicking on: filter "Date"',
        'Clicking on: filter option "October"',
        "Clicking on: menu toggler",
        "Testing menu menu 2 app2_menu2",
        'Clicking on: menu item "menu 2"',
        "Clicking on: search bar menu dropdown",
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
    const clickEverywhereDef = new Deferred();
    let clickBotStarted = false;
    patchWithCleanup(browser, {
        console: {
            ...browser.console,
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
    defineActions(
        [
            {
                id: 1,
                res_model: "foo",
                views: [[false, "list"]],
            },
        ],
        { mode: "replace" },
    );
    defineMenus([
        {
            id: 1,
            actionID: 1,
            xmlid: "app1",
        },
    ]);
    const webClient = await mountWebClient();
    patchWithCleanup(odoo, {
        __WOWL_DEBUG__: { root: webClient },
    });
    await runAllTimers();
    await animationFrame();
    clickBotStarted = true;
    window.clickEverywhere();
    await clickEverywhereDef;
    expect.verifySteps([
        "web_search_read called",
        "response",
        "web_search_read called",
        "response",
        "web_search_read called",
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
            ...browser.console,
            log: (msg) => {
                if (msg === "test successful") {
                    expect.step(msg);
                    clickEverywhereDef.resolve();
                }
            },
            error: (msg) => {
                msg = msg
                    .toString()
                    .replaceAll(/"id":\d+,/g, `"id":null,`)
                    .replaceAll(/id="dialog_\d+_title"/g, 'id="dialog_0_title"');
                if (msg.startsWith(RPC_ERROR_MARKER)) {
                    msg =
                        RPC_ERROR_MARKER +
                        canonicalJson(msg.slice(RPC_ERROR_MARKER.length));
                }
                expect.step(msg);
                clickEverywhereDef.resolve();
            },
        },
    });
    onRpc("web_search_read", () => {
        if (clickBotStarted) {
            if (id === 3) {
                throw makeServerError({
                    message:
                        "This is a server Error, it should be displayed in an error dialog",
                    type: "Programming error",
                });
            }
            id++;
        }
    });
    defineActions([
        {
            id: 1,
            name: "App1",
            res_model: "foo",
            views: [[false, "list"]],
        },
    ]);
    defineMenus([
        {
            id: 1,
            name: "App1",
            appID: 1,
            actionID: 1001,
            xmlid: "app1",
        },
    ]);
    const webClient = await mountWebClient();
    patchWithCleanup(odoo, {
        __WOWL_DEBUG__: { root: webClient },
    });
    await runAllTimers();
    await animationFrame();
    clickBotStarted = true;
    window.clickEverywhere();
    await clickEverywhereDef;
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
        url: "/web/dataset/call_kw/foo/web_search_read",
        settings: { silent: false, cache: false, retry: false, dedup: false },
        error: {
            name: "RPC_ERROR",
            type: "server",
            code: 0,
            data: {
                name: "odoo.exceptions.Programming error",
                debug: "traceback",
                arguments: [],
                context: {},
                message:
                    "This is a server Error, it should be displayed in an error dialog",
            },
            exceptionName: "odoo.exceptions.Programming error",
            retryable: false,
            subType: "server",
            message:
                "This is a server Error, it should be displayed in an error dialog",
            model: "foo",
            errorEvent: { isTrusted: true },
        },
    });
    const expectedModalHtml = `
        <header class="modal-header">
            <h4 class="modal-title text-break flex-grow-1" id="dialog_0_title">Oops!</h4>
            <button type="button" class="btn-close" aria-label="Close" tabindex="-1"></button>
        </header>
        <main class="modal-body">
            <div role="alert">
                <p class="text-prewrap"> Something went wrong... If you really are stuck, share the report with your friendly support service </p>
                <button class="btn btn-link p-0">See technical details</button>
            </div>
        </main>
        <footer class="modal-footer d-empty-none justify-content-around justify-content-md-start flex-wrap gap-1 w-100">
            <button class="btn btn-primary o-default-button">Close</button>
        </footer>`
        .trim()
        .replaceAll(/>[\n\s]+</gm, "><");

    expect.verifyErrors(["This is a server Error"]);
    expect.verifySteps([
        `${RPC_ERROR_MARKER}${canonicalJson(expectedRpcData)}`,
        "Error while testing App1 app1",
        `Error: Error dialog detected${expectedModalHtml}`,
    ]);
});

test("clickbot test waiting render after clicking filter", async () => {
    onRpc("has_group", () => true);
    const clickEverywhereDef = new Deferred();
    let clickBotStarted = false;
    patchWithCleanup(browser, {
        console: {
            ...browser.console,
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
    const webClient = await mountWebClient();
    patchWithCleanup(odoo, {
        __WOWL_DEBUG__: { root: webClient },
    });
    await runAllTimers();
    await animationFrame();
    clickBotStarted = true;
    window.clickEverywhere();
    await clickEverywhereDef;
    expect.verifySteps([
        "onWillStart called",
        "response",
        "onWillUpdateProps called",
        "response",
        "onWillUpdateProps called",
        "response",
        SUCCESS_SIGNAL,
    ]);
});

test("clickbot clickeverywhere menu modal", async () => {
    onRpc("has_group", () => true);
    mockDate("2017-10-08T15:35:11.000");
    Foo._views.form = `
        <form>
            <field name="foo"/>
        </form>
    `;
    const clickEverywhereDef = new Deferred();
    patchWithCleanup(browser, {
        console: {
            ...browser.console,
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
    const webClient = await mountWebClient();
    patchWithCleanup(odoo, {
        __WOWL_DEBUG__: { root: webClient },
    });
    window.clickEverywhere();
    await clickEverywhereDef;
    expect.verifySteps([
        "Testing app menu: app1",
        "Testing menu App1 app1",
        'Clicking on: menu item "App1"',
        "Clicking on: search bar menu dropdown",
        "Testing 2 filters",
        'Clicking on: filter "Not Bar"',
        'Clicking on: filter "Date"',
        'Clicking on: filter option "October"',
        "Testing view switch: kanban",
        "Clicking on: kanban view switcher",
        "Clicking on: search bar menu dropdown",
        "Testing 2 filters",
        'Clicking on: filter "Not Bar"',
        'Clicking on: filter "Date"',
        'Clicking on: filter option "October"',
        "Clicking on: home menu toggle button",
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

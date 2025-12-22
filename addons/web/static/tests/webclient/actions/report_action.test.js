import { afterEach, expect, test } from "@odoo/hoot";
import { runAllTimers } from "@odoo/hoot-mock";
import {
    contains,
    defineActions,
    defineModels,
    getService,
    mockService,
    models,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    serverState,
    stepAllNetworkCalls,
} from "@web/../tests/web_test_helpers";

import { router } from "@web/core/browser/router";
import { download } from "@web/core/network/download";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { ReportAction } from "@web/webclient/actions/reports/report_action";
import { downloadReport } from "@web/webclient/actions/reports/utils";
import { WebClient } from "@web/webclient/webclient";

class Partner extends models.Model {
    _rec_name = "display_name";

    _records = [
        { id: 1, display_name: "First record" },
        { id: 2, display_name: "Second record" },
    ];
    _views = {
        form: `
            <form>
                <header>
                    <button name="object" string="Call method" type="object"/>
                </header>
                <group>
                    <field name="display_name"/>
                </group>
            </form>`,
        "kanban,1": `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="display_name"/>
                    </t>
                </templates>
            </kanban>`,
        list: `<list><field name="display_name"/></list>`,
    };
}

defineModels([Partner]);

defineActions([
    {
        id: 7,
        xml_id: "action_7",
        name: "Some Report",
        report_name: "some_report",
        report_type: "qweb-pdf",
        type: "ir.actions.report",
    },
    {
        id: 11,
        xml_id: "action_11",
        name: "Another Report",
        report_name: "another_report",
        report_type: "qweb-pdf",
        type: "ir.actions.report",
        close_on_report_download: true,
    },
    {
        id: 12,
        xml_id: "action_12",
        name: "Some HTML Report",
        report_name: "some_report",
        report_type: "qweb-html",
        type: "ir.actions.report",
    },
]);

afterEach(() => {
    // In the prod environment, we keep a promise with the wkhtmlstatus (e.g. broken, upgrade...).
    // This ensures the request to be done only once. In the test environment, we mock this request
    // to simulate the different status, so we want to erase the promise at the end of each test,
    // otherwise all tests but the first one would use the status in cache.
    delete downloadReport.wkhtmltopdfStatusProm;
});

test("can execute report actions from db ID", async () => {
    patchWithCleanup(download, {
        _download: (options) => {
            expect.step(options.url);
            return Promise.resolve();
        },
    });
    onRpc("/report/check_wkhtmltopdf", () => "ok");
    stepAllNetworkCalls();

    await mountWithCleanup(WebClient);
    await getService("action").doAction(7, { onClose: () => expect.step("on_close") });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "/report/check_wkhtmltopdf",
        "/report/download",
        "on_close",
    ]);
});

test("report actions can close modals and reload views", async () => {
    defineActions([
        {
            id: 5,
            name: "Create a Partner",
            res_model: "partner",
            target: "new",
            views: [[false, "form"]],
        },
    ]);
    patchWithCleanup(download, {
        _download: (options) => {
            expect.step(options.url);
            return Promise.resolve();
        },
    });

    onRpc("/report/check_wkhtmltopdf", () => "ok");

    await mountWithCleanup(WebClient);
    await getService("action").doAction(5, { onClose: () => expect.step("on_close") });
    expect(".o_technical_modal .o_form_view").toHaveCount(1, {
        message: "should have rendered a form view in a modal",
    });

    await getService("action").doAction(7, { onClose: () => expect.step("on_printed") });
    expect(".o_technical_modal .o_form_view").toHaveCount(1, {
        message: "The modal should still exist",
    });

    await getService("action").doAction(11);
    expect(".o_technical_modal .o_form_view").toHaveCount(0, {
        message: "the modal should have been closed after the action report",
    });
    expect.verifySteps(["/report/download", "on_printed", "/report/download", "on_close"]);
});

test("should trigger a notification if wkhtmltopdf is to upgrade", async () => {
    patchWithCleanup(download, {
        _download: (options) => {
            expect.step(options.url);
            return Promise.resolve();
        },
    });
    mockService("notification", {
        add: () => expect.step("notify"),
    });

    onRpc("/report/check_wkhtmltopdf", () => "upgrade");
    stepAllNetworkCalls();

    await mountWithCleanup(WebClient);
    await getService("action").doAction(7);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "/report/check_wkhtmltopdf",
        "/report/download",
        "notify",
    ]);
});

test("should open the report client action if wkhtmltopdf is broken", async () => {
    // patch the report client action to override its iframe's url so that
    // it doesn't trigger an RPC when it is appended to the DOM
    patchWithCleanup(ReportAction.prototype, {
        setup() {
            super.setup(...arguments);
            rpc(this.reportUrl);
            this.reportUrl = "about:blank";
        },
    });
    patchWithCleanup(download, {
        _download: () => {
            expect.step("download"); // should not be called
            return Promise.resolve();
        },
    });
    mockService("notification", {
        add: () => expect.step("notify"),
    });

    onRpc("/report/check_wkhtmltopdf", () => "broken");
    onRpc("/report/html/some_report", async (request) => {
        const search = decodeURIComponent(new URL(request.url).search);
        expect(search).toBe(`?context={"lang":"en","tz":"taht","uid":7,"allowed_company_ids":[1]}`);
        return true;
    });
    stepAllNetworkCalls();

    await mountWithCleanup(WebClient);
    await getService("action").doAction(7);
    expect(".o_content iframe").toHaveCount(1, {
        message: "should have opened the report client action",
    });
    // the control panel has the content twice and a d-none class is toggled depending the screen size
    expect(":not(.d-none) > button[title='Print']").toHaveCount(1, {
        message: "should have a print button",
    });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "/report/check_wkhtmltopdf",
        "notify",
        "/report/html/some_report",
    ]);
});

test("send context in case of html report", async () => {
    serverState.userContext = { some_key: 2 };
    // patch the report client action to override its iframe's url so that
    // it doesn't trigger an RPC when it is appended to the DOM
    patchWithCleanup(ReportAction.prototype, {
        setup() {
            super.setup(...arguments);
            rpc(this.reportUrl);
            this.reportUrl = "about:blank";
        },
    });
    patchWithCleanup(download, {
        _download: () => {
            expect.step("download"); // should not be called
            return Promise.resolve();
        },
    });
    mockService("notification", {
        add(message, options) {
            expect.step(options.type || "notification");
        },
    });

    onRpc("/report/html/some_report", async (request) => {
        const search = decodeURIComponent(new URL(request.url).search);
        expect(search).toBe(
            `?context={"some_key":2,"lang":"en","tz":"taht","uid":7,"allowed_company_ids":[1]}`
        );
        return true;
    });
    stepAllNetworkCalls();

    await mountWithCleanup(WebClient);
    await getService("action").doAction(12);
    expect(".o_content iframe").toHaveCount(1, { message: "should have opened the client action" });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "/report/html/some_report",
    ]);
});

test("UI unblocks after downloading the report even if it threw an error", async () => {
    let timesDownloasServiceHasBeenCalled = 0;
    patchWithCleanup(download, {
        _download: () => {
            if (timesDownloasServiceHasBeenCalled === 0) {
                expect.step("successful download");
                timesDownloasServiceHasBeenCalled++;
                return Promise.resolve();
            }
            if (timesDownloasServiceHasBeenCalled === 1) {
                expect.step("failed download");
                return Promise.reject();
            }
        },
    });

    onRpc("/report/check_wkhtmltopdf", () => "ok");

    await mountWithCleanup(WebClient);
    const onBlock = () => {
        expect.step("block");
    };
    const onUnblock = () => {
        expect.step("unblock");
    };
    getService("ui").bus.addEventListener("BLOCK", onBlock);
    getService("ui").bus.addEventListener("UNBLOCK", onUnblock);

    await getService("action").doAction(7);
    try {
        await getService("action").doAction(7);
    } catch {
        expect.step("error caught");
    }
    expect.verifySteps([
        "block",
        "successful download",
        "unblock",
        "block",
        "failed download",
        "unblock",
        "error caught",
    ]);
    getService("ui").bus.removeEventListener("BLOCK", onBlock);
    getService("ui").bus.removeEventListener("UNBLOCK", onUnblock);
});

test("can use custom handlers for report actions", async () => {
    patchWithCleanup(download, {
        _download: (options) => {
            expect.step(options.url);
            return Promise.resolve();
        },
    });

    onRpc("/report/check_wkhtmltopdf", () => "ok");
    stepAllNetworkCalls();

    await mountWithCleanup(WebClient);
    let customHandlerCalled = false;
    registry.category("ir.actions.report handlers").add("custom_handler", async (action) => {
        if (action.id === 7 && !customHandlerCalled) {
            customHandlerCalled = true;
            expect.step("calling custom handler");
            return true;
        }
        expect.step("falling through to default handler");
    });
    await getService("action").doAction(7);
    expect.step("first doAction finished");

    await getService("action").doAction(7);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "calling custom handler",
        "first doAction finished",
        "falling through to default handler",
        "/report/check_wkhtmltopdf",
        "/report/download",
    ]);
});

test.tags("desktop");
test("context is correctly passed to the client action report", async (assert) => {
    patchWithCleanup(download, {
        _download: (options) => {
            expect.step(options.url);
            expect(options.data.context).toBe(
                `{"lang":"en","tz":"taht","uid":7,"allowed_company_ids":[1],"rabbia":"E Tarantella","active_ids":[99]}`
            );
            expect(JSON.parse(options.data.data)).toEqual([
                "/report/pdf/ennio.morricone/99",
                "qweb-pdf",
            ]);
            return Promise.resolve();
        },
    });
    patchWithCleanup(ReportAction.prototype, {
        setup() {
            super.setup(...arguments);
            rpc(this.reportUrl);
            this.reportUrl = "about:blank";
        },
    });

    onRpc("/report/check_wkhtmltopdf", () => "ok");
    onRpc("/report/html", async (request) => {
        const search = decodeURIComponent(new URL(request.url).search);
        expect(search).toBe(`?context={"lang":"en","tz":"taht","uid":7,"allowed_company_ids":[1]}`);
        return true;
    });
    stepAllNetworkCalls();

    await mountWithCleanup(WebClient);

    const action = {
        context: {
            rabbia: "E Tarantella",
            active_ids: [99],
        },
        data: null,
        name: "Ennio Morricone",
        report_name: "ennio.morricone",
        report_type: "qweb-html",
        type: "ir.actions.report",
    };
    expect.verifySteps(["/web/webclient/translations", "/web/webclient/load_menus"]);

    await getService("action").doAction(action);
    expect.verifySteps(["/report/html/ennio.morricone/99"]);

    await contains(".o_control_panel_main_buttons button[title='Print']").click();
    expect.verifySteps(["/report/check_wkhtmltopdf", "/report/download"]);
});

test("url is valid", async (assert) => {
    patchWithCleanup(ReportAction.prototype, {
        init() {
            super.init(...arguments);
            this.reportUrl = "about:blank";
        },
    });

    await mountWithCleanup(WebClient);
    await getService("action").doAction(12); // 12 is a html report action
    await runAllTimers();
    const urlState = router.current;
    // used to put report.client_action in the url
    expect(urlState.action === "report.client_action").toBe(false);
    expect(urlState.action).toBe(12);
});

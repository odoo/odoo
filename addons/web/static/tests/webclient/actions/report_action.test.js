// @ts-check

import { expect, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { animationFrame, Deferred, runAllTimers } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import {
    contains,
    defineActions,
    defineModels,
    getService,
    mockService,
    models,
    mountWebClient,
    onRpc,
    patchWithCleanup,
    serverState,
    stepAllNetworkCalls,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { router } from "@web/core/browser/router";
import { makeLogger } from "@web/core/debug/debug_logger";
import { AppEvent } from "@web/core/events";
import { download } from "@web/core/network/download";
import { registry } from "@web/core/registry";
import { SupersededError } from "@web/core/utils/concurrency";
import { ReportAction } from "@web/webclient/actions/reports/report_action";
import { downloadReport } from "@web/webclient/actions/reports/utils";

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

test("can execute report actions from db ID", async () => {
    patchWithCleanup(download, {
        _download: (options) => {
            expect.step(options.url);
            return Promise.resolve();
        },
    });
    stepAllNetworkCalls();

    await mountWebClient();
    await getService("action").doAction(7, { onClose: () => expect.step("on_close") });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
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

    await mountWebClient();
    await getService("action").doAction(5, { onClose: () => expect.step("on_close") });
    expect(".o_technical_modal .o_form_view").toHaveCount(1, {
        message: "should have rendered a form view in a modal",
    });

    await getService("action").doAction(7, {
        onClose: () => expect.step("on_printed"),
    });
    expect(".o_technical_modal .o_form_view").toHaveCount(1, {
        message: "The modal should still exist",
    });

    await getService("action").doAction(11);
    await animationFrame();
    expect(".o_technical_modal .o_form_view").toHaveCount(0, {
        message: "the modal should have been closed after the action report",
    });
    expect.verifySteps([
        "/report/download",
        "on_printed",
        "/report/download",
        "on_close",
    ]);
});

test("send context in case of html report", async () => {
    serverState.userContext = { some_key: 2 };
    patchWithCleanup(ReportAction.prototype, {
        setup() {
            super.setup(...arguments);
            browser.fetch(this.reportUrl);
            this.reportUrl = "about:blank";
        },
    });
    patchWithCleanup(download, {
        _download: () => {
            expect.step("download");
            return Promise.resolve();
        },
    });
    mockService("notification", {
        add(message, options) {
            expect.step(options.type || "notification");
            return () => {};
        },
    });

    onRpc("/report/html/some_report", async (request) => {
        const search = decodeURIComponent(new URL(request.url).search);
        expect(search).toBe(
            `?context={"some_key":2,"lang":"en","tz":"taht","uid":7,"allowed_company_ids":[1]}`,
        );
        return true;
    });
    stepAllNetworkCalls();

    await mountWebClient();
    await getService("action").doAction(12);
    expect(".o_content iframe").toHaveCount(1, {
        message: "should have opened the client action",
    });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "/report/html/some_report",
    ]);
});

test("downloadReport resolves with nothing (no wkhtmltopdf-fallback plumbing)", async () => {
    patchWithCleanup(download, {
        _download: (options) => {
            expect.step(options.url);
            return Promise.resolve();
        },
    });
    /** @type {import("@web/webclient/actions/action_service").ReportAction} */
    const action = {
        type: "ir.actions.report",
        report_name: "some_report",
        report_type: "qweb-pdf",
    };
    const result = await downloadReport(action, "pdf", {});
    expect(result).toBe(undefined);
    expect.verifySteps(["/report/download"]);
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

    await mountWebClient();
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

    stepAllNetworkCalls();

    await mountWebClient();
    let customHandlerCalled = false;
    registry
        .category("ir.actions.report handlers")
        .add("custom_handler", async (action) => {
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
        "/report/download",
    ]);
});

test("custom handlers can close modals", async () => {
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

    await mountWebClient();
    registry
        .category("ir.actions.report handlers")
        .add("custom_handler", async (action) => {
            expect.step("calling custom handler for action " + action.id);
            return true;
        });

    await getService("action").doAction(5);
    await waitFor(".o_technical_modal .o_form_view");
    expect(".o_technical_modal .o_form_view").toHaveCount(1, {
        message: "should have rendered a form view in a modal",
    });

    await getService("action").doAction(7);
    expect(".o_technical_modal .o_form_view").toHaveCount(1, {
        message: "The modal should still exist",
    });

    await getService("action").doAction(11);
    await animationFrame();
    expect(".o_technical_modal .o_form_view").toHaveCount(0, {
        message: "the modal should have been closed after the custom handler",
    });
    expect.verifySteps([
        "calling custom handler for action 7",
        "calling custom handler for action 11",
    ]);
});

test.tags("desktop");
test("context is correctly passed to the client action report", async (assert) => {
    patchWithCleanup(download, {
        _download: (options) => {
            expect.step(options.url);
            expect(options.data.context).toBe(
                `{"lang":"en","tz":"taht","uid":7,"allowed_company_ids":[1],"rabbia":"E Tarantella","active_ids":[99]}`,
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
            browser.fetch(this.reportUrl);
            this.reportUrl = "about:blank";
        },
    });

    onRpc("/report/html/ennio.morricone/99", async (request) => {
        const search = decodeURIComponent(new URL(request.url).search);
        expect(search).toBe(
            `?context={"lang":"en","tz":"taht","uid":7,"allowed_company_ids":[1],"rabbia":"E Tarantella","active_ids":[99]}`,
        );
        return true;
    });
    stepAllNetworkCalls();

    await mountWebClient();

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
    expect.verifySteps(["/report/download"]);
});

test("url is valid", async (assert) => {
    patchWithCleanup(ReportAction.prototype, {
        init() {
            super.init(...arguments);
            this.reportUrl = "about:blank";
        },
    });

    await mountWebClient();
    await getService("action").doAction(12);
    await runAllTimers();
    const urlState = router.current;
    expect(urlState.action === "report.client_action").toBe(false);
    expect(urlState.action).toBe(12);
});

test("direct HTML report dispatch respects an inline leave veto", async () => {
    const webClient = await mountWebClient();
    const action = getService("action");
    const controller = action.currentController;
    const veto = ({ detail }) => detail.push(() => false);
    webClient.env.bus.addEventListener(AppEvent.CLEAR_UNCOMMITTED_CHANGES, veto);
    await action.doAction({
        type: "ir.actions.report",
        report_type: "qweb-html",
        report_name: "test",
    });
    expect(action.currentController).toBe(controller);
    webClient.env.bus.removeEventListener(AppEvent.CLEAR_UNCOMMITTED_CHANGES, veto);
});

test("a delayed report handler cannot revive a superseded inline report", async () => {
    class NewerAction extends Component {
        static template = xml`<div>Newer navigation</div>`;
        static props = ["*"];
    }
    registry.category("actions").add("newer_review", NewerAction);
    patchWithCleanup(ReportAction.prototype, {
        init() {
            super.init(...arguments);
            this.reportUrl = "about:blank";
        },
    });
    const pending = new Deferred();
    const entered = new Deferred();
    registry.category("ir.actions.report handlers").add("delayed_review", async () => {
        entered.resolve();
        return pending;
    });
    await mountWebClient();
    const action = getService("action");
    const report = action
        .doAction({
            type: "ir.actions.report",
            report_type: "qweb-html",
            report_name: "stale",
        })
        .catch((error) => error);
    await entered;
    await action.doAction({
        type: "ir.actions.client",
        tag: "newer_review",
    });
    const current = action.currentController;
    pending.resolve(false);
    expect(await report).toBeInstanceOf(SupersededError);
    makeLogger("web.report.test").logic("late handler returned", {
        action: action.currentController?.action.type,
    });
    expect(action.currentController?.jsId).toBe(current?.jsId);
});

// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { download } from "@web/core/network/download";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { NavigationTracker } from "@web/webclient/actions/navigation_token";
import { ReportAction } from "@web/webclient/actions/reports/report_action";
import {
    executeReportAction,
    executeReportClientAction,
} from "@web/webclient/actions/reports/report_executor";
import { getReportUrl } from "@web/webclient/actions/reports/utils";

/** @param {Object} [overrides] */
function makeFakeAm(overrides = {}) {
    /** @type {Record<string, any[]>} */
    const calls = { updateUI: [], doAction: [], ui: [], actionInfo: [] };
    const am = {
        navigation: new NavigationTracker(),
        confirmLeave: async () => true,
        env: { marker: "the-env" },
        uiService: {
            block: () => calls.ui.push("block"),
            unblock: () => calls.ui.push("unblock"),
        },
        makeController: (params) => ({ jsId: "controller_1", ...params }),
        getActionInfo: (action, props) => {
            calls.actionInfo.push({ action, props });
            return { props };
        },
        updateUI: async (controller, options) => {
            calls.updateUI.push({ controller, options });
            return "updateUI-result";
        },
        doAction: async (action, options) => {
            calls.doAction.push({ action, options });
            return "doAction-result";
        },
        ...overrides,
    };
    am.__calls = calls;
    return am;
}

/** @param {Object} [overrides] */
function makeReportAction(overrides = {}) {
    return /** @type {any} */ ({
        type: "ir.actions.report",
        report_type: "qweb-pdf",
        report_name: "sale.report_saleorder",
        report_file: "sale.report_saleorder",
        name: "Quotation",
        display_name: "Quotation",
        ...overrides,
    });
}

function patchDownload({ fails = false } = {}) {
    const downloads = [];
    patchWithCleanup(download, {
        _download: async (options) => {
            downloads.push(options);
            if (fails) {
                throw new Error("download failed");
            }
        },
    });
    return downloads;
}

function defineReportHandler(name, handler) {
    registry.category("ir.actions.report handlers").add(name, handler);
}

describe.current.tags("desktop");

test("a plain report url is just type and report name", async () => {
    expect(getReportUrl(makeReportAction(), "pdf", {})).toBe(
        "/report/pdf/sale.report_saleorder",
    );
});

test("action.data is encoded into options and context query params", async () => {
    const url = getReportUrl(
        makeReportAction({ data: { form: 1 }, context: { lang: "fr_FR" } }),
        "pdf",
        {},
    );
    expect(url).toInclude(`options=${encodeURIComponent('{"form":1}')}`);
    expect(url).toInclude(`context=${encodeURIComponent('{"lang":"fr_FR"}')}`);
});

test("an empty data object is treated as no data at all", async () => {
    const url = getReportUrl(
        makeReportAction({ data: {}, context: { active_ids: [3, 4] } }),
        "pdf",
        {},
    );
    expect(url).toBe("/report/pdf/sale.report_saleorder/3,4");
});

test("active_ids become a path segment when there is no data", async () => {
    const url = getReportUrl(
        makeReportAction({ context: { active_ids: [7] } }),
        "pdf",
        {},
    );
    expect(url).toBe("/report/pdf/sale.report_saleorder/7");
});

test("an html report carries the user context as a query param", async () => {
    const url = getReportUrl(makeReportAction(), "html", { lang: "en_US" });
    expect(url).toBe(
        `/report/html/sale.report_saleorder?context=${encodeURIComponent('{"lang":"en_US"}')}`,
    );
});

test("an html report renders the ReportAction component", async () => {
    const am = makeFakeAm();
    const action = makeReportAction({ report_type: "qweb-html" });

    const res = await executeReportAction(action, {}, am);

    expect(am.__calls.updateUI).toHaveLength(1);
    expect(am.__calls.updateUI[0].controller.Component).toBe(ReportAction);
    expect(res).toBe("updateUI-result");
    expect(am.__calls.ui).toEqual([]);
});

test("the preview props carry the html url and a COPY of the action context", async () => {
    const am = makeFakeAm();
    const context = { active_ids: [1] };
    const action = makeReportAction({ report_type: "qweb-html", context });

    await executeReportClientAction(action, { props: { extra: true } }, am);

    const { props } = am.__calls.actionInfo[0];
    expect(props.report_url).toInclude("/report/html/sale.report_saleorder");
    expect(props.extra).toBe(true);
    expect(props.report_name).toBe("sale.report_saleorder");
    expect(props.context).toEqual(context);
    expect(props.context).not.toBe(context);
});

test("a pdf report downloads and pairs block with unblock", async () => {
    const downloads = patchDownload();
    const am = makeFakeAm();

    await executeReportAction(makeReportAction(), {}, am);

    expect(downloads).toHaveLength(1);
    expect(am.__calls.ui).toEqual(["block", "unblock"]);
    expect(am.__calls.updateUI).toEqual([]);
});

test("a text report downloads as text, not pdf", async () => {
    const downloads = patchDownload();
    const am = makeFakeAm();

    await executeReportAction(makeReportAction({ report_type: "qweb-text" }), {}, am);

    const [url, reportType] = JSON.parse(downloads[0].data.data);
    expect(url).toInclude("/report/text/");
    expect(reportType).toBe("qweb-text");
});

test("the download context is the user context overlaid with the action's", async () => {
    const downloads = patchDownload();
    const am = makeFakeAm();
    const action = makeReportAction({ context: { lang: "fr_FR", extra: 1 } });

    await executeReportAction(action, {}, am);

    const context = JSON.parse(downloads[0].data.context);
    expect(context.extra).toBe(1);
    expect(context.lang).toBe("fr_FR");
    expect(context.uid).toBe(user.context.uid);
});

test("a failed download still unblocks the UI and propagates", async () => {
    patchDownload({ fails: true });
    const am = makeFakeAm();

    await expect(executeReportAction(makeReportAction(), {}, am)).rejects.toThrow(
        /download failed/,
    );

    expect(am.__calls.ui).toEqual(["block", "unblock"]);
});

test("close_on_report_download closes the wrapping dialog after downloading", async () => {
    patchDownload();
    const am = makeFakeAm();
    const onClose = () => {};

    await executeReportAction(
        makeReportAction({ close_on_report_download: true }),
        { onClose },
        am,
    );

    expect(am.__calls.doAction).toHaveLength(1);
    expect(am.__calls.doAction[0].action).toEqual({
        type: "ir.actions.act_window_close",
    });
    expect(am.__calls.doAction[0].options.onClose).toBe(onClose);
});

test("without the close flag, onClose runs directly and no action is dispatched", async () => {
    patchDownload();
    const am = makeFakeAm();
    let closed = 0;

    await executeReportAction(makeReportAction(), { onClose: () => closed++ }, am);

    expect(closed).toBe(1);
    expect(am.__calls.doAction).toEqual([]);
});

test("a handler returning truthy short-circuits the whole report flow", async () => {
    const downloads = patchDownload();
    defineReportHandler("re_short", () => "handled");
    const am = makeFakeAm();

    const res = await executeReportAction(makeReportAction(), {}, am);

    expect(res).toBe("handled");
    expect(downloads).toEqual([]);
    expect(am.__calls.updateUI).toEqual([]);
    expect(am.__calls.ui).toEqual([]);
});

test("handlers receive the action, the options and the env", async () => {
    patchDownload();
    const seen = [];
    defineReportHandler("re_args", (action, options, env) => {
        seen.push({ action, options, env });
    });
    const am = makeFakeAm();
    const action = makeReportAction();
    const options = { onClose: () => {} };

    await executeReportAction(action, options, am);

    expect(seen).toHaveLength(1);
    expect(seen[0].action).toBe(action);
    expect(seen[0].options).toBe(options);
    expect(seen[0].env.marker).toBe("the-env");
});

test("a handler returning falsy falls through to the default flow", async () => {
    const downloads = patchDownload();
    defineReportHandler("re_passthrough", () => undefined);
    const am = makeFakeAm();

    await executeReportAction(makeReportAction(), {}, am);

    expect(downloads).toHaveLength(1);
});

test("a handling handler honours close_on_report_download", async () => {
    defineReportHandler("re_short_close", () => "handled");
    const am = makeFakeAm();
    const onClose = () => {};

    const res = await executeReportAction(
        makeReportAction({ close_on_report_download: true }),
        { onClose },
        am,
    );

    expect(res).toBe("doAction-result");
    expect(am.__calls.doAction[0].options.onClose).toBe(onClose);
});

test("a handling handler runs onClose when there is no close flag", async () => {
    defineReportHandler("re_short_onclose", () => "handled");
    const am = makeFakeAm();
    let closed = 0;

    const res = await executeReportAction(
        makeReportAction(),
        { onClose: () => closed++ },
        am,
    );

    expect(closed).toBe(1);
    expect(res).toBe("handled");
    expect(am.__calls.doAction).toEqual([]);
});

test("an unknown report type is reported and does nothing else", async () => {
    const errors = [];
    patchWithCleanup(console, { error: (...args) => errors.push(args[0]) });
    const downloads = patchDownload();
    const am = makeFakeAm();

    const res = await executeReportAction(
        makeReportAction({ report_type: "qweb-something-else" }),
        {},
        am,
    );

    expect(res).toBe(undefined);
    expect(errors[0]).toInclude("qweb-something-else");
    expect(downloads).toEqual([]);
    expect(am.__calls.updateUI).toEqual([]);
    expect(am.__calls.ui).toEqual([]);
});

test("an unhandled report_type still settles the caller's onClose", async () => {
    const am = makeFakeAm();
    patchWithCleanup(console, { error: () => expect.step("console.error") });

    let closed = 0;
    await executeReportAction(
        { ...makeReportAction(), report_type: "qweb-something-else" },
        { onClose: () => closed++ },
        am,
    );

    expect.verifySteps(["console.error"]);
    expect(closed).toBe(1);
    expect(am.__calls.doAction).toHaveLength(0);
});

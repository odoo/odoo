import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { allowTranslations, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { printJobs, } from "@printer/print_action_handler";
import { registry } from "@web/core/registry";

describe.current.tags("headless");

const notificationsReceived = [];
const actionsExecuted = [];

beforeEach(() => {
    notificationsReceived.length = 0;
    actionsExecuted.length = 0;
});

const mockReportId = 42;


const makeEposPrinter = (overrides = {}) => ({
    type: "epos",
    ip_address: "1.2.3.4",
    ...overrides,
});

const makeZplPrinter = (overrides = {}) => ({
    type: "zpl",
    ip_address: "5.6.7.8",
    ...overrides,
});

const makeEposJob = (overrides = {}) => ({
    type: "epos",
    report: btoa("hello printer"),
    ...overrides,
});

const makeZplJob = (overrides = {}) => ({
    type: "zpl",
    report: btoa("^XA^XZ"),
    ...overrides,
});

const makeMockServices = () => ({
    notification: {
        add: (title, opts) => {
            notificationsReceived.push({ title, opts });
            return () => {};
        },
    },
});


const getHandler = () =>
    registry.category("ir.actions.report handlers").get("print_action_handler");

const makeMockEnv = (printerSettings = null) => ({
    services: {
        ...makeMockServices(),
        report_printers_cache: {
            getPrinterSettingsForReport: async () => printerSettings,
        },
        action: {
            doAction: async (a) => actionsExecuted.push(a),
        },
    },
});

describe("printJobs", () => {
    test("sends an epos job to the correct endpoint and resolves", async () => {
        const fetchCalls = [];
        patchWithCleanup(window, {
            fetch: async (url, params) => {
                fetchCalls.push({ url, params });
                return { text: async () => `<response success="true" code=""/>`, ok: true };
            },
        });

        const printer = makeEposPrinter();
        const services = makeMockServices();
        await printJobs(printer, [makeEposJob()], services);

        expect(fetchCalls).toHaveLength(1);
        expect(fetchCalls[0].url).toMatch(/epos\/service\.cgi/);
        expect(notificationsReceived).toHaveLength(0);
    });

    test("sends a zpl job to /pstprnt in no-cors mode", async () => {
        const fetchCalls = [];
        patchWithCleanup(window, {
            fetch: async (url, params) => {
                fetchCalls.push({ url, params });
                return {};
            },
        });

        const printer = makeZplPrinter();
        const services = makeMockServices();
        await printJobs(printer, [makeZplJob()], services);

        expect(fetchCalls).toHaveLength(1);
        expect(fetchCalls[0].url).toBe(`http://${printer.ip_address}/pstprnt`);
        expect(fetchCalls[0].params.mode).toBe("no-cors");
        expect(notificationsReceived).toHaveLength(0);
    });

    test("skips jobs whose type does not match the printer", async () => {
        const fetchCalls = [];
        patchWithCleanup(window, {
            fetch: async (url) => {
                fetchCalls.push(url);
                return {};
            },
        });

        const printer = makeZplPrinter();
        const services = makeMockServices();
        await printJobs(printer, [makeEposJob()], services);

        expect(fetchCalls).toHaveLength(0);
        expect(notificationsReceived).toHaveLength(0);
    });

    test("shows a danger notification when epos returns a non-success response", async () => {
        allowTranslations();
        patchWithCleanup(window, {
            fetch: async () => ({ text: async () => `<response success="false" code="ERROR_GENERAL"/>` }),
        });

        const printer = makeEposPrinter();
        const services = makeMockServices();
        await printJobs(printer, [makeEposJob()], services);

        expect(notificationsReceived).toHaveLength(1);
        expect(notificationsReceived[0].opts.type).toBe("danger");
    });

    test("shows a danger notification when fetch throws", async () => {
        allowTranslations();
        patchWithCleanup(window, {
            fetch: async () => { throw new Error("network error"); },
        });

        const printer = makeEposPrinter();
        const services = makeMockServices();
        await printJobs(printer, [makeEposJob()], services);

        expect(notificationsReceived).toHaveLength(1);
        expect(notificationsReceived[0].opts.type).toBe("danger");
    });

    test("retries on ERROR_WAIT_EJECT before succeeding", async () => {
        let callCount = 0;
        patchWithCleanup(window, {
            fetch: async () => {
                callCount++;
                const success = callCount > 1;
                const code = success ? "" : "ERROR_WAIT_EJECT";
                return { text: async () => `<response success="${success}" code="${code}"/>` };
            },
        });

        const printer = makeEposPrinter();
        const services = makeMockServices();
        await printJobs(printer, [makeEposJob()], services);

        expect(callCount).toBeGreaterThan(1);
        expect(notificationsReceived).toHaveLength(0);
    });

    test("processes multiple jobs of matching type in sequence", async () => {
        const fetchCalls = [];
        patchWithCleanup(window, {
            fetch: async (url) => {
                fetchCalls.push(url);
                return { text: async () => `<response success="true" code=""/>` };
            },
        });

        const printer = makeEposPrinter();
        const services = makeMockServices();
        await printJobs(printer, [makeEposJob(), makeEposJob()], services);

        expect(fetchCalls).toHaveLength(2);
        expect(notificationsReceived).toHaveLength(0);
    });
});


describe("printActionHandler", () => {
    const makeAction = (overrides = {}) => ({
        id: mockReportId,
        context: {
            report_id: mockReportId,
            jobs: [makeEposJob()],
            active_ids: [1, 2, 3],
        },
        data: {},
        ...overrides,
    });

    test("returns false when there are no jobs", async () => {
        const env = makeMockEnv();
        const action = makeAction({ context: { report_id: mockReportId, jobs: [] } });
        const result = await getHandler()(action, {}, env);

        expect(result).not.toBe(true);
    });

    test("returns false when jobs is undefined", async () => {
        const env = makeMockEnv();
        const action = makeAction({ context: { report_id: mockReportId } });
        const result = await getHandler()(action, {}, env);

        expect(result).not.toBe(true);
    });

    test("returns false when getPrinterSettingsForReport returns no selectedPrinters", async () => {
        const env = makeMockEnv({ skipDialog: true }); // selectedPrinters absent
        const result = await getHandler()(makeAction(), {}, env);

        expect(result).not.toBe(true);
    });

    test("returns false when getPrinterSettingsForReport returns null", async () => {
        const env = makeMockEnv(null);
        const result = await getHandler()(makeAction(), {}, env);

        expect(result).not.toBe(true);
    });

    test("returns true and calls onClose after a successful print", async () => {
        patchWithCleanup(window, {
            fetch: async () => ({ text: async () => `<response success="true" code=""/>` }),
        });

        const env = makeMockEnv({
            selectedPrinters: [makeEposPrinter()],
        });
        const closed = [];

        const result = await getHandler()(makeAction(), { onClose: () => closed.push(true) }, env);

        expect(result).toBe(true);
        expect(closed).toHaveLength(1);
    });

    test("prints to every selected printer", async () => {
        const fetchCalls = [];
        patchWithCleanup(window, {
            fetch: async (url) => {
                fetchCalls.push(url);
                return { text: async () => `<response success="true" code=""/>` };
            },
        });

        const env = makeMockEnv({
            selectedPrinters: [makeEposPrinter({ ip_address: "1.1.1.1" }), makeEposPrinter({ ip_address: "2.2.2.2" })],
        });

        await getHandler()(makeAction(), {}, env);

        const hosts = fetchCalls.map((u) => new URL(u).hostname);
        expect(hosts).toInclude("1.1.1.1");
        expect(hosts).toInclude("2.2.2.2");
    });
});

import { describe, destroy, expect, test } from "@odoo/hoot";
import { animationFrame, Deferred } from "@odoo/hoot-mock";
import { TestEPos } from "@point_of_sale/backend/test_epos/test_epos";
import {
    mockService,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

for (const preset of ["desktop", "mobile"]) {
    describe(preset, () => {
        describe.current.tags(preset);

        async function mountPrinter(
            data = { epson_printer_ip: "printer.local" },
            useLna = false,
        ) {
            patchWithCleanup(odoo, { use_lna: false });
            mockService("orm", { call: async () => ({ use_lna: useLna }) });
            const notifications = [];
            mockService("notification", {
                add: (message, options) => notifications.push({ message, ...options }),
            });
            const printer = await mountWithCleanup(TestEPos, {
                props: { record: { data } },
            });
            return { printer, notifications };
        }

        test("repeated clicks produce one request and unlock after completion", async () => {
            const response = new Deferred();
            let requests = 0;
            patchWithCleanup(window, {
                fetch: () => {
                    requests++;
                    return response;
                },
            });
            const { printer, notifications } = await mountPrinter();
            const printing = printer.onClick();
            // Do not await the duplicate: a broken implementation starts a second fetch.
            const duplicate = printer.onClick();
            await animationFrame();
            expect(requests).toBe(1);
            expect("button").toHaveProperty("disabled", true);
            response.resolve(new Response('<response success="true" code=""/>'));
            await Promise.all([printing, duplicate]);
            expect(notifications).toHaveLength(1);
            expect(notifications[0].type).toBe("info");
            await animationFrame();
            expect("button").toHaveProperty("disabled", false);
        });

        for (const body of [
            '<response success="true"/>',
            '<response success="true" code=""/>',
        ]) {
            test(`successful printer response: ${body}`, async () => {
                patchWithCleanup(window, { fetch: async () => new Response(body) });
                const { printer, notifications } = await mountPrinter();
                await printer.onClick();
                expect(notifications[0].type).toBe("info");
            });
        }

        for (const [body, status] of [
            ['<response success="false" code="EPTR_COVER_OPEN"/>', 200],
            ['<response success="false" code="toString"/>', 200],
            ["<html>not a printer</html>", 200],
            ['<response success="true" code=""/>', 503],
        ]) {
            test(`invalid printer response: ${status} ${body}`, async () => {
                patchWithCleanup(window, {
                    fetch: async () => new Response(body, { status }),
                });
                const { printer, notifications } = await mountPrinter();
                await printer.onClick();
                expect(notifications).toHaveLength(1);
                expect(notifications[0].type).toBe("warning");
                expect(typeof notifications[0].message).not.toBe("function");
                expect(String(notifications[0].message)).toInclude(
                    body.includes("EPTR_COVER_OPEN")
                        ? "Printer cover is open"
                        : "Failed to print a test receipt",
                );
            });
        }

        test("a missing printer address does not send a request", async () => {
            patchWithCleanup(window, {
                fetch: () => {
                    throw new Error("unexpected request");
                },
            });
            const { printer, notifications } = await mountPrinter({
                epson_printer_ip: false,
            });
            await printer.onClick();
            expect(notifications[0].type).toBe("danger");
        });

        test("settings field and fetch failure remain retryable", async () => {
            let requests = 0;
            patchWithCleanup(window, {
                fetch: async (address) => {
                    expect(address).toInclude(
                        "//settings.local/cgi-bin/epos/service.cgi",
                    );
                    requests++;
                    throw new TypeError("offline");
                },
            });
            const { printer, notifications } = await mountPrinter({
                pos_epson_printer_ip: "settings.local",
            });
            await printer.onClick();
            await printer.onClick();
            expect(requests).toBe(2);
            expect(notifications.map(({ type }) => type)).toEqual(["danger", "danger"]);
        });

        test("denied local network permission does not print", async () => {
            patchWithCleanup(navigator.permissions, {
                query: async () => ({ state: "denied" }),
            });
            let requests = 0;
            patchWithCleanup(window, {
                fetch: async () => {
                    requests++;
                },
            });
            const { printer } = await mountPrinter(undefined, true);
            await printer.onClick();
            expect(requests).toBe(0);
        });

        test("closing the view cancels its pending print without an error notification", async () => {
            let signal;
            patchWithCleanup(window, {
                fetch: (address, params) => {
                    signal = params.signal;
                    return new Promise((resolve, reject) => {
                        signal.addEventListener("abort", () => reject(signal.reason));
                    });
                },
            });
            const { printer, notifications } = await mountPrinter();
            const pending = printer.onClick();
            destroy(printer);
            await pending;
            expect(signal.aborted).toBe(true);
            expect(notifications).toHaveLength(0);
        });

        test("print timeout starts after local network permission resolves", async () => {
            const permission = new Deferred();
            patchWithCleanup(AbortSignal, {
                timeout: (ms) => {
                    expect(ms).toBe(15000);
                    expect.step("timeout");
                    return new AbortController().signal;
                },
            });
            patchWithCleanup(window, {
                fetch: async (address, params) => {
                    expect(params.targetAddressSpace).toBe("loopback");
                    return new Response('<response success="true" code=""/>');
                },
            });
            const { printer } = await mountPrinter(
                { epson_printer_ip: "localhost" },
                true,
            );
            patchWithCleanup(navigator.permissions, { query: () => permission });
            const pending = printer.onClick();
            expect.verifySteps([]);
            permission.resolve({ state: "granted" });
            await pending;
            expect.verifySteps(["timeout"]);
        });
    });
}

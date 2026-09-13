import { Deferred, expect, microTick, test } from "@odoo/hoot";
import { Component, xml } from "@odoo/owl";
import { PosPrinterService } from "@point_of_sale/app/services/pos_printer_service";
import { PrinterService } from "@point_of_sale/app/services/printer_service";
import {
    allowTranslations,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

import { definePosModels } from "../data/generate_model_definitions.js";

definePosModels();

test("browser printing remains pending until the receipt is mounted and printed", async () => {
    const mounted = new Deferred();
    const receipt = document.createElement("div");
    const printer = new PrinterService(
        {},
        {
            renderer: {
                toHtml: async () => receipt,
                whenMounted: async ({ callback }) => {
                    await mounted;
                    return callback(receipt);
                },
            },
        },
    );
    patchWithCleanup(window, { print: () => expect.step("printed") });
    let settled = false;
    const printing = printer.print(
        function Receipt() {},
        {},
        { webPrintFallback: true },
    );
    printing.then(() => {
        settled = true;
    });
    await microTick();
    expect(settled).toBe(false);
    expect(printer.state.isPrinting).toBe(true);
    mounted.resolve();
    expect(await printing).toBe(true);
    expect(printer.state.isPrinting).toBe(false);
    expect.verifySteps(["printed"]);
});

test("POS reports an asynchronous browser printing failure", async () => {
    const dialogs = [];
    const printer = new PosPrinterService(
        {},
        {
            hardware_proxy: { printer: null },
            dialog: { add: (component, props) => dialogs.push(props) },
            renderer: { whenMounted: ({ callback, el }) => callback(el) },
        },
    );
    patchWithCleanup(window, {
        print: () => {
            throw new Error("Unsupported");
        },
    });
    expect(await printer.printWeb(document.createElement("div"))).toBe(false);
    expect(dialogs).toHaveLength(1);
    expect(dialogs[0].title).toBe("Printing is not supported on some browsers");
});

test("printing state stays active until every concurrent job finishes", async () => {
    const jobs = [new Deferred(), new Deferred()];
    let nextJob = 0;
    const printer = new PrinterService(
        {},
        {
            renderer: { toHtml: async () => document.createElement("div") },
        },
    );
    printer.setPrinter({ printReceipt: () => jobs[nextJob++] });
    const first = printer.print(function Receipt() {}, {});
    const second = printer.print(function Receipt() {}, {});
    await microTick();
    jobs[0].resolve({ successful: true });
    await first;
    expect(printer.state.isPrinting).toBe(true);
    jobs[1].resolve({ successful: true });
    await second;
    expect(printer.state.isPrinting).toBe(false);
});

test("a rejected print does not clear another job's busy state", async () => {
    const jobs = [new Deferred(), new Deferred()];
    let nextJob = 0;
    const printer = new PrinterService(
        {},
        { renderer: { toHtml: () => jobs[nextJob++] } },
    );
    printer.setPrinter({ printReceipt: async () => ({ successful: true }) });
    const first = printer.print(function Receipt() {}, {}).catch((error) => error);
    const second = printer.print(function Receipt() {}, {});
    jobs[0].reject(new Error("Render failed"));
    expect((await first).message).toBe("Render failed");
    expect(printer.state.isPrinting).toBe(true);
    jobs[1].resolve(document.createElement("div"));
    await second;
    expect(printer.state.isPrinting).toBe(false);
});

test("POS setup runs once even when extended", () => {
    let setups = 0;
    class ExtendedPrinter extends PosPrinterService {
        setup() {
            super.setup(...arguments);
            setups++;
        }
    }
    const printer = new ExtendedPrinter(
        {},
        {
            renderer: {},
            hardware_proxy: { printer: null },
            dialog: {},
        },
    );
    expect(setups).toBe(1);
    expect(printer.state.isPrinting).toBe(false);
});

test("concurrent browser jobs print their own rendered receipt", async () => {
    allowTranslations();
    const comp = await mountWithCleanup("none");
    const printer = new PrinterService({}, { renderer: comp.env.services.renderer });
    class Receipt extends Component {
        static props = ["number"];
        static template = xml`<div t-esc="props.number"/>`;
    }
    patchWithCleanup(window, {
        print() {
            expect.step(document.querySelector(".render-container").textContent);
        },
    });
    const results = await Promise.all(
        ["first", "second", "third"].map((number) =>
            printer.print(Receipt, { number }, { webPrintFallback: true }),
        ),
    );
    expect(results).toEqual([true, true, true]);
    expect.verifySteps(["first", "second", "third"]);
    expect(printer.state.isPrinting).toBe(false);
});

import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { onRpc } from "@web/../tests/web_test_helpers";
import { jsToPyLocale } from "@web/core/l10n/utils";
import { user } from "@web/core/user";
import { getFilledSelfOrder, setupSelfPosEnv } from "../utils";
import { definePosSelfModels } from "../data/generate_model_definitions";

definePosSelfModels();

const CHANGE_RECEIPT_ROUTE = "/pos-self-order/kiosk/change-receipt";
const CLIENT_IMAGE = "client-image";

function serverImage(width = 515) {
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = 100;
    return canvas.toDataURL("image/jpeg").split(",")[1];
}

function addPrinter(store, name, paperSize, { successful = true } = {}) {
    const printer = store.models["pos.printer"].create({
        name,
        printer_type: "epson_epos",
        use_type: "preparation",
        product_categories_ids: store.models["pos.category"].getAll(),
    });
    printer.paper_size = paperSize;
    printer._instance = {
        print: async (data) => {
            store.printed.push({ printer: name, data });
            return { successful, message: { body: "Error" } };
        },
    };
    return printer;
}

async function setupKiosk({ defaultUserLang = "fr_FR", failing = [] } = {}) {
    const store = await setupSelfPosEnv("kiosk");
    const order = await getFilledSelfOrder(store);
    store.printed = [];
    store.config._default_user_lang = defaultUserLang;
    store.config.preparation_printer_ids = [
        addPrinter(store, "Kitchen", "80", { successful: !failing.includes("Kitchen") }),
        addPrinter(store, "Bar", "80", { successful: !failing.includes("Bar") }),
        addPrinter(store, "Small", "58"),
        addPrinter(store, "Label", "label"),
    ];
    Object.assign(store.ticketPrinter, {
        generateIframe: async () => {},
        setIframeSizeFromPrinter: async () => {},
        generateImage: async () => CLIENT_IMAGE,
    });
    return { store, order };
}

const receiptsOf = (store) =>
    Object.fromEntries(
        store.config.preparation_printer_ids
            .filter((printer) => printer.paper_size !== "label")
            .map((printer) => [printer.id, [serverImage()]])
    );

const printedBy = (store, source) =>
    store.printed
        .filter(({ data }) =>
            source === "client"
                ? data === CLIENT_IMAGE || typeof data === "string"
                : data instanceof HTMLCanvasElement
        )
        .map(({ printer }) => printer);

describe("printOrderChanges", () => {
    let rpcCalls;
    beforeEach(() => {
        rpcCalls = 0;
    });

    test("kiosk in the default user language keeps the kiosk rendering", async () => {
        const { store, order } = await setupKiosk({ defaultUserLang: jsToPyLocale(user.lang) });
        onRpc(`${CHANGE_RECEIPT_ROUTE}/${order.id}`, () => {
            rpcCalls++;
        });

        await store.ticketPrinter.printOrderChanges({ order });

        expect(rpcCalls).toBe(0);
        expect(printedBy(store, "client")).toEqual(["Kitchen", "Bar", "Small", "Label"]);
    });

    test("other language prints the 80mm tickets from the server, others stay on the kiosk", async () => {
        const { store, order } = await setupKiosk();
        onRpc(`${CHANGE_RECEIPT_ROUTE}/${order.id}`, () => ({
            receipts: receiptsOf(store),
        }));

        await store.ticketPrinter.printOrderChanges({ order });

        expect(printedBy(store, "server")).toEqual(["Kitchen", "Bar"]);
        expect(printedBy(store, "client")).toEqual(["Small", "Label"]);
    });

    test("printer refusing the server ticket falls back alone on the kiosk rendering", async () => {
        const { store, order } = await setupKiosk({ failing: ["Bar"] });
        onRpc(`${CHANGE_RECEIPT_ROUTE}/${order.id}`, () => ({
            receipts: receiptsOf(store),
        }));

        await store.ticketPrinter.printOrderChanges({ order });

        expect(printedBy(store, "server")).toEqual(["Kitchen", "Bar"]);
        expect(printedBy(store, "client").sort()).toEqual(["Bar", "Label", "Small"]);
    });

    test("server error falls back on the kiosk rendering for every printer", async () => {
        const { store, order } = await setupKiosk();
        onRpc(`${CHANGE_RECEIPT_ROUTE}/${order.id}`, () => {
            throw new Error("Server down");
        });

        await store.ticketPrinter.printOrderChanges({ order });

        expect(printedBy(store, "server")).toEqual([]);
        expect(printedBy(store, "client")).toEqual(["Kitchen", "Bar", "Small", "Label"]);
    });

    test("only prints on the requested printers", async () => {
        const { store, order } = await setupKiosk();
        const [kitchen] = store.config.preparation_printer_ids;
        onRpc(`${CHANGE_RECEIPT_ROUTE}/${order.id}`, () => ({
            receipts: receiptsOf(store),
        }));

        await store.ticketPrinter.printOrderChanges({ order, printers: [kitchen] });

        expect(store.printed.map(({ printer }) => printer)).toEqual(["Kitchen"]);
    });

    test("printers matching no category of the order print nothing", async () => {
        const { store, order } = await setupKiosk();
        const [kitchen, bar, small, label] = store.config.preparation_printer_ids;
        const unmatched = store.models["pos.category"].create({ id: 999, name: "Unmatched" });
        for (const printer of [kitchen, small, label]) {
            printer.product_categories_ids = [unmatched];
        }
        onRpc(`${CHANGE_RECEIPT_ROUTE}/${order.id}`, () => ({
            receipts: { [bar.id]: [serverImage()] },
        }));

        await store.ticketPrinter.printOrderChanges({ order });

        expect(store.printed.map(({ printer }) => printer)).toEqual(["Bar"]);
    });

    test("kiosk without 80mm printer prints without calling the server", async () => {
        const { store, order } = await setupKiosk();
        store.config.preparation_printer_ids = store.config.preparation_printer_ids.slice(-2);
        onRpc(`${CHANGE_RECEIPT_ROUTE}/${order.id}`, () => {
            rpcCalls++;
            return { receipts: {} };
        });

        await store.ticketPrinter.printOrderChanges({ order });

        expect(rpcCalls).toBe(0);
        expect(printedBy(store, "client")).toEqual(["Small", "Label"]);
    });

    test("label printer matching no category of the order prints nothing", async () => {
        const { store, order } = await setupKiosk();
        const label = store.config.preparation_printer_ids.at(-1);
        const unmatched = store.models["pos.category"].create({ id: 999, name: "Unmatched" });
        label.product_categories_ids = [unmatched];
        store.config.preparation_printer_ids = [label];
        onRpc(`${CHANGE_RECEIPT_ROUTE}/${order.id}`, () => ({ receipts: {} }));

        await store.ticketPrinter.printOrderChanges({ order });

        expect(store.printed).toEqual([]);
    });

    describe("80mm and label printers", () => {
        async function setupReceiptAndLabelKiosk(options) {
            const { store, order } = await setupKiosk(options);
            const [kitchen, , , label] = store.config.preparation_printer_ids;
            store.config.preparation_printer_ids = [kitchen, label];
            return { store, order, kitchen, label };
        }

        const mockServerReceipts = (order, getReceipts) =>
            onRpc(`${CHANGE_RECEIPT_ROUTE}/${order.id}`, () => {
                rpcCalls++;
                return { receipts: getReceipts() };
            });

        test("each printer prints once, 80mm from the server and label as ZPL", async () => {
            const { store, order, kitchen } = await setupReceiptAndLabelKiosk();
            mockServerReceipts(order, () => ({ [kitchen.id]: [serverImage()] }));

            await store.ticketPrinter.printOrderChanges({ order });

            expect(rpcCalls).toBe(1);
            expect(printedBy(store, "server")).toEqual(["Kitchen"]);
            expect(printedBy(store, "client")).toEqual(["Label"]);
            expect(store.printed.find(({ printer }) => printer === "Label").data).toInclude("^XA");
        });

        test("label never prints an image sent by the server", async () => {
            const { store, order, kitchen, label } = await setupReceiptAndLabelKiosk();
            mockServerReceipts(order, () => ({
                [kitchen.id]: [serverImage()],
                [label.id]: [serverImage()],
            }));

            await store.ticketPrinter.printOrderChanges({ order });

            expect(printedBy(store, "server")).toEqual(["Kitchen"]);
            expect(printedBy(store, "client")).toEqual(["Label"]);
        });

        test("every image of the 80mm printer is printed", async () => {
            const { store, order, kitchen } = await setupReceiptAndLabelKiosk();
            mockServerReceipts(order, () => ({ [kitchen.id]: [serverImage(), serverImage()] }));

            await store.ticketPrinter.printOrderChanges({ order });

            expect(printedBy(store, "server")).toEqual(["Kitchen", "Kitchen"]);
            expect(printedBy(store, "client")).toEqual(["Label"]);
        });

        test("failing 80mm falls back on the kiosk and label prints once", async () => {
            const { store, order, kitchen } = await setupReceiptAndLabelKiosk({
                failing: ["Kitchen"],
            });
            mockServerReceipts(order, () => ({ [kitchen.id]: [serverImage()] }));

            await store.ticketPrinter.printOrderChanges({ order });

            expect(printedBy(store, "server")).toEqual(["Kitchen"]);
            expect(printedBy(store, "client").sort()).toEqual(["Kitchen", "Label"]);
        });

        test("server error prints both printers once on the kiosk", async () => {
            const { store, order } = await setupReceiptAndLabelKiosk();
            onRpc(`${CHANGE_RECEIPT_ROUTE}/${order.id}`, () => {
                throw new Error("Server down");
            });

            await store.ticketPrinter.printOrderChanges({ order });

            expect(printedBy(store, "server")).toEqual([]);
            expect(printedBy(store, "client")).toEqual(["Kitchen", "Label"]);
        });

        test("80mm the server failed to render falls back on the kiosk", async () => {
            const { store, order, kitchen } = await setupReceiptAndLabelKiosk();
            mockServerReceipts(order, () => ({ [kitchen.id]: [] }));

            await store.ticketPrinter.printOrderChanges({ order });

            expect(printedBy(store, "server")).toEqual([]);
            expect(printedBy(store, "client").sort()).toEqual(["Kitchen", "Label"]);
        });

        test("label still prints when the server has nothing for the 80mm", async () => {
            const { store, order } = await setupReceiptAndLabelKiosk();
            mockServerReceipts(order, () => ({}));

            await store.ticketPrinter.printOrderChanges({ order });

            expect(printedBy(store, "server")).toEqual([]);
            expect(printedBy(store, "client")).toEqual(["Label"]);
        });
    });
});

describe("base64ToCanvas", () => {
    test("server image width is reduced to a multiple of 8", async () => {
        const { store } = await setupKiosk();

        for (const [width, expectedWidth] of [
            [515, 512],
            [512, 512],
        ]) {
            const canvas = await store.ticketPrinter.base64ToCanvas(serverImage(width));

            expect(canvas.width).toBe(expectedWidth);
            expect(canvas.height).toBe(100);
        }
    });
});

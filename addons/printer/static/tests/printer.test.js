import { advanceTime, animationFrame, beforeEach, expect, test } from "@odoo/hoot";
import {
    contains,
    defineModels,
    fields,
    getService,
    models,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

import { download } from "@web/core/network/download";
import { WebClient } from "@web/webclient/webclient";
import { getLinkedPrinters, setLinkedPrinters } from "@printer/linked_printers";
import { getEposPrintXml } from "@printer/printers/epos_printer";

class PrinterPrinter extends models.Model {
    _name = "printer.printer";

    name = fields.Char();
    kind = fields.Selection({
        selection: [
            ["zpl", "ZPL"],
            ["epos", "ePOS"],
        ],
    });
    address = fields.Char();

    _records = [
        { id: 1, name: "ZPL - Packing station", kind: "zpl", address: "192.168.1.20" },
        { id: 2, name: "ePOS - Shipping desk", kind: "epos", address: "epson-1.local:8080/" },
    ];
}

defineModels([PrinterPrinter]);

const ZPL_URL = "http://192.168.1.20/pstprnt";
const EPOS_URL = "http://epson-1.local:8080/cgi-bin/epos/service.cgi";
const RASTER = { width: 576, height: 2, raster: "AAAA" };

function reportAction(printerIds = [1, 2]) {
    return {
        type: "ir.actions.report",
        name: "Shipping Labels",
        report_name: "stock_printer.report_shipping_labels",
        report_type: "qweb-pdf",
        context: { active_ids: [7] },
        printer_ids: printerIds,
    };
}

function eposResponse(success, code = "") {
    return new Response(
        `<?xml version="1.0" encoding="utf-8"?>
        <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body>
            <response success="${success}" code="${code}" status="251658262"
                xmlns="http://www.epson-pos.com/schemas/2011/03/epos-print"/>
        </s:Body></s:Envelope>`
    );
}

beforeEach(() => {
    localStorage.clear();
    patchWithCleanup(download, {
        _download: (options) => {
            expect.step("download");
            return Promise.resolve();
        },
    });
    onRpc("/report/get_pdf_engine_state", () => "ok");
    onRpc("/printer/report_documents", async (request) => {
        const { params } = await request.json();
        expect.step(`render for printers ${params.printer_ids}`);
        expect(params.report_name).toBe("stock_printer.report_shipping_labels");
        expect(params.res_ids).toEqual([7]);
        return { zpl: ["^XA^FDfirst^FS^XZ", "^XA^FDsecond^FS^XZ"], epos: [RASTER] };
    });
    onRpc(ZPL_URL, async (request) => {
        expect.step(`zpl: ${await request.text()}`);
        return new Response("");
    });
    onRpc(EPOS_URL, async (request) => {
        expect.step(`epos: ${await request.text()}`);
        return eposResponse(true);
    });
});

test("report without printers is downloaded", async () => {
    await mountWithCleanup(WebClient);
    await getService("action").doAction(reportAction([]));
    expect(".modal").toHaveCount(0);
    expect.verifySteps(["download"]);
});

test("first print asks which printers to use, and remembers the choice", async () => {
    await mountWithCleanup(WebClient);
    getService("action").doAction(reportAction());
    await animationFrame();
    expect(".modal .modal-title").toHaveText("Print Shipping Labels");
    expect(".modal .o_printer_dialog_printers .form-check-label").toHaveText(
        ["ZPL - Packing station", "ePOS - Shipping desk"].join("")
    );

    // At least one printer must be chosen.
    await contains(".modal-footer .btn-primary").click();
    expect(".o_printer_dialog_error").toHaveText("Select at least one printer");
    expect(".modal").toHaveCount(1);

    await contains(".modal input[name='printer_1']").check();
    expect(".o_printer_dialog_error").toHaveCount(0);
    await contains(".modal-footer .btn-primary").click();
    await animationFrame();
    expect(".modal").toHaveCount(0);
    expect.verifySteps([
        "render for printers 1",
        "zpl: ^XA^FDfirst^FS^XZ",
        "zpl: ^XA^FDsecond^FS^XZ",
    ]);
    expect(getLinkedPrinters("stock_printer.report_shipping_labels")).toEqual({
        reportName: "stock_printer.report_shipping_labels",
        displayName: "Shipping Labels",
        printerIds: [1],
        skipDialog: false,
    });

    // Next time, the dialog opens again, with the remembered printers selected.
    getService("action").doAction(reportAction());
    await animationFrame();
    expect(".modal input[name='printer_1']").toBeChecked();
    expect(".modal input[name='printer_2']").not.toBeChecked();
    expect(".modal input[name='skip_dialog']").not.toBeChecked();
});

test("do not ask me again", async () => {
    await mountWithCleanup(WebClient);
    getService("action").doAction(reportAction());
    await animationFrame();
    await contains(".modal input[name='printer_1']").check();
    await contains(".modal input[name='printer_2']").check();
    await contains(".modal input[name='skip_dialog']").check();
    await contains(".modal-footer .btn-primary").click();
    await animationFrame();
    expect.verifySteps([
        "render for printers 1,2",
        "zpl: ^XA^FDfirst^FS^XZ",
        "zpl: ^XA^FDsecond^FS^XZ",
        `epos: ${getEposPrintXml(RASTER)}`,
    ]);

    // Next time, the document goes to the printers without asking.
    await getService("action").doAction(reportAction());
    expect(".modal").toHaveCount(0);
    expect.verifySteps([
        "render for printers 1,2",
        "zpl: ^XA^FDfirst^FS^XZ",
        "zpl: ^XA^FDsecond^FS^XZ",
        `epos: ${getEposPrintXml(RASTER)}`,
    ]);
});

test("remembered printers that are no longer on the report are asked again", async () => {
    setLinkedPrinters({
        reportName: "stock_printer.report_shipping_labels",
        displayName: "Shipping Labels",
        printerIds: [2],
        skipDialog: true,
    });
    await mountWithCleanup(WebClient);
    getService("action").doAction(reportAction([1]));
    await animationFrame();
    expect(".modal").toHaveCount(1);
    expect(".modal input[name='printer_1']").not.toBeChecked();
});

test("closing the dialog downloads the report", async () => {
    await mountWithCleanup(WebClient);
    getService("action").doAction(reportAction());
    await animationFrame();
    await contains(".modal-footer .btn-secondary").click();
    await animationFrame();
    expect(".modal").toHaveCount(0);
    expect.verifySteps(["download"]);
    expect(getLinkedPrinters("stock_printer.report_shipping_labels")).toBe(null);
});

test("ePOS printer: SOAP envelope", async () => {
    expect(getEposPrintXml({ width: 576, height: 3, raster: "AQID" })).toBe(
        `<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body>` +
            `<epos-print xmlns="http://www.epson-pos.com/schemas/2011/03/epos-print">` +
            `<image width="576" height="3" align="center">AQID</image><cut type="feed" />` +
            `</epos-print></s:Body></s:Envelope>`
    );
});

test("ePOS printer: errors are notified and the label waiting to be taken out is printed again", async () => {
    setLinkedPrinters({
        reportName: "stock_printer.report_shipping_labels",
        displayName: "Shipping Labels",
        printerIds: [2],
        skipDialog: true,
    });
    onRpc("/printer/report_documents", () => ({ epos: [RASTER, RASTER, RASTER] }));
    const responses = [
        eposResponse(false, "ERROR_WAIT_EJECT"),
        eposResponse(true),
        eposResponse(false, "EPTR_COVER_OPEN"),
        eposResponse(true),
    ];
    onRpc(EPOS_URL, () => {
        expect.step("epos");
        return responses.shift();
    });
    await mountWithCleanup(WebClient);
    const printing = getService("action").doAction(reportAction());
    await animationFrame();
    expect.verifySteps(["epos"]);
    // The first label waits to be taken out: sent again a second later.
    await advanceTime(1000);
    await animationFrame();
    // The second one fails, printing goes on with the third one.
    expect.verifySteps(["epos", "epos", "epos"]);
    await printing;
    expect(".o_notification").toHaveCount(1);
    expect(".o_notification").toHaveText(
        /The document could not be printed on ePOS - Shipping desk. Error code: EPTR_COVER_OPEN/
    );
});

test("ZPL printer not reachable", async () => {
    setLinkedPrinters({
        reportName: "stock_printer.report_shipping_labels",
        displayName: "Shipping Labels",
        printerIds: [1],
        skipDialog: true,
    });
    onRpc(ZPL_URL, () => {
        throw new TypeError("Failed to fetch");
    });
    await mountWithCleanup(WebClient);
    await getService("action").doAction(reportAction());
    await animationFrame();
    expect(".o_notification").toHaveCount(2);
    expect(".o_notification:first").toHaveText(/Error code: PRINTER_NOT_REACHABLE/);
});

test("reset linked printers", async () => {
    setLinkedPrinters({
        reportName: "stock_printer.report_shipping_labels",
        displayName: "Shipping Labels",
        printerIds: [1],
        skipDialog: true,
    });
    setLinkedPrinters({
        reportName: "product.report_product_label_zpl",
        displayName: "Product Label (ZPL)",
        printerIds: [2],
        skipDialog: false,
    });
    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        type: "ir.actions.client",
        tag: "printer.reset_linked_printers",
    });
    expect(".o_printer_reset_linked_printers tr").toHaveCount(2);
    expect(".o_printer_reset_linked_printers tr:first td:first").toHaveText("Product Label (ZPL)");

    await contains(".o_printer_reset_linked_printers tr:last button").click();
    expect(".o_printer_reset_linked_printers tr").toHaveCount(1);
    expect(getLinkedPrinters("stock_printer.report_shipping_labels")).toBe(null);
    expect(getLinkedPrinters("product.report_product_label_zpl")).not.toBe(null);

    await contains(".o_printer_reset_linked_printers tr button").click();
    expect(".o_printer_reset_linked_printers_empty").toHaveCount(1);
});

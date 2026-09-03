import { expect, test, describe } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { contains, mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";
import { PrintReceipt } from "@point_of_sale/backend/print_receipt/print_receipt";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

const PRINTER_URL = "https://0.0.0.0/cgi-bin/epos/service.cgi";
const FALLBACK_BUTTON = ".o_notification_buttons button:contains('Print with the browser')";

let printers = [];

function makePrinter(id, name) {
    return {
        id,
        name,
        printer_type: "epson_epos",
        printer_ip: "0.0.0.0",
        receipt: "<epos-print/>",
    };
}

onRpc("pos.order", "get_receipt_print_data", () => ({
    config_id: 1,
    printers,
    receipt_html: "<div class='pos-receipt'>Receipt</div>",
}));

onRpc(PRINTER_URL, () => {
    expect.step("print");
    throw new Error("The printer is not reachable");
});

async function mountPrintReceiptButton(receiptPrinters) {
    odoo.pos_config_id = 1;
    odoo.pos_session_id = 1;
    odoo.info = { db: "pos" };
    printers = receiptPrinters;
    await mountWithCleanup(PrintReceipt, { props: { record: { resId: 1 } } });
}

describe("PrintReceipt", () => {
    test("the browser is offered as a fallback when the printer is unreachable", async () => {
        await mountPrintReceiptButton([makePrinter(1, "Receipt Printer")]);

        await contains("button:contains('Print Receipt')").click();
        await waitFor(FALLBACK_BUTTON);

        expect(".modal").toHaveCount(0, {
            message: "a single printer is used without asking the device",
        });
        expect.verifySteps(["print"]);
    });

    test("the device is asked which printer to use, and remembers it", async () => {
        await mountPrintReceiptButton([
            makePrinter(1, "Receipt Printer"),
            makePrinter(2, "Second Printer"),
        ]);

        await contains("button:contains('Print Receipt')").click();
        await contains(
            ".modal:contains('Several receipt printers are available') label:contains('Second Printer') input"
        ).click();
        await contains(".modal button:contains('Confirm')").click();
        await waitFor(FALLBACK_BUTTON);

        expect(localStorage.getItem("pos_default_printer_id_1_pos")).toBe("2");
        expect.verifySteps(["print", "print"]);
    });

    test("the printer chosen by the device is not asked again", async () => {
        localStorage.setItem("pos_default_printer_id_1_pos", "2");
        await mountPrintReceiptButton([
            makePrinter(1, "Receipt Printer"),
            makePrinter(2, "Second Printer"),
        ]);

        await contains("button:contains('Print Receipt')").click();
        await waitFor(FALLBACK_BUTTON);

        expect(".modal").toHaveCount(0);
        expect.verifySteps(["print", "print"]);
    });
});

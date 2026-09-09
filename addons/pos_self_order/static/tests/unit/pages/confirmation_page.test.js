import { test, expect } from "@odoo/hoot";
import { setupSelfPosEnv, mockRouterNavigate } from "@pos_self_order/../tests/unit/utils";
import { definePosSelfModels } from "../data/generate_model_definitions";
import { patch } from "@web/core/utils/patch";
import * as Utils from "@pos_self_order/../tests/unit/ui_utils";
import { PosTicketPrinterService } from "@point_of_sale/app/services/pos_ticket_printer_service";

definePosSelfModels();

const mockTicketPrinterService = () => {
    const printedTickets = [];

    patch(PosTicketPrinterService.prototype, {
        async printOrderReceipt() {},
        async generateIframe(_template, data) {
            printedTickets.push(data.changes.data.map((line) => line.basic_name));
            return document.createElement("iframe");
        },
        setIframeSizeFromPrinter(iframe, printer) {
            return;
        },
        async generateImage() {
            return "fake_image_data";
        },
        print() {
            return { successful: true };
        },
    });

    return () => printedTickets;
};

test("kiosk prints order change recipt", async () => {
    mockRouterNavigate();
    const store = await setupSelfPosEnv(
        "kiosk",
        "counter",
        "each",
        {
            use_presets: false,
            available_preset_ids: [],
            preparation_printer_ids: [],
        },
        true
    );

    const posPrinter = store.models["pos.printer"].create({
        product_categories_ids: store.models["pos.category"].map((catg) => catg.id),
        pos_config_ids: [store.config],
        printer_type: "epson_epos",
    });

    store.config.preparation_printer_ids = [posPrinter];
    store.ticketPrinter.initPrinters();

    const getPrintedTickets = mockTicketPrinterService();

    await Utils.clickOrderNow();
    await Utils.clickProduct("Multi Category Product");
    await Utils.clickBtn("Checkout");
    await Utils.clickBtn("Order");
    await Utils.clickBtn("Close");

    const printedTickets = getPrintedTickets();
    expect(printedTickets).toHaveLength(1);
    expect(printedTickets[0]).toEqual(["Multi Category Product"]);
});

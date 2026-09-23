import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import {
    getFilledOrder,
    setupPosEnv,
    setupAndMountPosApp,
} from "@point_of_sale/../tests/unit/utils";
import { patch } from "@web/core/utils/patch";
import * as PosUiUtils from "@point_of_sale/../tests/unit/ui_utils";
import * as ResUiUtils from "@pos_restaurant/../tests/unit/ui_utils";
const Utils = { ...PosUiUtils, ...ResUiUtils };

definePosModels();

function buildChangeLine({
    uuid,
    product,
    quantity = 1,
    isCombo = false,
    comboParentUuid = undefined,
    name = product.display_name,
}) {
    return {
        uuid,
        product_id: product.id,
        name,
        basic_name: name,
        display_name: name,
        quantity,
        note: "",
        customer_note: "",
        attribute_value_names: [],
        pos_categ_id: product.pos_categ_ids[0]?.id ?? 0,
        pos_categ_sequence: product.pos_categ_ids[0]?.sequence ?? 0,
        pack_lot_lines: [],
        group: undefined,
        isCombo,
        combo_parent_uuid: comboParentUuid,
    };
}

test("preparation data includes table and customer note", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const table = store.models["restaurant.table"].get(2);
    const allCategoryIds = new Set(store.models["pos.category"].map((c) => c.id));
    order.table_id = table;
    order.setCustomerCount(5);
    order.lines[0].setCustomerNote("Updated customer note - orderline");

    const generator = store.ticketPrinter.getGenerator({ models: store.models, order });
    const receipts = generator.generatePreparationData(allCategoryIds, {});

    expect(receipts.length).toBe(1);
    expect(receipts[0].extra_data.table_name).toBe(table.table_number);
    expect(receipts[0].extra_data.time).toBeOfType("string");
    expect(receipts[0].changes.title).toBe("NEW");
    expect(receipts[0].changes.data[0].customer_note).toBe("Updated customer note - orderline");
});

test("note update title is generated", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const allCategoryIds = new Set(store.models["pos.category"].map((c) => c.id));

    const line = order.lines[0];
    const manualOrderChange = {
        addedQuantity: [],
        removedQuantity: [],
        noteUpdate: [
            {
                ...buildChangeLine({
                    uuid: line.uuid,
                    product: line.product_id,
                    quantity: line.qty,
                    name: line.product_id.display_name,
                }),
                customer_note: "Updated customer note - orderline",
            },
        ],
    };

    const generator = store.ticketPrinter.getGenerator({ models: store.models, order });
    const receipts = generator.generatePreparationData(allCategoryIds, {
        orderChange: manualOrderChange,
    });

    expect(receipts).toHaveLength(1);
    expect(receipts[0].changes.title).toBe("NOTE UPDATE");
    expect(receipts[0].changes.data).toHaveLength(1);
    expect(receipts[0].changes.data[0].customer_note).toBe("Updated customer note - orderline");
});

test("only printers with matching categories are used", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);

    const category1 = store.models["pos.category"].get(1);
    const category2 = store.models["pos.category"].get(2);

    const printer1 = store.models["pos.printer"].create({
        name: "Printer 1",
        printer_type: "epson_epos",
        product_categories_ids: [category1],
    });
    const printer2 = store.models["pos.printer"].create({
        name: "Printer 2",
        printer_type: "epson_epos",
        product_categories_ids: [category2],
    });

    printer1._instance = {};
    printer2._instance = {};

    let printedBy = [];
    store.ticketPrinter.generateIframe = async () => ({
        contentWindow: {},
        contentDocument: {},
    });
    store.ticketPrinter.generateImage = async () => "mock-image";
    store.ticketPrinter.print = async ({ printer }) => {
        printedBy.push(printer.name);
        return { successful: true };
    };
    store.ticketPrinter.showPrinterErrorDialog = () => {};
    store.ticketPrinter.setIframeSizeFromPrinter = () => {};

    // Both printers print when order has lines matching both categories
    let result = await store.ticketPrinter.printOrderChanges({
        order,
        printers: [printer1, printer2],
    });
    expect(result).toBe(true);
    expect(printedBy.sort()).toEqual(["Printer 1", "Printer 2"]);

    // Only matching printer prints when order has lines for one category
    order.lines[1].delete();
    printedBy = [];
    result = await store.ticketPrinter.printOrderChanges({
        order,
        printers: [printer1, printer2],
    });
    expect(result).toBe(true);
    expect(printedBy).toEqual(["Printer 1"]);
});

test("check only matching categories product data printed and reprinted", async () => {
    // Configure a printer that accepts only the category of the steel desk.
    const store = await setupAndMountPosApp({ preparation_printer_ids: [1] });
    let printedData = [];
    const generateIframeFun = store.ticketPrinter.generateIframe;
    patch(store.ticketPrinter, {
        async generateIframe(...args) {
            const data = args[1];
            // Capture the rendered lines to verify filtering independently of the printer UI.
            printedData.push(
                data.changes.data.map((line) => ({
                    basic_name: line.basic_name,
                    quantity: line.quantity,
                }))
            );
            return await generateIframeFun(...args);
        },
        print() {
            return { successful: true };
        },
    });
    await Utils.clickTable("1");
    await Utils.clickDisplayedProduct("Steel desk");
    await Utils.clickOrderButton();
    await animationFrame();
    await Utils.clickPlanButton();
    // A newly sent order prints the product matching the printer category.
    expect(printedData).toHaveLength(1);
    expect(printedData[0]).toHaveLength(1);
    expect(printedData[0][0]).toMatchObject({
        basic_name: "Steel desk",
        quantity: 1,
    });
    printedData = [];
    await Utils.clickTable("1");
    await Utils.clickDisplayedProduct("Bacon burger"); // Product category is not included in preparation printer
    await Utils.checkNoOrderButton();
    if (store.ui.isSmall) {
        await Utils.clickBackButton();
    }
    await Utils.clickReprintButton();
    // Reprinting must retain the previously printed matching line and exclude the burger.
    expect(printedData).toHaveLength(1);
    expect(printedData[0]).toHaveLength(1);
    expect(printedData[0][0]).toMatchObject({
        basic_name: "Steel desk",
        quantity: 1,
    });
});

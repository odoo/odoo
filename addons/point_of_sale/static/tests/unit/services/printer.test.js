import { test, expect } from "@odoo/hoot";
import { getFilledOrder, setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

definePosModels();

test("Preparation ticket: order note behavior and change detection", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const categoryIds = new Set(store.models["pos.category"].map((category) => category.id));

    const generatePreparationChanges = (currentOrder) => {
        const generator = store.ticketPrinter.getGenerator({
            models: store.models,
            order: currentOrder,
        });
        return generator.generatePreparationData(categoryIds, {});
    };
    // Case 1: Adding a general customer note with line changes
    {
        order.general_customer_note = "Order Customer Note";
        const changes = generatePreparationChanges(order);
        expect(changes).toHaveLength(1);
        expect(changes[0].extra_data.general_customer_note).toBe("Order Customer Note");
        expect(changes[0].changes.title).toBe("NEW");
    }
    // Case 2: Updating the general customer note alone
    {
        order.updateLastOrderChange();
        order.general_customer_note = "Updated Order Customer Note";
        const changes = generatePreparationChanges(order);
        expect(changes).toHaveLength(1);
        expect(changes[0].extra_data.general_customer_note).toBe("Updated Order Customer Note");
        expect(changes[0].changes).toMatchObject({
            data: [],
            title: "",
        });
    }
    // Case 3: Updating internal note should trigger with order Note Change
    {
        order.updateLastOrderChange();
        order.internal_note = "Order Internal Note";
        order.lines[0].customer_note = "Orderline customer note";
        const changes = generatePreparationChanges(order);
        expect(changes).toHaveLength(1);
        expect(changes[0].extra_data.internal_note).toBe("Order Internal Note");
        expect(changes[0].changes.title).toBe("NOTE UPDATE");
    }
});

const setupSinglePrinter = async () => {
    const store = await setupPosEnv();
    const printer = store.models["pos.printer"].get(3);
    printer.use_cashdrawer = true;
    store.config.update({ receipt_printer_ids: [printer] });
    patchWithCleanup(printer._instance, {
        openCashbox() {
            expect.step("cashbox opened");
        },
    });
    return { store, printer };
};

test("Cashdrawer: a single receipt printer becomes the default printer", async () => {
    const { store, printer } = await setupSinglePrinter();

    expect(store.ticketPrinter.defaultPrinter).toBe(null);
    expect(store.canOpenCashdrawer).toBe(true);

    await store.openCashbox();

    expect(store.ticketPrinter.defaultPrinter).toBe(printer);
    expect.verifySteps(["cashbox opened"]);
});

test("Cashdrawer: the default printer is restored after a refresh", async () => {
    const { store, printer } = await setupSinglePrinter();
    await store.openCashbox();

    expect(localStorage.getItem(store.ticketPrinter.printerStorageKey)).toBe(String(printer.id));

    store.ticketPrinter._defaultPrinter = null;
    store.ticketPrinter.initDefaultPrinter();

    expect(store.ticketPrinter.defaultPrinter).toBe(printer);
    expect.verifySteps(["cashbox opened"]);
});

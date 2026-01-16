import { test, expect } from "@odoo/hoot";
import { getFilledOrder, setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { TestReceiptUtil } from "../test_receipt_helper";

definePosModels();

test("[Order Receipt] validates printed order lines", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);

    const receipt = new TestReceiptUtil(store, order);
    await receipt.generateReceiptToTest();
    expect(receipt.tickets).toHaveLength(1);
    const ticketCheck = receipt.check(
        [
            { name: "TEST", qty: 3, infoList: ["3.00 / Units"] },
            { name: "TEST 2", qty: 2 },
        ],
        { nbPrints: 1 }
    );
    expect(ticketCheck).toBe(true);
});

test("[Preparation Ticket] validates product lines and customer notes", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    order.general_customer_note = "Test-P Order General Customer Note";

    const receipt = new TestReceiptUtil(store, order, "preparation");
    await receipt.generateReceiptToTest();
    expect(receipt.tickets).toHaveLength(2);
    // --- Ticket 1: Product lines ---
    const firstTicketCheck = receipt.check(
        [
            { name: "TEST", qty: 3 },
            { name: "TEST 2", qty: 2 },
        ],
        {
            visibleInDom: ["NEW"],
            invisibleInDom: ["DUPLICATE"],
            nbPrints: 2,
        }
    );
    expect(firstTicketCheck).toBe(true);
    // --- Ticket 2: Customer note ---
    const secondTicketCheck = receipt.check(
        [],
        {
            visibleInDom: ["Test-P Order General Customer Note"],
            invisibleInDom: ["DUPLICATE"],
        },
        2
    );
    expect(secondTicketCheck).toBe(true);
});

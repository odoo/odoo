import { test, expect } from "@odoo/hoot";
import { getFilledOrder, setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";

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

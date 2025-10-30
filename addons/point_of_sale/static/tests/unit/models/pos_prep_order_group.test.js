import { test, describe, expect } from "@odoo/hoot";
import { getFilledOrder, setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

describe("pos.prep.order.group", () => {
    test("Preparation changes", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);

        // Check preparation categories and product categories
        expect(Array.from(store.config.printerCategories)).toEqual([1, 2]);
        expect(order.lines[0].product_id.pos_categ_ids.map((c) => c.id)).toEqual([1]);
        expect(order.lines[1].product_id.pos_categ_ids.map((c) => c.id)).toEqual([2]);

        {
            // Check changes
            const change = order.preparationChanges;
            expect(change.quantity).toBe(5);
            expect(order.lines[0].qty).toBe(3);
            expect(order.lines[1].qty).toBe(2);
            expect(change.printerData.addedQuantity).toHaveLength(2);
            expect(change.printerData.removedQuantity).toHaveLength(0);
            expect(change.printerData.noteUpdate).toHaveLength(0);
            expect(order.prep_order_group_id.pos_order_ids).toHaveLength(1);
            expect(order.prep_order_group_id.prep_order_ids).toHaveLength(0);
            expect(order.prep_order_group_id.prepLines).toHaveLength(0);
        }

        {
            // Send changes to preparation and check that there is no more change
            await store.sendOrderInPreparation(order);
            const change = order.preparationChanges;
            expect(change.quantity).toBe(0);
            expect(change.printerData.addedQuantity).toHaveLength(0);
            expect(change.printerData.removedQuantity).toHaveLength(0);
            expect(change.printerData.noteUpdate).toHaveLength(0);
            expect(order.prep_order_group_id.pos_order_ids).toHaveLength(1);
            expect(order.prep_order_group_id.prep_order_ids).toHaveLength(1);
            expect(order.prep_order_group_id.prepLines).toHaveLength(2);
        }

        {
            // Increase quantity of the first line and check changes
            order.lines[0].setQuantity(5);
            const change = order.preparationChanges;
            const addedQuantity = change.printerData.addedQuantity;
            expect(change.quantity).toBe(2);
            expect(addedQuantity).toHaveLength(1);
            expect(addedQuantity[0].product_id).toBe(order.lines[0].product_id.id);
            expect(addedQuantity[0].quantity).toBe(2);
            expect(change.printerData.removedQuantity).toHaveLength(0);
            expect(change.printerData.noteUpdate).toHaveLength(0);

            await store.sendOrderInPreparation(order);
            expect(order.lines[0].qty).toBe(5);
            expect(order.lines[1].qty).toBe(2);
            expect(order.preparationChanges.quantity).toBe(0);
            expect(order.preparationChanges.printerData.addedQuantity).toHaveLength(0);
            expect(order.preparationChanges.printerData.removedQuantity).toHaveLength(0);
            expect(order.preparationChanges.printerData.noteUpdate).toHaveLength(0);
            expect(order.prep_order_group_id.pos_order_ids).toHaveLength(1);
            expect(order.prep_order_group_id.prep_order_ids).toHaveLength(2);
            expect(order.prep_order_group_id.prepLines).toHaveLength(3);
        }

        {
            // Cancel some quantity of the second line and check changes
            order.lines[1].setQuantity(1);
            const change = order.preparationChanges;
            const removedQuantity = change.printerData.removedQuantity;
            expect(change.quantity).toBe(-1);
            expect(removedQuantity).toHaveLength(1);
            expect(removedQuantity[0].product_id).toBe(order.lines[1].product_id.id);
            expect(removedQuantity[0].quantity).toBe(-1);
            expect(change.printerData.addedQuantity).toHaveLength(0);
            expect(change.printerData.noteUpdate).toHaveLength(0);

            await store.sendOrderInPreparation(order);
            expect(order.lines[0].qty).toBe(5);
            expect(order.lines[1].qty).toBe(1);
            expect(order.preparationChanges.quantity).toBe(0);
            expect(order.preparationChanges.printerData.addedQuantity).toHaveLength(0);
            expect(order.preparationChanges.printerData.removedQuantity).toHaveLength(0);
            expect(order.preparationChanges.printerData.noteUpdate).toHaveLength(0);
            expect(order.prep_order_group_id.pos_order_ids).toHaveLength(1);
            expect(order.prep_order_group_id.prep_order_ids).toHaveLength(2);
            expect(order.prep_order_group_id.prepLines).toHaveLength(3);
        }

        {
            // Cancel quantity by deleting a line and check changes
            const productId = order.lines[1].product_id.id;
            order.removeOrderline(order.lines[1]);
            const change = order.preparationChanges;
            const removedQuantity = change.printerData.removedQuantity;
            expect(change.quantity).toBe(-1);
            expect(removedQuantity).toHaveLength(1);
            expect(removedQuantity[0].product_id).toBe(productId);
            expect(removedQuantity[0].quantity).toBe(-1);
            expect(change.printerData.addedQuantity).toHaveLength(0);
            expect(change.printerData.noteUpdate).toHaveLength(0);

            await store.sendOrderInPreparation(order);
            expect(order.lines[0].qty).toBe(5);
            expect(order.lines).toHaveLength(1);
            expect(order.preparationChanges.quantity).toBe(0);
            expect(order.preparationChanges.printerData.addedQuantity).toHaveLength(0);
            expect(order.preparationChanges.printerData.removedQuantity).toHaveLength(0);
            expect(order.preparationChanges.printerData.noteUpdate).toHaveLength(0);
            expect(order.prep_order_group_id.pos_order_ids).toHaveLength(1);
            expect(order.prep_order_group_id.prep_order_ids).toHaveLength(2);
            expect(order.prep_order_group_id.prepLines).toHaveLength(3);
        }
    });

    test("Preparation note updates (order & lines)", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);

        // Check preparation categories and product categories
        expect(Array.from(store.config.printerCategories)).toEqual([1, 2]);
        expect(order.lines[0].product_id.pos_categ_ids.map((c) => c.id)).toEqual([1]);
        expect(order.lines[1].product_id.pos_categ_ids.map((c) => c.id)).toEqual([2]);

        {
            // Send order to preparation
            await store.sendOrderInPreparation(order);
            const change = order.preparationChanges;
            expect(change.quantity).toBe(0);
            expect(change.printerData.addedQuantity).toHaveLength(0);
            expect(change.printerData.removedQuantity).toHaveLength(0);
            expect(change.printerData.noteUpdate).toHaveLength(0);
            expect(order.prep_order_group_id.pos_order_ids).toHaveLength(1);
            expect(order.prep_order_group_id.prep_order_ids).toHaveLength(1);
            expect(order.prep_order_group_id.prepLines).toHaveLength(2);
        }

        {
            // Update notes on both lines and check changes
            order.lines[0].setNote("A");
            order.lines[1].setCustomerNote("B");
            const change = order.preparationChanges;
            const noteUpdate = change.printerData.noteUpdate;
            expect(change.quantity).toBe(0);
            expect(noteUpdate).toHaveLength(2);
            expect(noteUpdate[0].note).toBe("A");
            expect(noteUpdate[1].customer_note).toBe("B");
            expect(change.printerData.addedQuantity).toHaveLength(0);
            expect(change.printerData.removedQuantity).toHaveLength(0);
        }

        {
            // Send changes to preparation and check that there is no more change
            await store.sendOrderInPreparation(order);
            const change = order.preparationChanges;
            expect(change.quantity).toBe(0);
            expect(change.printerData.addedQuantity).toHaveLength(0);
            expect(change.printerData.removedQuantity).toHaveLength(0);
            expect(change.printerData.noteUpdate).toHaveLength(0);
            expect(order.prep_order_group_id.pos_order_ids).toHaveLength(1);
            expect(order.prep_order_group_id.prep_order_ids).toHaveLength(1);
            expect(order.prep_order_group_id.prepLines).toHaveLength(2);
        }

        {
            // Update general notes and check changes
            order.setGeneralCustomerNote("C");
            order.setInternalNote("D");
            const change = order.preparationChanges;
            expect(change.quantity).toBe(0);
            expect(change.printerData.addedQuantity).toHaveLength(0);
            expect(change.printerData.removedQuantity).toHaveLength(0);
            expect(change.printerData.noteUpdate).toHaveLength(0);
            expect(change.generalCustomerNote).toBe("C");
            expect(change.internalNote).toBe("D");
        }

        {
            // Send changes to preparation and check that there is no more change
            await store.sendOrderInPreparation(order);
            const change = order.preparationChanges;
            expect(change.quantity).toBe(0);
            expect(change.printerData.addedQuantity).toHaveLength(0);
            expect(change.printerData.removedQuantity).toHaveLength(0);
            expect(change.printerData.noteUpdate).toHaveLength(0);
            expect(change.generalCustomerNote).toBe(undefined);
            expect(change.internalNote).toBe(undefined);
            expect(order.prep_order_group_id.pos_order_ids).toHaveLength(1);
            expect(order.prep_order_group_id.prep_order_ids).toHaveLength(1);
            expect(order.prep_order_group_id.prepLines).toHaveLength(2);
        }
    });

    test("Preparation category count", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const categoryOne = store.models["pos.category"].get(1);
        const categoryTwo = store.models["pos.category"].get(2);
        const productTemplate = store.models["product.template"].get(8);
        // Check preparation categories and product categories
        expect(Array.from(store.config.printerCategories)).toEqual([1, 2]);
        expect(order.lines[0].product_id.pos_categ_ids.map((c) => c.id)).toEqual([1]);
        expect(order.lines[1].product_id.pos_categ_ids.map((c) => c.id)).toEqual([2]);
        expect(productTemplate.pos_categ_ids.map((c) => c.id)).toEqual([2]);

        {
            // Check category count before preparation
            const change = order.preparationChanges;
            expect(change.categoryCount[0].name).toBe(categoryOne.name);
            expect(change.categoryCount[0].count).toBe(3);
            expect(change.categoryCount[1].name).toBe(categoryTwo.name);
            expect(change.categoryCount[1].count).toBe(2);
        }

        {
            // Send order to preparation
            await store.sendOrderInPreparation(order);
            const change = order.preparationChanges;
            expect(change.quantity).toBe(0);
            expect(change.categoryCount).toHaveLength(0);
            expect(change.printerData.addedQuantity).toHaveLength(0);
            expect(change.printerData.removedQuantity).toHaveLength(0);
            expect(change.printerData.noteUpdate).toHaveLength(0);
            expect(order.prep_order_group_id.pos_order_ids).toHaveLength(1);
            expect(order.prep_order_group_id.prep_order_ids).toHaveLength(1);
            expect(order.prep_order_group_id.prepLines).toHaveLength(2);
        }

        {
            // Add quantity, remove quantity change note
            order.lines[0].setQuantity(0); // Category 1
            order.lines[1].setNote("A"); // Category 2
            await store.addLineToOrder({ product_tmpl_id: productTemplate, qty: 4 }, order); // Category 2
            const change = order.preparationChanges;
            expect(change.quantity).toBe(1);
            expect(change.categoryCount).toHaveLength(3);
            expect(change.categoryCount[0].name).toBe(categoryOne.name);
            expect(change.categoryCount[0].count).toBe(-3);
            expect(change.categoryCount[1].name).toBe(categoryTwo.name);
            expect(change.categoryCount[1].count).toBe(4);
            expect(change.categoryCount[2].name).toBe("Note");
            expect(change.categoryCount[2].count).toBe(1);
            expect(change.printerData.addedQuantity).toHaveLength(1);
            expect(change.printerData.removedQuantity).toHaveLength(1);
            expect(change.printerData.noteUpdate).toHaveLength(1);
        }

        {
            // Send changes to preparation and check that there is no more change
            await store.sendOrderInPreparation(order);
            const change = order.preparationChanges;
            expect(change.quantity).toBe(0);
            expect(change.categoryCount).toHaveLength(0);
            expect(change.printerData.addedQuantity).toHaveLength(0);
            expect(change.printerData.removedQuantity).toHaveLength(0);
            expect(change.printerData.noteUpdate).toHaveLength(0);
            expect(order.prep_order_group_id.pos_order_ids).toHaveLength(1);
            expect(order.prep_order_group_id.prep_order_ids).toHaveLength(2);
            expect(order.prep_order_group_id.prepLines).toHaveLength(3);
        }
    });
});

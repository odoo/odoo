import { test, describe, expect } from "@odoo/hoot";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { getFilledOrder, setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { SplitBillScreen } from "@pos_restaurant/app/screens/split_bill_screen/split_bill_screen";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

definePosModels();

describe("pos.prep.order.group", () => {
    test("Preparation with splitted orders", async () => {
        const store = await setupPosEnv();
        const orderOne = await getFilledOrder(store);
        const productTemplateOne = store.models["product.template"].get(8);
        const productTemplateTwo = store.models["product.template"].get(9);

        expect(Array.from(store.config.printerCategories)).toEqual([1, 2]);
        expect(orderOne.lines[0].product_id.pos_categ_ids.map((c) => c.id)).toEqual([1]);
        expect(orderOne.lines[1].product_id.pos_categ_ids.map((c) => c.id)).toEqual([2]);
        expect(productTemplateOne.pos_categ_ids.map((c) => c.id)).toEqual([2]);
        expect(productTemplateTwo.pos_categ_ids.map((c) => c.id)).toEqual([2]);

        /**
         * First we send the initial order to preparation.
         *
         * OrderOne states:
         * - Line 1: qty 3, prep qty 3
         * - Line 2: qty 2, prep qty 2
         */
        await store.sendOrderInPreparation(orderOne);
        const change = orderOne.preparationChanges;
        expect(change.quantity).toBe(0);
        expect(change.printerData.addedQuantity).toHaveLength(0);
        expect(change.printerData.removedQuantity).toHaveLength(0);
        expect(change.printerData.noteUpdate).toHaveLength(0);
        expect(orderOne.prep_order_group_id.pos_order_ids).toHaveLength(1);
        expect(orderOne.prep_order_group_id.prep_order_ids).toHaveLength(1);
        expect(orderOne.prep_order_group_id.prepLines).toHaveLength(2);
        expect(orderOne.prep_order_group_id.prepLines[0].quantity).toBe(3);
        expect(orderOne.prep_order_group_id.prepLines[1].quantity).toBe(2);
        expect(store.models["pos.prep.order.group"].length).toBe(1);

        /**
         * Split orderOne into two orders
         *
         * OrderOne states:
         * - Line 1: qty 3, prep qty 1
         * - Line 2: qty 2, prep qty 2
         *
         * OrderTwo states:
         * - Line 1: qty 2, prep qty 2
         */
        const comp = await mountWithCleanup(SplitBillScreen, {
            props: { orderUuid: orderOne.uuid },
        });
        comp.onClickLine(orderOne.lines[0]);
        comp.onClickLine(orderOne.lines[0]);
        const orderTwo = await comp.createSplittedOrder();
        expect(orderTwo.lines).toHaveLength(1);
        expect(orderTwo.lines[0].qty).toBe(2);
        expect(orderOne.lines).toHaveLength(2);
        expect(orderOne.lines[0].qty).toBe(1);
        await store.sendOrderInPreparation(orderOne);
        await store.sendOrderInPreparation(orderTwo);
        const prepGroupOne = orderOne.prep_order_group_id;
        const prepGroupTwo = orderTwo.prep_order_group_id;
        expect(orderOne.prep_order_group_id.pos_order_ids).toHaveLength(2);
        expect(orderOne.prep_order_group_id.prep_order_ids).toHaveLength(1);
        expect(orderOne.prep_order_group_id.prepLines).toHaveLength(2);
        expect(prepGroupOne.id).toBe(prepGroupTwo.id);
        expect(orderOne.lines[0].qty).toBe(1);
        expect(orderOne.lines[1].qty).toBe(2);
        expect(orderTwo.lines[0].qty).toBe(2);
        expect(store.models["pos.prep.order.group"].length).toBe(1);

        /**
         * Add a lines to orderTwo
         *
         * OrderOne states:
         * - Line 1: qty 1, prep qty 1
         * - Line 2: qty 2, prep qty 2
         *
         * OrderTwo states:
         * - Line 1: qty 2, prep qty 2
         * - Line 2: qty 1, prep qty 1
         */
        await store.addLineToOrder({ product_tmpl_id: productTemplateOne, qty: 1 }, orderTwo);
        await store.sendOrderInPreparation(orderTwo);
        expect(orderOne.prep_order_group_id.pos_order_ids).toHaveLength(2);
        expect(orderOne.prep_order_group_id.prep_order_ids).toHaveLength(2); // Increased
        expect(orderOne.prep_order_group_id.prepLines).toHaveLength(3); // Increased
        expect(orderOne.lines[0].qty).toBe(1);
        expect(orderOne.lines[1].qty).toBe(2);
        expect(orderTwo.lines[0].qty).toBe(2);
        expect(orderTwo.lines[1].qty).toBe(1);
        expect(store.models["pos.prep.order.group"].length).toBe(1);

        /**
         * Split orderTwo again
         *
         * OrderOne states:
         * - Line 1: qty 1, prep qty 1
         * - Line 2: qty 2, prep qty 2
         *
         * OrderTwo states:
         * - Line 1: qty 1, prep qty 1
         *
         * OrderThree states:
         * - Line 1: qty 2, prep qty 2
         */
        const split = await mountWithCleanup(SplitBillScreen, {
            props: { orderUuid: orderTwo.uuid },
        });
        split.onClickLine(orderTwo.lines[0]);
        split.onClickLine(orderTwo.lines[0]);
        const orderThree = await split.createSplittedOrder();
        expect(orderThree.lines).toHaveLength(1);
        expect(orderThree.lines[0].qty).toBe(2);
        expect(orderTwo.lines).toHaveLength(1);
        expect(orderTwo.lines[0].qty).toBe(1);
        expect(orderOne.lines).toHaveLength(2);
        expect(orderOne.lines[0].qty).toBe(1);
        expect(orderOne.lines[1].qty).toBe(2);
        await store.sendOrderInPreparation(orderTwo);
        await store.sendOrderInPreparation(orderThree);
        expect(orderOne.prep_order_group_id.pos_order_ids).toHaveLength(3);
        expect(orderOne.prep_order_group_id.prep_order_ids).toHaveLength(2);
        expect(orderOne.prep_order_group_id.prepLines).toHaveLength(3);
        expect(store.models["pos.prep.order.group"].length).toBe(1);

        /**
         * Cancel orderOne
         *
         * OrderTwo states:
         * - Line 1: qty 1, prep qty 1
         *
         * OrderThree states:
         * - Line 1: qty 2, prep qty 2
         */
        await store.deleteOrders([orderOne]);
        await store.sendOrderInPreparation(orderTwo);
        await store.sendOrderInPreparation(orderThree);
        expect(orderTwo.prep_order_group_id.pos_order_ids).toHaveLength(2);
        expect(orderTwo.prep_order_group_id.prep_order_ids).toHaveLength(2);
        expect(orderTwo.prep_order_group_id.prepLines).toHaveLength(3);
        expect(store.models["pos.prep.order.group"].length).toBe(1);
        const cancelled = orderTwo.prep_order_group_id.prepLines.map((l) => l.cancelled);
        expect(cancelled).toEqual([1, 2, 0]); // Cancel line with FIFO logic

        /**
         * Add lines to orderTwo and orderThree
         *
         * OrderTwo states:
         * - Line 1: qty 1, prep qty 1
         * - Line 2: qty 2, prep qty 2
         * - Line 3: qty 1, prep qty 1
         *
         * OrderThree states:
         * - Line 1: qty 2, prep qty 2
         * - Line 2: qty 1, prep qty 1
         */
        await store.addLineToOrder({ product_tmpl_id: productTemplateOne, qty: 2 }, orderTwo);
        await store.addLineToOrder({ product_tmpl_id: productTemplateTwo, qty: 1 }, orderTwo);
        await store.addLineToOrder({ product_tmpl_id: productTemplateTwo, qty: 1 }, orderThree);
        await store.sendOrderInPreparation(orderTwo);
        await store.sendOrderInPreparation(orderThree);
        expect(orderThree.prep_order_group_id.pos_order_ids).toHaveLength(2);
        expect(orderThree.prep_order_group_id.prep_order_ids).toHaveLength(4);
        expect(orderThree.prep_order_group_id.prepLines).toHaveLength(6);
        expect(store.models["pos.prep.order.group"].length).toBe(1);
    });
});

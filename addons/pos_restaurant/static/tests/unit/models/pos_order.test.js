import { test, describe, expect } from "@odoo/hoot";
import { setupPosEnv, getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { serverState, mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { SplitBillScreen } from "@pos_restaurant/app/screens/split_bill_screen/split_bill_screen";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";

definePosModels();

describe("pos.order restaurant patches", () => {
    test("customer count and amount per guest", async () => {
        const store = await setupPosEnv();
        const table = store.models["restaurant.table"].get(2);
        const order = await getFilledOrder(store, { table_id: table });
        order.setCustomerCount(3);
        expect(order.getCustomerCount()).toBe(3);
        order.setCustomerCount(4);
        expect(order.amountPerGuest()).toBe(4.4625);
    });

    test("isDirectSale", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        expect(order.isDirectSale).toBe(true);
    });

    test("setPartner", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        const partner = store.models["res.partner"].get(serverState.partnerId);
        order.setPartner(partner);
        expect(order.floating_order_name).toBe("Mitchell Admin");
    });

    test("cleanCourses", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const course1 = store.addCourse();
        const line = order.lines[0];
        line.course_id = course1;
        const course2 = store.addCourse();
        course1.fired = true;
        order.cleanCourses();
        expect(order.course_ids.includes(course2)).toBe(false);
        expect(order.course_ids.includes(course1)).toBe(true);
    });

    test("getNextCourseIndex", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        store.addCourse();
        store.addCourse();
        expect(order.getNextCourseIndex()).toBe(4);
    });

    test("getName returns formatted name for table + children", async () => {
        const store = await setupPosEnv();
        const table = store.models["restaurant.table"].get(2);
        const order = store.addNewOrder({ table_id: table });
        const child = store.models["restaurant.table"].get(3);
        let name = order.getName();
        expect(name).toBe("T 1 - 1001");
        child.parent_id = table;
        name = order.getName();
        expect(name).toBe("T 1 & 3 - 1001");
    });

    test("preparationChanges after split order", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const table = store.models["restaurant.table"].get(2);
        order.table_id = table;

        const line1 = order.lines[0];
        const line2 = order.lines[1];

        order.updateLastOrderChange();

        const prepLine1 = line1.prep_line_ids[0];
        expect(prepLine1.quantity).toBe(3);
        expect(line2.prep_line_ids[0].quantity).toBe(2);

        expect(order.getChanges().addedQuantity.length).toBe(0);
        expect(order.getChanges().removedQuantity.length).toBe(0);

        line1.setQuantity(5);

        const changesBeforeSplit = order.getChanges();
        expect(changesBeforeSplit.addedQuantity.length).toBe(1);
        expect(changesBeforeSplit.addedQuantity[0].quantity).toBe(2);

        const screen = await mountWithCleanup(SplitBillScreen, {
            props: { orderUuid: order.uuid },
        });
        screen.qtyTracker[line1.uuid] = 2;
        await screen.createSplittedOrder();

        const newOrder = store.getOrder();
        const newLine = newOrder.lines[0];

        expect(line1.getQuantity()).toBe(3);
        expect(prepLine1.quantity).toBe(1);
        const originalChanges = order.getChanges();
        expect(originalChanges.addedQuantity.length).toBe(1);
        expect(originalChanges.addedQuantity[0].quantity).toBe(2);
        expect(originalChanges.removedQuantity.length).toBe(0);

        expect(newLine.getQuantity()).toBe(2);
        expect(newLine.prep_line_ids.length).toBe(1);
        expect(newLine.prep_line_ids[0].quantity).toBe(2);
        const newOrderChanges = newOrder.getChanges();
        expect(newOrderChanges.addedQuantity.length).toBe(0);
        expect(newOrderChanges.removedQuantity.length).toBe(0);
    });

    test("preparationChanges: split qty 4 from 5, then add 1 on split order", async () => {
        const store = await setupPosEnv();
        const table = store.models["restaurant.table"].get(2);
        const order = store.addNewOrder({ table_id: table });
        const product = store.models["product.template"].get(5);

        await store.addLineToOrder({ product_tmpl_id: product, qty: 5 }, order);
        store.addPendingOrder([order.id]);

        const line = order.lines[0];
        expect(line.getQuantity()).toBe(5);

        order.updateLastOrderChange();
        const prepLine = line.prep_line_ids[0];
        expect(prepLine.quantity).toBe(5);
        expect(order.getChanges().addedQuantity.length).toBe(0);

        const screen = await mountWithCleanup(SplitBillScreen, {
            props: { orderUuid: order.uuid },
        });
        screen.qtyTracker[line.uuid] = 4;
        await screen.createSplittedOrder();

        const splitOrder = store.getOrder();
        const splitLine = splitOrder.lines[0];

        expect(line.getQuantity()).toBe(1);
        expect(prepLine.quantity).toBe(1);
        expect(order.getChanges().addedQuantity.length).toBe(0);
        expect(order.getChanges().removedQuantity.length).toBe(0);

        expect(splitLine.getQuantity()).toBe(4);
        expect(splitLine.prep_line_ids[0].quantity).toBe(4);
        expect(splitOrder.getChanges().addedQuantity.length).toBe(0);

        splitLine.setQuantity(5);

        const splitChanges = splitOrder.getChanges();
        expect(splitChanges.addedQuantity.length).toBe(1);
        expect(splitChanges.addedQuantity[0].quantity).toBe(1);
        expect(splitChanges.removedQuantity.length).toBe(0);

        expect(order.getChanges().addedQuantity.length).toBe(0);
    });

    test("preparationChanges: combo 2x same + 1 different product, scale to 3 combos then split 1", async () => {
        const store = await setupPosEnv();
        const table = store.models["restaurant.table"].get(2);
        const order = store.addNewOrder({ table_id: table });
        const comboTemplate = store.models["product.template"].get(17);
        const steelDeskItem = store.models["product.combo.item"].get(4);
        const woodChairItem = store.models["product.combo.item"].get(5);

        await store.addLineToOrder(
            {
                product_tmpl_id: comboTemplate,
                payload: [
                    [
                        { combo_item_id: steelDeskItem, qty: 2 },
                        { combo_item_id: woodChairItem, qty: 1 },
                    ],
                    [{ combo_item_id: steelDeskItem, qty: 2 }],
                ],
            },
            order
        );
        store.addPendingOrder([order.id]);

        const comboParent = order.lines.find((l) => l.combo_line_ids.length > 0);
        const deskLine = order.lines.filter((l) => l.product_id.id === steelDeskItem.product_id.id);
        const chairLine = order.lines.find((l) => l.product_id.id === woodChairItem.product_id.id);

        expect(deskLine.length).toBe(2);
        expect(deskLine[0].getQuantity()).toBe(2);
        expect(deskLine[1].getQuantity()).toBe(2);
        expect(chairLine.getQuantity()).toBe(1);

        order.updateLastOrderChange();

        expect(deskLine[0].prep_line_ids[0].quantity).toBe(2);
        expect(deskLine[1].prep_line_ids[0].quantity).toBe(2);
        expect(chairLine.prep_line_ids[0].quantity).toBe(1);
        expect(
            order.getChanges().addedQuantity.filter((c) => c.combo_parent_uuid === comboParent.uuid)
                .length
        ).toBe(0);

        comboParent.setQuantity(3, true);

        const changesAfterScale = order.getChanges();
        const chairChanges = changesAfterScale.addedQuantity.filter(
            (c) => c.product_id === steelDeskItem.product_id.id
        );
        expect(chairChanges.length).toBe(2);
        expect(chairChanges[0].quantity).toBe(4);
        expect(chairChanges[1].quantity).toBe(4);
        expect(
            changesAfterScale.addedQuantity.find(
                (c) => c.product_id === woodChairItem.product_id.id
            ).quantity
        ).toBe(2);

        order.updateLastOrderChange();

        expect(deskLine[0].prepQty).toBe(6);
        expect(deskLine[1].prepQty).toBe(6);
        expect(chairLine.prepQty).toBe(3);
        expect(order.getChanges().addedQuantity.length).toBe(0);

        const screen = await mountWithCleanup(SplitBillScreen, {
            props: { orderUuid: order.uuid },
        });
        screen.qtyTracker[comboParent.uuid] = 1;
        screen.qtyTracker[deskLine[0].uuid] = 2;
        screen.qtyTracker[deskLine[1].uuid] = 2;
        screen.qtyTracker[chairLine.uuid] = 1;
        await screen.createSplittedOrder();

        const splitOrder = store.getOrder();
        const splitDeskLine = splitOrder.lines.filter(
            (l) => l.product_id.id === steelDeskItem.product_id.id
        );
        const splitChairLine = splitOrder.lines.find(
            (l) => l.product_id.id === woodChairItem.product_id.id
        );

        expect(deskLine[0].getQuantity()).toBe(4);
        expect(deskLine[0].prep_line_ids[0].quantity).toBe(4);
        expect(deskLine[1].getQuantity()).toBe(4);
        expect(deskLine[1].prep_line_ids[0].quantity).toBe(4);
        expect(chairLine.getQuantity()).toBe(2);
        expect(chairLine.prep_line_ids[0].quantity).toBe(2);
        expect(order.getChanges().addedQuantity.length).toBe(0);
        expect(order.getChanges().removedQuantity.length).toBe(0);

        expect(splitDeskLine[0].getQuantity()).toBe(2);
        expect(splitDeskLine[0].prep_line_ids[0].quantity).toBe(2);
        expect(splitDeskLine[1].getQuantity()).toBe(2);
        expect(splitDeskLine[1].prep_line_ids[0].quantity).toBe(2);
        expect(splitChairLine.getQuantity()).toBe(1);
        expect(splitChairLine.prep_line_ids[0].quantity).toBe(1);
        expect(splitOrder.getChanges().addedQuantity.length).toBe(0);
        expect(splitOrder.getChanges().removedQuantity.length).toBe(0);
    });

    test("preparationChanges: apply best combo", async () => {
        const store = await setupPosEnv();
        const table = store.models["restaurant.table"].get(2);
        const order = store.addNewOrder({ table_id: table });
        const soda = store.models["product.template"].get(22);
        const fries = store.models["product.template"].get(23);

        await store.addLineToOrder({ product_tmpl_id: soda, qty: 1 }, order);
        await store.addLineToOrder({ product_tmpl_id: fries, qty: 1 }, order);
        store.addPendingOrder([order.id]);

        order.updateLastOrderChange();
        const sodaLine = order.lines.find((l) => l.product_id.id === soda.id);
        const friesLine = order.lines.find((l) => l.product_id.id === fries.id);
        const originalSodaPrepId = sodaLine.prep_line_ids[0].id;
        const originalFriesPrepId = friesLine.prep_line_ids[0].id;
        expect(sodaLine.prep_line_ids[0].quantity).toBe(1);
        expect(friesLine.prep_line_ids[0].quantity).toBe(1);

        patchWithCleanup(store.comboSuggestion, {
            getPotentialCombos(order) {
                return super.getPotentialCombos(order).slice(0, 1);
            },
        });

        const orderSummary = await mountWithCleanup(OrderSummary);

        expect(orderSummary.state.potentialCombos.length).toBe(1);
        await orderSummary.applyBestCombo();
        const comboParent = order.lines.find((l) => l.combo_line_ids.length > 0);
        const sodaComboLine = comboParent.combo_line_ids.find((l) => l.product_id.id === 22);
        const friesComboLine = comboParent.combo_line_ids.find((l) => l.product_id.id === 23);

        expect(sodaComboLine.prep_line_ids.length).toBe(1);
        expect(sodaComboLine.prep_line_ids[0].quantity).toBe(1);
        expect(sodaComboLine.prep_line_ids[0].id).not.toBe(originalSodaPrepId);

        expect(friesComboLine.prep_line_ids.length).toBe(1);
        expect(friesComboLine.prep_line_ids[0].quantity).toBe(1);
        expect(friesComboLine.prep_line_ids[0].id).not.toBe(originalFriesPrepId);

        expect(comboParent.prep_line_ids.length).toBe(1);
        expect(comboParent.prep_line_ids[0].quantity).toBe(1);

        expect(order.getChanges().addedQuantity.length).toBe(0);
        expect(order.getChanges().removedQuantity.length).toBe(0);
    });

    test("ensureCourseSelection and getSelectedCourse", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        const course1 = store.addCourse();
        course1.fired = false;
        const course2 = store.addCourse();
        course2.fired = true;
        order.ensureCourseSelection();
        expect(order.getSelectedCourse().uuid).toBe(course1.uuid);
    });

    test("isTippedAfterPayment", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        order.config_id.set_tip_after_payment = true;
        order.state = "paid";
        order.amount_paid = order.priceIncl - 1;
        expect(order.isTippedAfterPayment).toBe(true);

        order.amount_paid = order.priceIncl;
        expect(order.isTippedAfterPayment).toBe(false);
    });
});

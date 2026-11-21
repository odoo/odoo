import { expect, test } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupAndMountPosApp, setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import * as PosUiUtils from "@point_of_sale/../tests/unit/ui_utils";
import * as ResUiUtils from "@pos_restaurant/../tests/unit/ui_utils";
import { SplitBillScreen } from "@pos_restaurant/app/screens/split_bill_screen/split_bill_screen";

const Utils = { ...PosUiUtils, ...ResUiUtils };

definePosModels();

async function setupTableOrders() {
    const store = await setupPosEnv();
    store.config.module_pos_deposit = true;
    const table = (id) => store.models["restaurant.table"].get(id);
    return {
        store,
        product: store.models["product.template"].get(5),
        deposit: store.models["product.template"].get(9100),
        sourceOrder: store.addNewOrder({ table_id: table(2) }),
        destOrder: store.addNewOrder({ table_id: table(3) }),
    };
}

const summary = (order) =>
    order.lines.map((line) => [
        line.product_id.display_name,
        line.qty,
        line.deposit_main_line_id?.order_id === order
            ? line.deposit_main_line_id.product_id.display_name
            : false,
    ]);

test("deposit lines follow the course of their product", async () => {
    const store = await setupAndMountPosApp({
        set_tip_after_payment: false,
        module_pos_deposit: true,
    });
    const template = (id) => store.models["product.template"].get(id);
    const comboItem = (id) => store.models["product.combo.item"].get(id);

    await Utils.clickTable("1");
    const product = await store.addLineToCurrentOrder({ product_tmpl_id: template(5) });
    await Utils.clickCourseButton();
    const combo = await store.addLineToCurrentOrder({
        product_tmpl_id: template(7),
        payload: [
            [
                { combo_item_id: comboItem(1), qty: 1 },
                { combo_item_id: comboItem(4), qty: 1 },
            ],
            [],
        ],
    });
    const comboFamily = combo
        .getAllLinesInCombo()
        .flatMap((line) => [line, ...line.deposit_line_ids]);
    const productCourse = product.course_id;
    const comboCourse = combo.course_id;

    expect(productCourse).not.toBe(comboCourse);
    expect(product.depositLine.course_id).toBe(productCourse);
    expect(comboFamily).toHaveLength(5);
    expect(comboFamily.every((line) => line.course_id === comboCourse)).toBe(true);

    product.course_id = comboCourse;
    expect(product.depositLine.course_id).toBe(comboCourse);

    combo.depositLine.course_id = productCourse;
    expect(comboFamily.every((line) => line.course_id === productCourse)).toBe(true);
});

test("merging tables with the same product keeps one deposit per product line", async () => {
    const { store, product, sourceOrder, destOrder } = await setupTableOrders();
    await store.addLineToOrder({ product_tmpl_id: product }, sourceOrder);
    await store.addLineToOrder({ product_tmpl_id: product }, destOrder);

    await store.mergeOrders(sourceOrder, destOrder);

    expect(summary(destOrder)).toEqual([
        ["TEST", 2, false],
        ["Deposit", 2, "TEST"],
    ]);
});

test("a product copied by a merge takes its deposit along", async () => {
    const { store, product, deposit, sourceOrder, destOrder } = await setupTableOrders();
    await store.addLineToOrder({ product_tmpl_id: product, qty: 3 }, sourceOrder);
    await store.addLineToOrder({ product_tmpl_id: deposit }, destOrder);

    await store.mergeOrders(sourceOrder, destOrder);

    expect(summary(destOrder)).toEqual([
        ["Deposit", 1, false],
        ["TEST", 3, false],
        ["Deposit", 3, "TEST"],
    ]);
});

test("splitting a bill splits each deposit with its product", async () => {
    const { store, product, sourceOrder } = await setupTableOrders();
    const productLine = await store.addLineToOrder(
        { product_tmpl_id: product, qty: 3 },
        sourceOrder
    );
    store.setOrder(sourceOrder);
    const screen = await mountWithCleanup(SplitBillScreen, {
        props: { orderUuid: sourceOrder.uuid },
    });
    screen.onClickLine(productLine);

    const newOrder = await screen.createSplittedOrder();

    expect(summary(sourceOrder)).toEqual([
        ["TEST", 2, false],
        ["Deposit", 2, "TEST"],
    ]);
    expect(summary(newOrder)).toEqual([
        ["TEST", 1, false],
        ["Deposit", 1, "TEST"],
    ]);
});

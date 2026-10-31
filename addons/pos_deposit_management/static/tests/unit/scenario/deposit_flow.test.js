import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import {
    setupAndMountPosApp,
    createTestProduct,
    createComboSetup,
} from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import * as Utils from "@point_of_sale/../tests/unit/ui_utils";
import { createDeposit } from "../utils";

definePosModels();

function createBottle(store, id) {
    const deposit = createDeposit(store, { id: id + 1, name: "Bottle Deposit", price: 1 });
    const { template } = createTestProduct(store, { id, name: "Bottle", price: 10 });
    template.deposit_product_id = deposit;
}

const names = (lines) => lines.map((line) => line.product_id.name);

test("deposit line is added after a simple product", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false });
    createBottle(store, 9100);
    await animationFrame();

    await Utils.clickDisplayedProduct("Bottle");
    await animationFrame();

    const order = store.getOrder();
    expect(names(order.sortDepositLines(order.lines))).toEqual(["Bottle", "Bottle Deposit"]);
    const [bottle] = order.lines;
    expect(bottle.depositLine.deposit_main_line_id).toBe(bottle);
    expect(order.priceIncl).toBe(11);
});

test("no deposit line when the setting is off", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false });
    store.config.module_pos_deposit_management = false;
    createBottle(store, 9110);
    await animationFrame();

    await Utils.clickDisplayedProduct("Bottle");
    await animationFrame();

    expect(store.getOrder().lines).toHaveLength(1);
});

test("quantity stays in sync between the main line and its deposit line", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false });
    createBottle(store, 9120);
    await animationFrame();
    await Utils.clickDisplayedProduct("Bottle");
    await animationFrame();

    const [bottle] = store.getOrder().lines;
    const deposit = bottle.depositLine;

    bottle.setQuantity(3);
    expect(deposit.qty).toBe(3);

    deposit.setQuantity(5);
    expect(bottle.qty).toBe(5);
    expect(deposit.qty).toBe(5);
});

test("adding the same product twice keeps one deposit line in sync", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false });
    createBottle(store, 9130);
    await animationFrame();

    await Utils.clickDisplayedProduct("Bottle");
    await Utils.clickDisplayedProduct("Bottle");
    await animationFrame();

    const order = store.getOrder();
    expect(order.lines).toHaveLength(2);
    const [bottle] = order.lines;
    expect(bottle.qty).toBe(2);
    expect(bottle.depositLine.qty).toBe(2);
});

test("removing the main line removes its deposit line", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false });
    createBottle(store, 9140);
    await animationFrame();
    await Utils.clickDisplayedProduct("Bottle");
    await animationFrame();

    const order = store.getOrder();
    order.removeOrderline(order.lines[0]);
    expect(order.lines).toHaveLength(0);
});

test("combo: deposits sit under their child and the parent deposit comes last", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false });
    const { template: comboTmpl, products } = createComboSetup(store, {
        id: 9150,
        name: "Office Combo",
        price: 30,
        combos: [
            {
                name: "Combo 1",
                items: [{ name: "Combo Product 2", price: 11 }],
                basePrice: 10,
                qtyFree: 1,
                qtyMax: 1,
            },
            {
                name: "Combo 2",
                items: [{ name: "Combo Product 4", price: 20 }],
                basePrice: 10,
                qtyFree: 1,
                qtyMax: 1,
            },
        ],
    });
    const childDeposit = createDeposit(store, { id: 9161, name: "Child Deposit", price: 1 });
    const parentDeposit = createDeposit(store, { id: 9171, name: "Parent Deposit", price: 2 });
    products.find(
        ({ template }) => template.name === "Combo Product 2"
    ).template.deposit_product_id = childDeposit;
    comboTmpl.deposit_product_id = parentDeposit;
    await animationFrame();

    await Utils.clickDisplayedProduct("Office Combo");
    await animationFrame();

    const order = store.getOrder();
    expect(names(order.sortDepositLines(order.lines))).toEqual([
        "Office Combo",
        "Combo Product 2",
        "Child Deposit",
        "Combo Product 4",
        "Parent Deposit",
    ]);
});

test("combo: changing the parent quantity updates every deposit line", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false });
    const { template: comboTmpl } = createComboSetup(store, {
        id: 9180,
        name: "Office Combo",
        price: 30,
        combos: [
            {
                name: "Combo 1",
                items: [{ name: "Combo Product 2", price: 11 }],
                basePrice: 10,
                qtyFree: 1,
                qtyMax: 1,
            },
        ],
    });
    comboTmpl.deposit_product_id = createDeposit(store, {
        id: 9191,
        name: "Parent Deposit",
        price: 2,
    });
    await animationFrame();
    await Utils.clickDisplayedProduct("Office Combo");
    await animationFrame();

    const parent = store.getOrder().lines.find((line) => line.combo_line_ids.length);
    parent.setQuantity(2);

    expect(parent.depositLine.qty).toBe(2);
    for (const child of parent.combo_line_ids) {
        expect(child.qty).toBe(2);
    }
});

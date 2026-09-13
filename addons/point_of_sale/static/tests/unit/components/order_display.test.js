import { expect, test } from "@odoo/hoot";
import { click, queryAll, queryAllTexts, queryOne } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { OrderDisplay } from "@point_of_sale/app/components/order_display/order_display";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";
import { formatCurrency } from "@web/core/currency";

definePosModels();

const TEST_PRODUCT = 5;

async function addLine(store, order, vals = {}) {
    const { product = TEST_PRODUCT, lots = [], ...rest } = vals;
    const line = await store.addLineToOrder(
        {
            product_tmpl_id: store.models["product.template"].get(product),
            price_unit: 10,
            qty: 1,
            ...rest,
        },
        order,
        {},
        false,
    );
    if (lots.length) {
        line.setPackLotLines({
            modifiedPackLotLines: {},
            newPackLotLines: lots.map((lot_name) => ({ lot_name })),
            setQuantity: true,
        });
    }
    return line;
}

async function mountDisplay(order, props = {}) {
    return mountWithCleanup(OrderDisplay, { props: { order, slots: {}, ...props } });
}

const rows = () => queryAll(".order-container > .orderline");

test("lines of one serial product collapse into one row listing every lot", async () => {
    const store = await setupPosEnv();
    store.models["product.template"].get(TEST_PRODUCT).tracking = "serial";
    const order = store.addNewOrder();
    await addLine(store, order, { lots: ["SN1"] });
    await addLine(store, order, { lots: ["SN2"] });
    expect(order.lines).toHaveLength(2);
    expect(order.lines.map((l) => l.qty)).toEqual([1, 1]);
    expect(order.lines.map((l) => l.hasValidProductLot())).toEqual([true, true]);

    await mountDisplay(order);
    expect(rows()).toHaveLength(1);
    expect(queryOne(".orderline .qty").textContent.trim()).toBe("2");
    expect(queryAllTexts(".orderline .lot-number")).toEqual(["SN SN1", "SN SN2"]);
});

test("lines that differ in customer note stay apart", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    await addLine(store, order, { customer_note: "no onions" });
    await addLine(store, order, { customer_note: "extra onions" });

    await mountDisplay(order);
    expect(rows()).toHaveLength(2);
});

test("the row is selected when any of its lines is", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const first = await addLine(store, order);
    const last = await addLine(store, order);
    expect(order.getSelectedOrderline()).toBe(last);
    expect(first.isSelected()).toBe(false);

    await mountDisplay(order);
    expect(rows()).toHaveLength(1);
    expect(queryAll(".order-container > .orderline.selected")).toHaveLength(1);
});

test("clicking the row toggles the selection on the displayed order", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    store.setOrder(order);
    await addLine(store, order);
    await addLine(store, order);

    await mountWithCleanup(OrderSummary, {});
    expect(rows()).toHaveLength(1);
    expect(queryAll(".orderline.selected")).toHaveLength(1);
    expect(queryOne(".orderline .qty").textContent.trim()).toBe("2");

    await click(".order-container > .orderline");
    await animationFrame();
    expect(order.getSelectedOrderline()).toBe(undefined);
    expect(queryAll(".orderline.selected")).toHaveLength(0);

    await click(".order-container > .orderline");
    await animationFrame();
    expect(order.lines.map((l) => l.uuid)).toInclude(order.getSelectedOrderline().uuid);
    expect(queryAll(".orderline.selected")).toHaveLength(1);
});

test("receipt mode shows every line and no headers", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    await addLine(store, order);
    await addLine(store, order);

    await mountDisplay(order, { mode: "receipt" });
    expect(rows()).toHaveLength(2);
    expect(queryAll(".orderline-headers")).toHaveLength(0);
});

test("a finalized order is never grouped, so each line can be refunded", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    await addLine(store, order);
    await addLine(store, order);
    order.state = "paid";

    await mountDisplay(order);
    expect(rows()).toHaveLength(2);
    expect(queryAll(".orderline-headers")).toHaveLength(0);
});

test("the ticket screen lists every line of a paid order and a click picks that line for refund", async () => {
    onRpc("search_paid_order_ids", () => ({ ordersInfo: [], totalCount: 0 }));
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    await addLine(store, order);
    const second = await addLine(store, order);
    order.state = "paid";
    store.addNewOrder();

    const screen = await mountWithCleanup(TicketScreen, {
        props: { stateOverride: { selectedOrderUuid: order.uuid, filter: "SYNCED" } },
    });
    await animationFrame();
    if (screen.ui.isSmall) {
        await click(".review-button");
        await animationFrame();
    }
    expect(rows()).toHaveLength(2);
    await click(rows()[1]);
    await animationFrame();
    expect(screen.getSelectedOrderlineId()).toBe(second.id);
});

test("clicking a row of a displayed order that is not the current one leaves the current order alone", async () => {
    const store = await setupPosEnv();
    const shown = store.addNewOrder();
    await addLine(store, shown);
    await addLine(store, shown);
    const current = store.addNewOrder();
    const currentLine = await addLine(store, current, { product: 6 });
    store.setOrder(current);
    shown.deselectOrderline();

    await mountDisplay(shown);
    await click(".order-container > .orderline");
    await animationFrame();
    expect(current.getSelectedOrderline().uuid).toBe(currentLine.uuid);
    expect(shown.getSelectedOrderline()).toBe(undefined);
});

test("the row price is the sum of the lines' display prices under the configured tax mode", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const l1 = await addLine(store, order, { qty: 2 });
    const l2 = await addLine(store, order, { qty: 3 });
    await mountDisplay(order);

    for (const mode of ["total", "subtotal"]) {
        order.config.iface_tax_included = mode;
        await animationFrame();
        const expected = formatCurrency(
            l1.displayPrice + l2.displayPrice,
            order.currency.id,
        );
        expect(
            queryOne(".order-container > .orderline .product-price").textContent,
        ).toBe(expected);
    }
    expect(l1.priceIncl).not.toBe(l1.priceExcl);
});

test("the row quantity is formatted with the unit's precision", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    await addLine(store, order, { qty: 0.1 });
    await addLine(store, order, { qty: 0.2 });

    await mountDisplay(order);
    const asOneLine = order.lines[0].quantityStrFor(0.3).qtyStr;
    expect(asOneLine).not.toBe(String(0.1 + 0.2));
    expect(queryOne(".orderline .qty").textContent.replace(/\s/g, "")).toBe(asOneLine);
});

test("lines from different stock locations stay apart and show their location", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const l1 = await addLine(store, order);
    const l2 = await addLine(store, order);
    const l3 = await addLine(store, order);
    l1.location_id = { id: 1, display_name: "Shelf A" };
    l2.location_id = { id: 1, display_name: "Shelf A" };
    l3.location_id = { id: 2, display_name: "Shelf B" };

    await mountDisplay(order);
    expect(rows()).toHaveLength(2);
    expect(queryAllTexts(".orderline .qty")).toEqual(["2", "1"]);
    expect(queryAllTexts(".orderline .line-location")).toEqual(["Shelf A", "Shelf B"]);
});

test("combos are never grouped and keep their children under their parent", async () => {
    const store = await setupPosEnv();
    const data = store.models.loadConnectedData({
        "pos.order": [
            { id: 900, name: "Combos", state: "draft", lines: [901, 902, 903, 904] },
        ],
        "pos.order.line": [
            {
                id: 901,
                order_id: 900,
                product_id: 7,
                price_unit: 0,
                qty: 1,
                combo_line_ids: [902],
                tax_ids: [],
            },
            {
                id: 902,
                order_id: 900,
                product_id: 8,
                price_unit: 5,
                qty: 1,
                combo_parent_id: 901,
                tax_ids: [],
            },
            {
                id: 903,
                order_id: 900,
                product_id: 7,
                price_unit: 0,
                qty: 1,
                combo_line_ids: [904],
                tax_ids: [],
            },
            {
                id: 904,
                order_id: 900,
                product_id: 10,
                price_unit: 8,
                qty: 1,
                combo_parent_id: 903,
                tax_ids: [],
            },
        ],
    });
    const order = data["pos.order"][0];

    await mountDisplay(order);
    expect(rows()).toHaveLength(4);
    const names = queryAllTexts(
        ".order-container > .orderline .product-name .text-wrap",
    ).map((t) => t.split("\n")[0].trim());
    expect(names).toEqual([
        "Product combo",
        "Wood chair",
        "Product combo",
        "Wood desk",
    ]);
});

test("headers render once above a draft order's lines and not for an empty order", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    await mountDisplay(order);
    expect(queryAll(".orderline-headers")).toHaveLength(0);

    await addLine(store, order);
    await animationFrame();
    expect(queryAll(".orderline-headers")).toHaveLength(1);
    expect(
        queryAll(".orderline-headers > *").map((el) => el.textContent.trim()),
    ).toEqual(["Qty.", "Product", "Price"]);
    expect(queryOne(".order-container").firstElementChild).toHaveClass(
        "orderline-headers",
    );
});

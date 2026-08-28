import { test, describe, expect, beforeEach } from "@odoo/hoot";
import {
    setupSelfPosEnv,
    getFilledSelfOrder,
    addComboProduct,
    mockLNAPermissionCheck,
} from "../utils";
import { mockDate } from "@odoo/hoot-mock";
import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { definePosSelfModels } from "../data/generate_model_definitions";
import { patchWithCleanup, onRpc, MockServer } from "@web/../tests/web_test_helpers";

definePosSelfModels();

const setOrderIdentifier = (token) => {
    const url = new URL(browser.location.href);
    url.searchParams.set("order_identifier", token);
    history.replaceState({}, "", url);
};

test("currentOrder", async () => {
    const store = await setupSelfPosEnv();
    const models = store.models;
    const order = store.currentOrder;
    const orders = models["pos.order"].getAll();

    expect(orders).toHaveLength(1);
    expect(order.id).toBe(orders[0].id);

    store.selectedOrderUuid = false;
    expect(store.currentOrder.id).toBe(orders[0].id);
    expect(store.selectedOrderUuid).toBe(orders[0].uuid);

    orders[0].delete();
    expect(models["pos.order"].length).toBe(0);
    expect(store.currentOrder.id).toBe(models["pos.order"].getAll()[0].id);
});

describe("currentTable", () => {
    test("dynamic_qr mode returns the current order's bound table", async () => {
        const store = await setupSelfPosEnv("mobile", "dynamic_qr", "meal");
        const order = await getFilledSelfOrder(store);

        expect(store.currentTable).toBe(null);

        const table = store.models["restaurant.table"].getFirst();
        order.table_id = table;
        expect(store.currentTable?.id).toBe(table.id);
    });

    test("other modes returns the table matching the router identifier", async () => {
        const store = await setupSelfPosEnv("mobile", "table", "each");
        await getFilledSelfOrder(store);
        const table = store.models["restaurant.table"].getFirst();
        table.identifier = "test-table-identifier";

        expect(store.currentTable).toBe(null);

        store.router.addTableIdentifier(table);
        expect(store.currentTable?.id).toBe(table.id);
    });
});

describe("currentTableIdentifier", () => {
    test("dynamic_qr mode returns the current order's bound table identifier", async () => {
        const store = await setupSelfPosEnv("mobile", "dynamic_qr", "meal");
        const order = await getFilledSelfOrder(store);
        const table = store.models["restaurant.table"].getFirst();
        table.identifier = "bound-table-identifier";

        expect(store.currentTableIdentifier).toBe(null);

        order.table_id = table;
        expect(store.currentTableIdentifier).toBe("bound-table-identifier");
    });

    test("other modes fall back to the router identifier", async () => {
        const store = await setupSelfPosEnv("mobile", "table", "each");
        await getFilledSelfOrder(store);
        const table = store.models["restaurant.table"].getFirst();
        table.identifier = "test-table-identifier";

        expect(store.currentTableIdentifier).toBe(null);

        store.router.addTableIdentifier(table);
        expect(store.currentTableIdentifier).toBe("test-table-identifier");
    });
});

describe("availablePresets", () => {
    test("dynamic_qr mode", async () => {
        const store = await setupSelfPosEnv("mobile", "dynamic_qr", "meal", {}, true);
        expect(store.availablePresets.map((preset) => preset.id)).toEqual([20, 22]);
    });

    test("kiosk mode", async () => {
        const store = await setupSelfPosEnv("kiosk", "counter", "each", {}, true);
        const allPresets = store.models["pos.preset"].getAll();

        expect(store.availablePresets.length).toBe(allPresets.length);
    });

    test("table mode", async () => {
        const store = await setupSelfPosEnv("mobile", "table", "each", {}, true);
        const allPresets = store.models["pos.preset"].getAll();
        const table = store.models["restaurant.table"].getFirst();
        table.identifier = "test-table-identifier";

        // No table identifier
        expect(store.availablePresets.length).toBe(allPresets.length - 2);
        expect(store.availablePresets).not.toInclude(store.models["pos.preset"].get(20));
        expect(store.availablePresets).not.toInclude(store.models["pos.preset"].get(22));

        // Has table identifier
        store.router.addTableIdentifier(table);
        expect(store.availablePresets.length).toBe(allPresets.length);
    });

    test("shop closed", async () => {
        const store = await setupSelfPosEnv("kiosk", "counter", "each", {}, false);
        store.ordering = true;

        const presetIds = store.availablePresets.map((preset) => preset.id).sort((a, b) => a - b);
        expect(presetIds).toEqual([2, 5, 23]);
    });
});

describe("initMobileData", () => {
    test("order_identifier in the url validates and selects the order in dynamic_qr mode", async () => {
        const store = await setupSelfPosEnv("mobile", "dynamic_qr", "meal", {}, true);
        const order = await getFilledSelfOrder(store);
        store.selectedOrderUuid = null;
        setOrderIdentifier(order.access_token);

        await store.initMobileData();

        expect(store.selectedOrderUuid).toBe(order.uuid);
        expect(store.ordering).toBe(true);
    });

    test("order_identifier pointing to a no longer draft order is not selected nor validated", async () => {
        const store = await setupSelfPosEnv("mobile", "dynamic_qr", "meal", {}, true);
        const order = await getFilledSelfOrder(store);
        order.state = "paid";
        store.selectedOrderUuid = order.uuid;
        setOrderIdentifier(order.access_token);

        await store.initMobileData();

        expect(store.selectedOrderUuid).toBe(null);
        expect(store.ordering).toBe(false);
    });

    test("order_identifier is ignored entirely outside dynamic_qr mode", async () => {
        const store = await setupSelfPosEnv("mobile", "table", "meal", {}, true);
        const order = await getFilledSelfOrder(store);
        store.selectedOrderUuid = null;
        setOrderIdentifier(order.access_token);

        await store.initMobileData();

        expect(store.selectedOrderUuid).toBe(null);
        expect(store.ordering).toBe(true);
    });
});

describe("_computePendingDeltas", () => {
    test("returns a delta only for synced lines whose local qty differs from their last-synced baseline", async () => {
        const store = await setupSelfPosEnv();
        const order = await getFilledSelfOrder(store);
        await store.sendDraftOrderToServer();
        order.recomputeChanges();

        expect(store._computePendingDeltas().size).toBe(0);

        const line = order.lines[0];
        line.qty += 2;

        const pendingDeltas = store._computePendingDeltas();
        expect(pendingDeltas.size).toBe(1);
        expect(pendingDeltas.get(line)).toBe(2);
    });

    test("ignores lines that were never synced at all", async () => {
        const store = await setupSelfPosEnv();
        await getFilledSelfOrder(store);

        expect(store._computePendingDeltas().size).toBe(0);
    });
});

describe("_reapplyPendingDeltas", () => {
    test("reapplies the delta on top of the refreshed qty and restores it as the new baseline", async () => {
        const store = await setupSelfPosEnv();
        const order = await getFilledSelfOrder(store);
        await store.sendDraftOrderToServer();
        order.recomputeChanges();
        const line = order.lines[0];
        const syncedQty = line.qty;

        line.qty = syncedQty + 1;
        const pendingDeltas = store._computePendingDeltas();

        line.qty = syncedQty + 2;
        store._reapplyPendingDeltas(order, pendingDeltas);

        expect(line.qty).toBe(syncedQty + 3);
        expect(order.uiState.lineChanges[line.uuid].qty).toBe(syncedQty + 2);
    });

    test("removes the line instead of going negative when the reapplied delta would drop qty to 0 or below", async () => {
        const store = await setupSelfPosEnv();
        const order = await getFilledSelfOrder(store);
        await store.sendDraftOrderToServer();
        order.recomputeChanges();
        const line = order.lines[0];
        const syncedQty = line.qty;

        line.qty = syncedQty - 2;
        const pendingDeltas = store._computePendingDeltas();

        line.qty = 1;
        store._reapplyPendingDeltas(order, pendingDeltas);

        expect(order.lines.find((l) => l.uuid === line.uuid)).toBeEmpty();
    });

    test("ignores deltas for lines belonging to a different order", async () => {
        const store = await setupSelfPosEnv();
        const order = await getFilledSelfOrder(store);
        await store.sendDraftOrderToServer();
        order.recomputeChanges();
        const line = order.lines[0];
        const syncedQty = line.qty;

        line.qty = syncedQty + 1;
        const pendingDeltas = store._computePendingDeltas();

        const otherOrder = store.models["pos.order"].create({});
        store._reapplyPendingDeltas(otherOrder, pendingDeltas);

        expect(line.qty).toBe(syncedQty + 1);
    });
});

describe("_syncedOrderSnapshot", () => {
    test("changes when a synced line's qty changes", async () => {
        const store = await setupSelfPosEnv();
        const order = await getFilledSelfOrder(store);

        const before = store._syncedOrderSnapshot(order);
        await store.sendDraftOrderToServer();
        const [line1, line2] = order.lines;

        line1.qty += 1;

        const after = store._syncedOrderSnapshot(order);
        expect(after).not.toBe(before);
        expect(JSON.parse(after)).toEqual([
            order.state,
            order.general_customer_note,
            [
                [line1.id, line1.product_id.id, line1.qty, line1.price_unit],
                [line2.id, line2.product_id.id, line2.qty, line2.price_unit],
            ],
        ]);
    });

    test("changes when the order's general_customer_note changes", async () => {
        const store = await setupSelfPosEnv();
        const order = await getFilledSelfOrder(store);
        await store.sendDraftOrderToServer();

        const before = store._syncedOrderSnapshot(order);
        order.general_customer_note = "no onions";
        const after = store._syncedOrderSnapshot(order);

        expect(after).not.toBe(before);
    });

    test("ignores a line's customer_note (self-order cannot set per-line notes)", async () => {
        const store = await setupSelfPosEnv();
        const order = await getFilledSelfOrder(store);
        await store.sendDraftOrderToServer();
        const [line1] = order.lines;

        const before = store._syncedOrderSnapshot(order);
        line1.customer_note = "no onions";
        const after = store._syncedOrderSnapshot(order);

        expect(after).toBe(before);
    });

    test("ignores lines that were never synced", async () => {
        const store = await setupSelfPosEnv();
        const order = await getFilledSelfOrder(store);
        const before = store._syncedOrderSnapshot(order);
        await store.sendDraftOrderToServer();
        const [line1, line2] = order.lines;

        const product = store.models["product.template"].get(8);
        await store.addToCart(product, 1);

        const after = store._syncedOrderSnapshot(order);
        expect(after).not.toBe(before);
        expect(JSON.parse(after)).toEqual([
            order.state,
            order.general_customer_note,
            [
                [line1.id, line1.product_id.id, line1.qty, line1.price_unit],
                [line2.id, line2.product_id.id, line2.qty, line2.price_unit],
            ],
        ]);
    });
});

describe("canProceedToPay", () => {
    test("returns true without refreshing when the order has no access_token yet", async () => {
        const store = await setupSelfPosEnv();
        const product = store.models["product.template"].get(5);
        await store.addToCart(product, 1);

        expect(store.currentOrder.access_token).toBe(undefined);
        expect(await store.canProceedToPay()).toBe(true);
    });

    test("returns true and does not warn when nothing changed server-side", async () => {
        const store = await setupSelfPosEnv();
        const order = await getFilledSelfOrder(store);
        await store.sendDraftOrderToServer();
        onRpc("/pos-self-order/get-user-data/", () =>
            MockServer.env["pos.order"].read_pos_data([order.id], {}, store.config.id)
        );
        patchWithCleanup(store.notification, {
            add: () => expect.step("notification"),
        });

        expect(await store.canProceedToPay()).toBe(true);
        expect.verifySteps([]);
    });

    test("returns false and warns when the order changed server-side", async () => {
        const store = await setupSelfPosEnv();
        const order = await getFilledSelfOrder(store);
        await store.sendDraftOrderToServer();
        const line = order.lines[0];
        MockServer.env["pos.order.line"].write([line.id], { qty: line.qty + 5 });
        onRpc("/pos-self-order/get-user-data/", () =>
            MockServer.env["pos.order"].read_pos_data([order.id], {}, store.config.id)
        );
        patchWithCleanup(store.notification, {
            add: () => expect.step("notification"),
        });

        expect(await store.canProceedToPay()).toBe(false);
        expect.verifySteps(["notification"]);
    });

    test("returns false and warns when the order became paid server-side with an unchanged cart", async () => {
        const store = await setupSelfPosEnv();
        const order = await getFilledSelfOrder(store);
        await store.sendDraftOrderToServer();
        MockServer.env["pos.order"].write([order.id], { state: "paid" });
        onRpc("/pos-self-order/get-user-data/", () =>
            MockServer.env["pos.order"].read_pos_data([order.id], {}, store.config.id)
        );
        patchWithCleanup(store.notification, {
            add: () => expect.step("notification"),
        });

        expect(await store.canProceedToPay()).toBe(false);
        expect.verifySteps(["notification"]);
    });

    test("returns true and does not warn when only a line's customer_note changes server-side", async () => {
        const store = await setupSelfPosEnv();
        const order = await getFilledSelfOrder(store);
        await store.sendDraftOrderToServer();
        const line = order.lines[0];
        MockServer.env["pos.order.line"].write([line.id], { customer_note: "no onions" });
        onRpc("/pos-self-order/get-user-data/", () =>
            MockServer.env["pos.order"].read_pos_data([order.id], {}, store.config.id)
        );
        patchWithCleanup(store.notification, {
            add: () => expect.step("notification"),
        });

        expect(await store.canProceedToPay()).toBe(true);
        expect.verifySteps([]);
    });

    test("returns false and warns when the order's general note changed server-side", async () => {
        const store = await setupSelfPosEnv();
        const order = await getFilledSelfOrder(store);
        await store.sendDraftOrderToServer();
        MockServer.env["pos.order"].write([order.id], { general_customer_note: "no onions" });
        onRpc("/pos-self-order/get-user-data/", () =>
            MockServer.env["pos.order"].read_pos_data([order.id], {}, store.config.id)
        );
        patchWithCleanup(store.notification, {
            add: () => expect.step("notification"),
        });

        expect(await store.canProceedToPay()).toBe(false);
        expect.verifySteps(["notification"]);
    });
});

describe("getUserDataFromServer", () => {
    test("pushOrphanedLines (default): merges another local draft's lines into openOrder and deletes it", async () => {
        const store = await setupSelfPosEnv("kiosk", "counter", "each", {}, true);
        const ownOrder = await getFilledSelfOrder(store);
        expect(ownOrder.lines.length).toBe(2);

        const openOrderId = MockServer.env["pos.order"].create({
            config_id: store.config.id,
            session_id: store.session.id,
            access_token: "open-order-token",
            state: "draft",
        });
        onRpc("/pos-self-order/get-user-data/", () =>
            MockServer.env["pos.order"].read_pos_data([openOrderId], {}, store.config.id)
        );

        await store.getUserDataFromServer(["open-order-token"]);

        const openOrder = store.models["pos.order"].find(
            (o) => o.access_token === "open-order-token"
        );
        expect(store.selectedOrderUuid).toBe(openOrder.uuid);
        expect(store.models["pos.order"].find((o) => o.uuid === ownOrder.uuid)).toBe(undefined);
        expect(openOrder.lines.length).toBe(2);
    });

    test("pushOrphanedLines: false deletes another local draft without merging its lines", async () => {
        const store = await setupSelfPosEnv("kiosk", "counter", "each", {}, true);
        const ownOrder = await getFilledSelfOrder(store);

        const openOrderId = MockServer.env["pos.order"].create({
            config_id: store.config.id,
            session_id: store.session.id,
            access_token: "open-order-token",
            state: "draft",
        });
        onRpc("/pos-self-order/get-user-data/", () =>
            MockServer.env["pos.order"].read_pos_data([openOrderId], {}, store.config.id)
        );

        await store.getUserDataFromServer(["open-order-token"], { pushOrphanedLines: false });

        const openOrder = store.models["pos.order"].find(
            (o) => o.access_token === "open-order-token"
        );
        expect(store.selectedOrderUuid).toBe(openOrder.uuid);
        expect(store.models["pos.order"].find((o) => o.uuid === ownOrder.uuid)).toBe(undefined);
        expect(openOrder.lines.length).toBe(0);
    });

    test("prefers the draft matching the requested token over an arbitrary other draft", async () => {
        const store = await setupSelfPosEnv("kiosk", "counter", "each", {}, true);
        const requestedId = MockServer.env["pos.order"].create({
            config_id: store.config.id,
            session_id: store.session.id,
            access_token: "requested-token",
            state: "draft",
        });
        const otherId = MockServer.env["pos.order"].create({
            config_id: store.config.id,
            session_id: store.session.id,
            access_token: "other-token",
            state: "draft",
        });
        onRpc("/pos-self-order/get-user-data/", () =>
            MockServer.env["pos.order"].read_pos_data([otherId, requestedId], {}, store.config.id)
        );

        await store.getUserDataFromServer(["requested-token"]);

        const requestedOrder = store.models["pos.order"].find(
            (o) => o.access_token === "requested-token"
        );
        expect(store.selectedOrderUuid).toBe(requestedOrder.uuid);
    });

    test("multiple requested tokens: the first wins, neither is treated as an orphan", async () => {
        const store = await setupSelfPosEnv("kiosk", "counter", "each", {}, true);
        const firstId = MockServer.env["pos.order"].create({
            config_id: store.config.id,
            session_id: store.session.id,
            access_token: "first-token",
            state: "draft",
        });
        const secondId = MockServer.env["pos.order"].create({
            config_id: store.config.id,
            session_id: store.session.id,
            access_token: "second-token",
            state: "draft",
        });
        onRpc("/pos-self-order/get-user-data/", () =>
            // Backend returns second order then first order
            MockServer.env["pos.order"].read_pos_data([secondId, firstId], {}, store.config.id)
        );

        await store.getUserDataFromServer(["first-token", "second-token"]);

        const order1 = store.models["pos.order"].find((o) => o.access_token === "first-token");
        const order2 = store.models["pos.order"].find((o) => o.access_token === "second-token");
        expect(store.selectedOrderUuid).toBe(order1.uuid);
        expect(order2).not.toBeEmpty();
    });
});

describe("initProducts", () => {
    test("hide special products", async () => {
        const store = await setupSelfPosEnv();
        const models = store.models;
        const tipProductTmpl = models["product.template"].get(1);

        expect(tipProductTmpl.product_variant_ids[0]._is_pos_special_product).toBe(true);

        models["product.template"].get(14).pos_categ_ids = [];
        store.initData();
        const UncategorisedProducts = store.productByCategIds["0"];
        expect(UncategorisedProducts.find((p) => p.id === tipProductTmpl.id)).toBeEmpty();

        tipProductTmpl.pos_categ_ids = [1];
        store.initData();
        const catg1Products = store.productByCategIds[1];
        expect(catg1Products.find((p) => p.id === tipProductTmpl.id)).toBeEmpty();
    });

    test("availableCategories and computeAvailableCategories", async () => {
        const store = await setupSelfPosEnv();
        const models = store.models;
        models["product.template"].get(14).pos_categ_ids = [];
        store.initData();

        store.computeAvailableCategories();
        expect(models["pos.category"].length).toBe(14);
        expect(store.availableCategories).toHaveLength(15); // Uncategorised also added
        expect(store.availableCategories.map((c) => c.id)).toEqual([
            1, 200, 2, 201, 4, 203, 3, 204, 5, 205, 206, 207, 208, 209, 0,
        ]);

        // When all products have categories - Uncategorised should be not there
        models["product.template"]
            .filter((p) => !p.pos_categ_ids.length)
            .forEach((prd) => prd.update({ pos_categ_ids: [2] }));
        store.initData();
        store.computeAvailableCategories();
        expect(store.availableCategories).toHaveLength(14);
        expect(store.availableCategories.map((c) => c.id)).toEqual([
            1, 200, 2, 201, 4, 203, 3, 204, 5, 205, 206, 207, 208, 209,
        ]);

        // Time availability
        const unAvailableCatg = models["pos.category"].get(1);
        unAvailableCatg.update({
            hour_after: 10,
            hour_until: 12,
        });
        mockDate("2025-11-29 18:00:00");
        store.computeAvailableCategories();
        expect(store.availableCategories).toHaveLength(13);
        expect(store.isCategoryAvailable(unAvailableCatg)).toBeEmpty();
    });
});

describe("initHardware", () => {
    test("adds payment terminals", async () => {
        const store = await setupSelfPosEnv();
        const models = store.models;
        const mockTerminalMethod = models["pos.payment.method"].create({
            payment_provider: "mock_terminal",
        });
        class MockTerminal {}
        registry.category("pos_payment_providers").add("mock_terminal", MockTerminal);

        store.initHardware();

        expect(mockTerminalMethod.payment_interface).toBeInstanceOf(MockTerminal);
    });

    test("initLNA is only called in kiosk mode", async () => {
        const store = await setupSelfPosEnv();
        store.models["pos.printer"].get(1).use_lna = true;

        const lna = mockLNAPermissionCheck();
        store.initHardware();
        expect(lna.wasCalled).toBe(true);

        lna.reset();
        store.config.self_ordering_mode = "mobile";
        store.initHardware();
        expect(lna.wasCalled).toBe(false);
    });
});

test("applyPendingComboConversion", async () => {
    const store = await setupSelfPosEnv();

    await store.addToCart(store.models["product.template"].get(8), 2);
    await store.addToCart(store.models["product.template"].get(10), 1);

    const [chairLine, deskLine] = store.currentOrder.lines;
    store.pendingComboConversion = {
        concernedLinesQty: {
            [chairLine.uuid]: 1,
            [deskLine.uuid]: 1,
        },
    };

    store.applyPendingComboConversion();

    expect(store.currentOrder.lines).toHaveLength(1);
    expect(store.currentOrder.lines[0].uuid).toBe(chairLine.uuid);
    expect(store.currentOrder.lines[0].qty).toBe(1);
    expect(store.pendingComboConversion).toBe(null);
});

test("createNewOrder", async () => {
    const store = await setupSelfPosEnv(
        "kiosk",
        "counter",
        "each",
        {
            default_preset_id: 1,
        },
        true
    );
    const models = store.models;
    {
        expect(store.config.available_preset_ids.length > 1).toBe(true);
        const order = store.createNewOrder();
        expect(order.preset_id).toBeEmpty();
    }
    models["pos.preset"].forEach((p) => p.id !== 1 && p.delete());
    {
        // automatically select the preset if only one is available
        expect(store.config.available_preset_ids).toHaveLength(1);
        const order = store.createNewOrder();
        expect(order.preset_id.id).toBe(1);
    }
});

test("removeLine", async () => {
    const store = await setupSelfPosEnv();
    const order = await getFilledSelfOrder(store);

    expect(order.lines).toHaveLength(2);
    store.removeLine(order.lines[0]);
    expect(order.lines).toHaveLength(1);
});

test("verifyCart", async () => {
    const store = await setupSelfPosEnv();
    const models = store.models;
    await getFilledSelfOrder(store);
    {
        const result = store.verifyCart();
        expect(result).toBe(true);
        expect(store.currentOrder.lines).toHaveLength(2);
    }
    {
        // with unavailable product
        models["product.product"].get(5).self_order_available = false;
        const result = store.verifyCart();
        expect(result).toBe(false);
        expect(store.currentOrder.lines).toHaveLength(1);
    }
});

test("getProductPriceInfo", async () => {
    const store = await setupSelfPosEnv();
    const order = await getFilledSelfOrder(store);

    const models = store.models;
    const product5 = models["product.template"].get(5);
    const variant5 = models["product.product"].get(5);
    const pricelist = models["product.pricelist"].get(3);
    const inPreset = models["pos.preset"].get(1);
    const outPreset = store.models["pos.preset"].get(2);

    // Template-only call uses first variant lst_price (same default as addToCart).
    const savedList = product5.list_price;
    const savedLst = variant5.lst_price;
    product5.list_price = 1;
    variant5.lst_price = 222;
    expect(store.getProductPriceInfo(product5).pricelist_price).toBe(222);
    product5.list_price = savedList;
    variant5.lst_price = savedLst;

    expect(store.getProductPriceInfo(product5).pricelist_price).toBe(100);

    store.config.pricelist_id = pricelist;
    expect(store.getProductPriceInfo(product5).pricelist_price).toBe(10);

    order.setPreset(outPreset);
    expect(store.getProductPriceInfo(product5).pricelist_price).toBe(10);

    const savedPercentPrice = pricelist.item_ids[0].percent_price;
    pricelist.item_ids[0].percent_price = 80;
    inPreset.pricelist_id = pricelist;
    order.setPreset(inPreset);
    expect(store.getProductPriceInfo(product5).pricelist_price).toBe(20);
    pricelist.item_ids[0].percent_price = savedPercentPrice;

    // Fiscal position on the order (via setPreset) must change display price.
    store.config.pricelist_id = false;
    const fpStrip = models["account.fiscal.position"].get(2);
    const savedOutFp = outPreset.fiscal_position_id;
    const savedOutPricelist = outPreset.pricelist_id;
    const savedDefaultFp = store.config.default_fiscal_position_id;
    outPreset.fiscal_position_id = false;
    outPreset.pricelist_id = false;
    store.config.default_fiscal_position_id = false;
    order.setPreset(outPreset);

    const displayWithTaxes = store.getProductDisplayPrice(product5);
    expect(displayWithTaxes).toBe(115);

    outPreset.fiscal_position_id = fpStrip;
    order.setPreset(outPreset);
    const displayAfterStripFp = store.getProductDisplayPrice(product5);
    expect(displayAfterStripFp).toBe(100);
    expect(displayAfterStripFp).not.toBe(displayWithTaxes);

    outPreset.fiscal_position_id = savedOutFp;
    outPreset.pricelist_id = savedOutPricelist;
    store.config.default_fiscal_position_id = savedDefaultFp;
});

describe("addToCart", () => {
    test("simple flow", async () => {
        const store = await setupSelfPosEnv();
        const models = store.models;
        const product5 = models["product.template"].get(5);
        const product6 = models["product.template"].get(6);

        store.addToCart(product5, 2, "");
        expect(store.currentOrder.lines).toHaveLength(1);
        expect(store.currentOrder.lines[0].qty).toBe(2);

        // with same Product
        store.addToCart(product5, 7, "");
        expect(store.currentOrder.lines).toHaveLength(1);
        expect(store.currentOrder.lines[0].qty).toBe(9);

        // with diffrent Product
        store.addToCart(product6, 4, "");
        expect(store.currentOrder.lines).toHaveLength(2);
        expect(store.currentOrder.lines[1].qty).toBe(4);
    });
    test("Combo Products", async () => {
        const store = await setupSelfPosEnv();
        await addComboProduct(store);

        expect(store.currentOrder.lines).toHaveLength(3);
        const [parent, child1, child2] = store.currentOrder.lines;

        expect(parent.combo_parent_id).toBeEmpty();
        expect(parent.combo_line_ids).toHaveLength(2);
        expect(parent.combo_line_ids[0].id).toBe(child1.id);
        expect(parent.combo_line_ids[1].id).toBe(child2.id);

        expect(child1.combo_parent_id.id).toBe(parent.id);
        expect(child2.combo_parent_id.id).toBe(parent.id);

        expect(parent.qty).toBe(2);
        expect(child1.qty).toBe(2);
        expect(child2.qty).toBe(2);
    });

    test("With pricelist acting on variants", async () => {
        const store = await setupSelfPosEnv();
        const productTemplate = store.models["product.template"].get(101);

        store.addToCart(productTemplate, 1, "", [101]);
        store.addToCart(productTemplate, 1, "", [102]);

        expect(store.currentOrder.lines[0].price_unit).toBe(10);
        expect(store.currentOrder.lines[1].price_unit).toBe(15);

        store.currentOrder.removeOrderline(store.currentOrder.lines[0]);
        store.currentOrder.removeOrderline(store.currentOrder.lines[0]);
        expect(store.currentOrder.lines).toHaveLength(0);

        const pricelist = store.models["product.pricelist"].get(101);
        store.config.pricelist_id = pricelist;

        store.addToCart(productTemplate, 1, "", [101]);
        store.addToCart(productTemplate, 1, "", [102]);
        expect(store.currentOrder.lines[0].price_unit).toBe(15);
        expect(store.currentOrder.lines[1].price_unit).toBe(20);
    });

    test("With price_extra for attribute create_variant='no_variant'", async () => {
        const store = await setupSelfPosEnv();
        const productTemplate = store.models["product.template"].get(102);

        store.addToCart(productTemplate, 1, "", [103]);
        store.addToCart(productTemplate, 1, "", [104]);
        expect(store.currentOrder.lines[0].price_unit).toBe(200);
        expect(store.currentOrder.lines[1].price_unit).toBe(210);
    });
});

test("syncs the local draft order and its lines, reusing the same order", async () => {
    const store = await setupSelfPosEnv();
    const order = await getFilledSelfOrder(store);

    expect(order.id).toBeOfType("string");
    expect(order.lines).toHaveLength(2);
    expect(order.lines[0].id).toBeOfType("string");
    expect(order.lines[1].id).toBeOfType("string");

    const syncOrder = await store.sendDraftOrderToServer();
    expect(order.id).toBeOfType("number");
    expect(order.lines).toHaveLength(2);
    expect(order.lines[0].id).toBeOfType("number");
    expect(order.lines[1].id).toBeOfType("number");

    expect(syncOrder.id).toBe(order.id);
    expect(store.currentOrder.id).toBe(syncOrder.id);
    // no other order should be created
    expect(store.models["pos.order"].length).toBe(1);
});

test("sendDraftOrderToServer updateLastOrderChange", async () => {
    const store = await setupSelfPosEnv("mobile", "table", "meal");
    const order = await getFilledSelfOrder(store);

    const product1 = store.models["product.template"].get(8);
    await store.addToCart(product1, 1, "");
    await store.sendDraftOrderToServer();
    expect(Object.keys(order.prep_order_ids[0].prep_line_ids)).toHaveLength(3);
});

describe("setOrderPrices", () => {
    test("Combo products order", async () => {
        const store = await setupSelfPosEnv();
        await addComboProduct(store);

        store.currentOrder.setOrderPrices();
        const [parentLine, comboLine1, comboLine2] = store.currentOrder.lines;

        expect(parentLine.price_subtotal).toBe(0);
        expect(parentLine.price_subtotal_incl).toBe(0);

        expect(comboLine1.price_subtotal).toBe(200);
        expect(comboLine1.price_subtotal_incl).toBe(250);

        expect(comboLine2.price_subtotal).toBe(200);
        expect(comboLine2.price_subtotal_incl).toBe(250);
    });
});

describe("cancelOrder", () => {
    test("Normal cancel order", async () => {
        const store = await setupSelfPosEnv();
        const models = store.models;
        const order = await getFilledSelfOrder(store);

        expect(order.lines).toHaveLength(2);
        expect(models["pos.order"].length).toBe(1);
        expect(models["pos.order.line"].length).toBe(2);

        store.cancelOrder();
        expect(order.lines).toHaveLength(0);
        // Order and lines are deleted
        expect(models["pos.order"].length).toBe(0);
        expect(models["pos.order.line"].length).toBe(0);
        expect(store.selectedOrderUuid).toBeEmpty();
    });
    test("Some line are sent", async () => {
        const store = await setupSelfPosEnv();
        const models = store.models;
        const order = await getFilledSelfOrder(store);
        const line1 = order.lines[0];

        expect(order.lines).toHaveLength(2);
        expect(line1.qty).toBe(3);
        await store.sendDraftOrderToServer();
        order.recomputeChanges();

        const product8 = models["product.template"].get(8);
        store.addToCart(product8, 2, "");
        expect(order.lines).toHaveLength(3);
        expect(models["pos.order.line"].length).toBe(3);

        line1.qty = 6; // 3 qty are sent
        store.cancelOrder();
        // unsent line were deleted
        expect(order.lines).toHaveLength(2);
        expect(line1.qty).toBe(3); // qty reset to 3
        expect(models["pos.order"].length).toBe(1);
        expect(models["pos.order.line"].length).toBe(2);
    });
    test("reverts to the last-sent qty, not the pending delta, across multiple sync rounds", async () => {
        const store = await setupSelfPosEnv();
        const order = await getFilledSelfOrder(store);
        const product1 = store.models["product.template"].get(5);
        const line1 = order.lines.find((l) => l.product_id.id === 5);

        expect(line1.qty).toBe(3);
        await store.sendDraftOrderToServer(); // round 1 sent: qty 3

        await store.addToCart(product1, 1);
        expect(line1.qty).toBe(4);
        await store.sendDraftOrderToServer(); // round 2 sent: qty 4

        await store.addToCart(product1, 1);
        expect(line1.qty).toBe(5); // round 3: pending, not sent

        store.cancelOrder();
        // Must revert to the last SENT quantity (4), not the pending
        // delta (5 - 4 = 1).
        expect(line1.qty).toBe(4);
    });
});

test("cancelBackendOrder", async () => {
    const store = await setupSelfPosEnv();
    const order = await getFilledSelfOrder(store);

    const syncOrder = await store.sendDraftOrderToServer();
    expect(order.id).toBeOfType("number");
    expect(order.lines[0].id).toBeOfType("number");
    expect(order.lines[1].id).toBeOfType("number");
    expect(syncOrder.id).toBe(order.id);

    await store.cancelBackendOrder();

    expect(order.state).toBe("cancel");
    expect(store.router.activeSlot).toBe("default");
});

test("resetCategorySelection", async () => {
    const store = await setupSelfPosEnv();
    store.computeAvailableCategories();
    const [ctg1, ctg2] = store.availableCategories.slice(0, 2);

    // Kiosk Mode
    store.config.self_ordering_mode = "kiosk";
    expect(store.currentCategory.id).toBe(ctg1.id);
    store.currentCategory = ctg2;
    expect(store.currentCategory.id).toBe(ctg2.id);
    store.resetCategorySelection();
    expect(store.currentCategory.id).toBe(ctg1.id);

    // Mobile Mode
    store.config.self_ordering_mode = "mobile";
    store.currentCategory = ctg2;
    expect(store.currentCategory.id).toBe(ctg2.id);
    store.resetCategorySelection();
    expect(store.currentCategory.id).toBe(ctg2.id);

    // On Order Confirmation
    await getFilledSelfOrder(store);
    store.config.self_ordering_mode = "kiosk";
    expect(store.currentCategory.id).toBe(ctg2.id);
    await store.confirmOrder();
    expect(store.currentCategory.id).toBe(ctg1.id);
});

describe("printOrderChanges", () => {
    beforeEach(async () => {
        const store = await setupSelfPosEnv("kiosk", "counter", "each", {}, true);

        store.config.self_ordering_mode = "kiosk";
        for (const relPrinter of store.models["pos.printer"].getAll()) {
            relPrinter.delete();
        }

        this.posPrinter = store.models["pos.printer"].create({
            product_categories_ids: [],
            pos_config_ids: [store.config],
            printer_type: "epson_epos",
        });

        store.config.preparation_printer_ids = [this.posPrinter];
        await store.ticketPrinter.initPrinters();

        const printedData = [];
        patchWithCleanup(store.ticketPrinter, {
            async generateIframe(template, data) {
                printedData.push(data.changes.data.map((line) => line.basic_name));
                return document.createElement("iframe");
            },
            print() {
                return { successful: true };
            },
        });

        this.printedData = printedData;
        this.getPrintedOrderLines = () => {
            expect(this.printedData.length).toBe(1);
            return this.printedData[0];
        };

        const cat1 = store.models["pos.category"].get(1);
        const cat2 = store.models["pos.category"].get(2);
        const cat3 = store.models["pos.category"].get(3);

        const comboTemplate = store.models["product.template"].get(7);
        comboTemplate.pos_categ_ids = [cat3];
        comboTemplate.product_variant_ids[0].pos_categ_ids = [cat3];

        const comboItem1 = comboTemplate.combo_ids[1].combo_item_ids[0];
        const comboItem2 = comboTemplate.combo_ids[0].combo_item_ids[0];

        comboItem1.product_id.pos_categ_ids = [cat1];
        comboItem1.product_id.product_tmpl_id.pos_categ_ids = [cat1];

        comboItem2.product_id.pos_categ_ids = [cat2];
        comboItem2.product_id.product_tmpl_id.pos_categ_ids = [cat2];

        const testProduct1 = store.models["product.template"].get(5);
        testProduct1.pos_categ_ids = [cat1];
        testProduct1.product_variant_ids[0].pos_categ_ids = [cat1];

        const testProduct2 = store.models["product.template"].get(6);
        testProduct2.pos_categ_ids = [cat2, cat3];
        testProduct2.product_variant_ids[0].pos_categ_ids = [cat2, cat3];

        const comboValues = [
            {
                combo_item_id: comboItem1,
                qty: 1,
            },
            {
                combo_item_id: comboItem2,
                qty: 1,
            },
        ];
        store.addToCart(comboTemplate, 1, "", {}, {}, comboValues);
        store.addToCart(testProduct1, 1);
        store.addToCart(testProduct2, 1);

        const orderLines = store.currentOrder.lines;
        expect(orderLines[0].product_id.pos_categ_ids[0]).toBe(cat3);
        expect(orderLines[1].product_id.pos_categ_ids[0]).toBe(cat2);
        expect(orderLines[2].product_id.pos_categ_ids[0]).toBe(cat1);
        expect(orderLines[3].product_id.pos_categ_ids[0]).toBe(cat1);
        expect(orderLines[4].product_id.pos_categ_ids[0]).toBe(cat2);
        expect(orderLines[4].product_id.pos_categ_ids[1]).toBe(cat3);

        this.store = store;
        this.cat1 = cat1;
        this.cat2 = cat2;
        this.comboTemplateCat = cat3;

        this.comboTemplate = comboTemplate;
        this.comboProduct1 = comboItem1.product_id;
        this.comboProduct2 = comboItem2.product_id;

        this.testProduct1 = testProduct1;
        this.testProduct2 = testProduct2;
    });

    test("all matching lines", async () => {
        this.posPrinter.product_categories_ids = [this.cat1, this.cat2];
        await this.store.ticketPrinter.printOrderChanges({ order: this.store.currentOrder });
        const orderLines = this.getPrintedOrderLines();
        expect(orderLines.length).toBe(5);
        expect(orderLines[0]).toInclude(this.comboTemplate.name);
        expect(orderLines[1]).toInclude(this.comboProduct2.name);
        expect(orderLines[2]).toInclude(this.comboProduct1.name);
        expect(orderLines[3]).toInclude(this.testProduct1.name);
        expect(orderLines[4]).toInclude(this.testProduct2.name);
    });

    test("combo lines and other lines are filtered cat1", async () => {
        this.posPrinter.product_categories_ids = [this.cat1];
        await this.store.ticketPrinter.printOrderChanges({ order: this.store.currentOrder });
        const orderLines = this.getPrintedOrderLines();
        expect(orderLines.length).toBe(3);
        expect(orderLines[0]).toInclude(this.comboTemplate.name);
        expect(orderLines[1]).toInclude(this.comboProduct1.name);
        expect(orderLines[2]).toInclude(this.testProduct1.name);
    });

    test("combo lines and other lines are filtered cat2", async () => {
        this.posPrinter.product_categories_ids = [this.cat2];
        await this.store.ticketPrinter.printOrderChanges({ order: this.store.currentOrder });
        const orderLines = this.getPrintedOrderLines();
        expect(orderLines.length).toBe(3);
        expect(orderLines[0]).toInclude(this.comboTemplate.name);
        expect(orderLines[1]).toInclude(this.comboProduct2.name);
        expect(orderLines[2]).toInclude(this.testProduct2.name);
    });

    test("no category matches", async () => {
        const cat = this.store.models["pos.category"].create({
            id: 999,
            name: "Unmatched Category",
        });
        this.posPrinter.product_categories_ids = [cat];
        await this.store.ticketPrinter.printOrderChanges({ order: this.store.currentOrder });
        expect(this.printedData.length).toBe(0);
    });

    test("ignores combo root category", async () => {
        // The combo root category is not taken into account for printing, only the categories of the combo items are.
        this.posPrinter.product_categories_ids = [this.comboTemplateCat];
        await this.store.ticketPrinter.printOrderChanges({ order: this.store.currentOrder });
        const orderLines = this.getPrintedOrderLines();
        expect(orderLines.length).toBe(1);
        expect(orderLines[0]).toInclude(this.testProduct2.name);
    });
});

test("orderLineNotSend", async () => {
    const store = await setupSelfPosEnv();

    expect(store.orderLineNotSend).toMatchObject({
        priceWithTax: 0,
        priceWithoutTax: 0,
        count: 0,
        tax: 0,
    });
    await getFilledSelfOrder(store);
    expect(store.orderLineNotSend).toMatchObject({
        priceWithTax: 595,
        priceWithoutTax: 500,
        count: 5,
        tax: 95,
    });

    const product1 = store.models["product.template"].get(5);
    await store.addToCart(product1, 1);
    expect(store.orderLineNotSend).toMatchObject({
        priceWithTax: 710,
        priceWithoutTax: 600,
        count: 6,
        tax: 110,
    });
});

test("orderLineNotSend only prices the pending delta once a line has already been sent", async () => {
    const store = await setupSelfPosEnv();
    await getFilledSelfOrder(store);

    await store.sendDraftOrderToServer();
    expect(store.orderLineNotSend).toMatchObject({
        priceWithTax: 0,
        priceWithoutTax: 0,
        count: 0,
        tax: 0,
    });

    const product1 = store.models["product.template"].get(5);
    await store.addToCart(product1, 1);
    expect(store.orderLineNotSend).toMatchObject({
        priceWithTax: 115,
        priceWithoutTax: 100,
        count: 1,
        tax: 15,
    });
});

test("orderLineSent", async () => {
    const store = await setupSelfPosEnv();

    expect(store.orderLineSent).toMatchObject({
        priceWithTax: 0,
        priceWithoutTax: 0,
        count: 0,
        tax: 0,
    });

    await getFilledSelfOrder(store);
    expect(store.orderLineSent).toMatchObject({
        priceWithTax: 0,
        priceWithoutTax: 0,
        count: 0,
        tax: 0,
    });

    await store.sendDraftOrderToServer();
    expect(store.orderLineSent).toMatchObject({
        priceWithTax: 595,
        priceWithoutTax: 500,
        count: 5,
        tax: 95,
    });

    const product1 = store.models["product.template"].get(5);
    await store.addToCart(product1, 1);
    expect(store.orderLineSent).toMatchObject({
        priceWithTax: 595,
        priceWithoutTax: 500,
        count: 5,
        tax: 95,
    });
});

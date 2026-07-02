import { expect, test, describe } from "@odoo/hoot";
import { getRelatedModelsInstance } from "../data/get_model_definitions";
import { makeMockServer } from "@web/../tests/web_test_helpers";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

describe(`Related models Events`, () => {
    test("Connecting multiple records must fire update once", async () => {
        await makeMockServer();
        const models = getRelatedModelsInstance(false);
        const order = models["pos.order"].create({});
        const line1 = models["pos.order.line"].create({});
        const line2 = models["pos.order.line"].create({});
        const orderUpdates = [];
        const linesUpdates = [];

        models["pos.order"].addEventListener("update", (data) => {
            orderUpdates.push(data);
        });

        models["pos.order.line"].addEventListener("update", (data) => {
            linesUpdates.push(data);
        });

        expect(orderUpdates.length).toBe(0);

        order.update({ lines: [line1, line2], amount_total: 10 });
        expect(orderUpdates.length).toBe(1);
        expect(orderUpdates[0].id).toEqual(order.id);
        expect(orderUpdates[0].fields).toEqual(["lines", "amount_total"]);

        expect(linesUpdates.length).toBe(2);
        expect(linesUpdates[0].fields).toEqual(["order_id"]);
    });

    test("Loading data", async () => {
        await makeMockServer();
        const models = getRelatedModelsInstance(false);
        let orderCreates = [];
        let orderUpdates = [];

        models["pos.order"].addEventListener("create", (data) => orderCreates.push(data));
        models["pos.order"].addEventListener("update", (data) => orderUpdates.push(data));

        const order1 = models["pos.order"].create({});
        expect(orderCreates).toEqual([{ ids: [order1.id] }]);

        orderCreates = [];
        orderUpdates = [];

        models.connectNewData({
            "pos.order": [{ id: 1, uuid: order1.uuid }, { id: 2 }, { id: 3 }],
        });

        expect(orderUpdates).toEqual([{ id: order1.id, fields: ["id", "uuid"] }]);
        expect(orderCreates).toEqual([{ ids: [2, 3] }]);

        orderCreates = [];
        orderUpdates = [];

        models._syncId = "test-sync-id";
        models.connectNewData({
            "pos.order": [{ id: 1, uuid: order1.uuid }, { id: 4 }],
        });

        expect(orderUpdates).toEqual([
            { id: order1.id, fields: ["id", "uuid"], syncId: "test-sync-id" },
        ]);
        expect(orderCreates).toEqual([{ ids: [4], syncId: "test-sync-id" }]);
        models._syncId = null;
    });

    test("Connecting new data", async () => {
        await makeMockServer();
        const models = getRelatedModelsInstance(false);
        const order1 = models["pos.order"].create({ id: 3333 });
        const orderUpdates = [];
        const lineUpdates = [];
        const lineCreates = [];

        models["pos.order"].addEventListener("update", (data) => {
            orderUpdates.push(data);
        });

        models["pos.order.line"].addEventListener("create", (data) => {
            lineCreates.push(data);
        });

        models["pos.order.line"].addEventListener("update", (data) => {
            lineUpdates.push(data);
        });

        models.connectNewData({
            "pos.order.line": [
                {
                    id: 1,
                    order_id: order1.id,
                },
            ],
        });

        expect(orderUpdates.length).toBe(1); // The new line is connected to the order and updates it
        expect(lineUpdates.length).toBe(0);
        expect(lineCreates.length).toBe(1);
    });

    test("generateSyncId", async () => {
        await makeMockServer();
        const models = getRelatedModelsInstance(false);
        expect(models._syncId).toBe(null);

        const id = models.generateSyncId();

        expect(typeof id).toBe("string");
        expect(id).toHaveLength(36);
        expect(models._syncId).toBe(id);
        models._syncId = null;
    });

    test("clearSyncId", async () => {
        await makeMockServer();
        const models = getRelatedModelsInstance(false);
        models._syncId = "test-sync-id";

        models.clearSyncId();

        expect(models._syncId).toBe(null);
        models._syncId = null;
    });

    test("Delete record", async () => {
        await makeMockServer();
        const models = getRelatedModelsInstance(false);
        let orderUpdates = [];
        const orderDeletes = [];
        const order = models["pos.order"].create({});

        models["pos.order"].addEventListener("update", (data) => {
            orderUpdates.push(data);
        });

        models["pos.order"].addEventListener("delete", (data) => {
            orderDeletes.push(data);
        });

        const linesUpdates = [];
        models["pos.order.line"].create({ order_id: order.id });
        models["pos.order.line"].create({ order_id: order.id });
        models["pos.order.line"].addEventListener("update", (data) => {
            linesUpdates.push(data);
        });

        expect(orderUpdates.length).toBe(2); // connecting lines to order
        expect(orderDeletes.length).toBe(0);
        expect(linesUpdates.length).toBe(0);

        orderUpdates = [];
        order.delete();
        expect(orderDeletes.length).toBe(1);
        expect(orderUpdates.length).toBe(0);
        expect(linesUpdates.length).toBe(2);
        expect(linesUpdates[0].fields).toEqual(["order_id"]);
    });
});

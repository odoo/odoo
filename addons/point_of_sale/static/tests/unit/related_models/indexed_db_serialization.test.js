import { expect, test, describe } from "@odoo/hoot";
import { SERIALIZED_UI_STATE_PROP } from "@point_of_sale/app/models/related_models/utils";
import { getRelatedModelsInstance } from "../data/get_model_definitions";
import { makeMockServer } from "@web/../tests/web_test_helpers";

describe("IndexedDB serialization", () => {
    test("newly created record", async () => {
        await makeMockServer();
        const models = getRelatedModelsInstance(false);
        const order = models["pos.order"].create({ amount_total: 10 });
        const line1 = models["pos.order.line"].create({
            order_id: order,
            qty: 1,
        });
        const line2 = models["pos.order.line"].create({
            order_id: order,
            qty: 2,
        });
        {
            const result = order.serializeForIndexedDB();
            expect(result.id).toBe(order.id);
            expect(result.amount_total).toBe(order.amount_total);
            expect(Array.isArray(result.lines)).toBe(true);
            expect(result.lines.length).toBe(2);
            expect(result.lines[0]).toBe(line1.id);
            expect(result.lines[1]).toBe(line2.id);
            expect(result[SERIALIZED_UI_STATE_PROP]).toBeEmpty();
        }

        {
            const result = line1.serializeForIndexedDB();
            expect(result.id).toBe(line1.id);
            expect(result.qty).toBe(1);
            expect(result[SERIALIZED_UI_STATE_PROP]).toBeEmpty();
        }
    });

    test("UIState serialization", async () => {
        await makeMockServer();
        const models = getRelatedModelsInstance(false);
        const order = models["pos.order"].create({ amount_total: 10 });
        order.uiState = { demoValue: 99 };

        const result = order.serializeForIndexedDB();
        expect(result.id).toBe(order.id);
        expect(result.amount_total).toBe(10);
        expect(result[SERIALIZED_UI_STATE_PROP]).not.toBeEmpty();
        expect(typeof result[SERIALIZED_UI_STATE_PROP]).toBe("string");
    });

    test("Restore serialized data", async () => {
        await makeMockServer();
        const models = getRelatedModelsInstance();
        const storedData = {
            "pos.order": [
                {
                    [SERIALIZED_UI_STATE_PROP]: '{"demoValue":999}',
                    total: 10,
                    id: 99,
                    lines: [11],
                },
            ],

            "pos.order.line": [
                {
                    id: 11,
                    quantity: 9,
                },
            ],
        };

        models.loadConnectedData(storedData);
        const order = models["pos.order"].get(99);
        // UI state is restored
        expect(order.uiState.demoValue).toBe(999);
        // UIState must be excluded from the raw data
        expect(order.raw.uiState).toBeEmpty();
        expect(order.raw.lines).toEqual([11]);

        expect(order.lines[0].id).toBe(11);
        expect(order.lines[0].uiState).toBeEmpty();
    });
});

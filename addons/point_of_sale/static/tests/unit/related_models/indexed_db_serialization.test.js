import { expect, test, describe } from "@odoo/hoot";
import { createRelatedModels } from "@point_of_sale/app/models/related_models";
import { SERIALIZED_UI_STATE_PROP } from "@point_of_sale/app/models/related_models/utils";

const getModels = () =>
    createRelatedModels(
        {
            "pos.order": {
                lines: {
                    name: "lines",
                    model: "pos.order",
                    relation: "pos.order.line",
                    type: "one2many",
                    inverse_name: "order_id",
                },

                total: {
                    name: "total",
                    type: "float",
                },

                uuid: { type: "char" },
            },
            "pos.order.line": {
                order_id: {
                    name: "order_id",
                    model: "pos.order.line",
                    relation: "pos.order",
                    type: "many2one",
                    ondelete: "cascade",
                },

                attribute_ids: {
                    name: "attribute_ids",
                    model: "pos.order.line",
                    relation: "product.attribute",
                    type: "many2many",
                },

                quantity: {
                    name: "quantity",
                    type: "float",
                },

                uuid: { type: "char" },
            },

            "product.attribute": {},
        },
        {},
        {
            dynamicModels: ["pos.order", "pos.order.line"],
            databaseIndex: {
                "pos.order": ["uuid"],
                "pos.order.line": ["uuid"],
            },
            databaseTable: {
                "pos.order": { key: "uuid" },
                "pos.order.line": { key: "uuid" },
            },
        }
    ).models;

describe("IndexedDB serialization", () => {
    test("newly created record", () => {
        const models = getModels();
        const att1 = models["product.attribute"].create({ id: 99 });
        const att2 = models["product.attribute"].create({ id: 999 });
        const order = models["pos.order"].create({ total: 10 });
        const line1 = models["pos.order.line"].create({
            order_id: order,
            quantity: 1,
            attribute_ids: [att1],
        });
        const line2 = models["pos.order.line"].create({
            order_id: order,
            quantity: 2,
            attribute_ids: [att2],
        });
        {
            const result = order.serializeForIndexedDB();
            expect(result.id).toBe(order.id);
            expect(result.total).toBe(order.total);
            expect(Array.isArray(result.lines)).toBe(true);
            expect(result.lines.length).toBe(2);
            expect(result.lines[0]).toBe(line1.id);
            expect(result.lines[1]).toBe(line2.id);
            expect(result[SERIALIZED_UI_STATE_PROP]).toBeEmpty();
        }

        {
            const result = line1.serializeForIndexedDB();
            expect(result.id).toBe(line1.id);
            expect(result.quantity).toBe(1);
            expect(result.attribute_ids).toEqual([99]);
            expect(result[SERIALIZED_UI_STATE_PROP]).toBeEmpty();
        }
    });

    test("UIState serialization", () => {
        const models = getModels();
        const order = models["pos.order"].create({ total: 10 });
        order.uiState = { demoValue: 99 };

        const result = order.serializeForIndexedDB();
        expect(result.id).toBe(order.id);
        expect(result.total).toBe(10);
        expect(result[SERIALIZED_UI_STATE_PROP]).not.toBeEmpty();
        expect(typeof result[SERIALIZED_UI_STATE_PROP]).toBe("string");
    });

    test("Restore serialized data", () => {
        const models = getModels();
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

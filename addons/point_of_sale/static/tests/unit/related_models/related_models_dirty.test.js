import { expect, test, describe } from "@odoo/hoot";
import { uuidv4 } from "@point_of_sale/utils";
import { getRelatedModelsInstance } from "../data/get_model_definitions";
import { makeMockServer } from "@web/../tests/web_test_helpers";
import { definePosModels } from "../data/generate_model_definitions";

const { DateTime } = luxon;

definePosModels();

describe("Dirty record", () => {
    test("field update", async () => {
        await makeMockServer();
        const models = getRelatedModelsInstance(false);
        const order = models["pos.order"].create({});
        expect(order.isDirty()).toBe(true);
        order.amount_total = 23.5;
        models.serializeForORM(order, { orm: true });

        // Setting the same value must not mark the record as dirty.
        expect(order.isDirty()).toBe(false);
        order.amount_total = 23.5;
        expect(order.isDirty()).toBe(false);
        order.amount_total = 25;
        expect(order.isDirty()).toBe(true);
        models.serializeForORM(order, { orm: true });
        expect(order.isDirty()).toBe(false);

        order.update({ amount_total: 26 });
        expect(order.isDirty()).toBe(true);
    });

    test("model creation", async () => {
        // Models created with a numeric ID are not considered dirty by default
        await makeMockServer();
        const models = getRelatedModelsInstance(false);
        const order = models["pos.order"].create({ id: 12 });
        expect(order.isDirty()).toBe(false);

        order.amount_total = 23.5;
        expect(order.isDirty()).toBe(true);
    });

    test("load data", async () => {
        await makeMockServer();
        const models = getRelatedModelsInstance(false);
        const sampleUUID = uuidv4();

        // When loading data, the dirty flag must not be updated.
        models.loadConnectedData({
            "pos.order": [
                {
                    id: 13,
                    amount_total: 30,
                    uuid: sampleUUID,
                },
            ],
        });

        const order = models["pos.order"].getBy("uuid", sampleUUID);
        expect(order.id).toBe(13);
        expect(order.amount_total).toBe(30);
        expect(order.isDirty()).toBe(false);
    });

    test("related record update", async () => {
        await makeMockServer();
        const models = getRelatedModelsInstance(false);
        const order = models["pos.order"].create({ id: 12 });
        expect(order.isDirty()).toBe(false);

        function clearOrder() {
            models.serializeForORM(order, { orm: true });
            expect(order.isDirty()).toBe(false);
        }

        // Add new line to the order
        const line = models["pos.order.line"].create({
            qty: 1,
            order_id: order,
        });
        expect(line.isDirty()).toBe(true);
        expect(order.isDirty()).toBe(true);
        clearOrder();
        expect(line.isDirty()).toBe(false);

        // Assign a product to the line
        const sampleProduct = models["product.product"].create({ name: "demo_product", id: 111 });
        line.product_id = sampleProduct;
        expect(line.isDirty()).toBe(true);
        expect(order.isDirty()).toBe(true);
        clearOrder();
        expect(line.isDirty()).toBe(false);

        // Update line quantity
        line.qty = 10;
        expect(line.isDirty()).toBe(true);
        expect(order.isDirty()).toBe(true);
        clearOrder();

        order.lines[0].qty = 1000;
        expect(line.isDirty()).toBe(true);
        expect(order.isDirty()).toBe(true);
        clearOrder();

        // Delete product from line
        line.product_id = null;
        expect(order.isDirty()).toBe(true);
        clearOrder();

        line.delete();
        expect(order.isDirty()).toBe(true);
        expect(order.lines.length).toBe(0);
    });

    test("many2many", async () => {
        await makeMockServer();
        const models = getRelatedModelsInstance(false);
        const order = models["pos.order"].create({ id: 12 });
        function clearOrder() {
            models.serializeForORM(order, { orm: true });
            expect(order.isDirty()).toBe(false);
        }
        const att1 = models["product.template.attribute.value"].create({ id: 99 });
        const line = models["pos.order.line"].create({ id: 100, order_id: order, qty: 1 });
        line.update({ attribute_value_ids: [["link", att1]] });
        expect(line.isDirty()).toBe(true);
        expect(order.isDirty()).toBe(true);

        clearOrder();
        const att2 = models["product.template.attribute.value"].create({ id: 999 });
        line.update({ attribute_value_ids: [["link", att2]] });
        expect(line.isDirty()).toBe(true);
        expect(order.isDirty()).toBe(true);

        clearOrder();
        line.update({ attribute_value_ids: [["unlink", att1]] });
        expect(line.isDirty()).toBe(true);
        expect(order.isDirty()).toBe(true);
    });

    test("datetime type", async () => {
        await makeMockServer();
        const models = getRelatedModelsInstance(false);
        const order = models["pos.order"].create({ id: 12 });
        function clearOrder() {
            models.serializeForORM(order, { orm: true });
            expect(order.isDirty()).toBe(false);
        }
        expect(order.isDirty()).toBe(false);

        order.date_order = undefined;
        expect(order.isDirty()).toBe(false);

        // Other valid DateTime
        clearOrder();
        order.date_order = DateTime.local(2025, 1, 1, 9, 30);
        expect(order.isDirty()).toBe(true);

        // Same DateTime
        clearOrder();
        order.date_order = DateTime.local(2025, 1, 1, 9, 30);
        expect(order.isDirty()).toBe(false);

        // Different DateTime
        clearOrder();
        order.date_order = DateTime.local(2028, 1, 1, 10, 30);
        expect(order.isDirty()).toBe(true);

        // Set to false / null
        clearOrder();
        order.date_order = false;
        expect(order.isDirty()).toBe(true);

        clearOrder();
        order.date_order = null;
        expect(order.isDirty()).toBe(false);
    });
});

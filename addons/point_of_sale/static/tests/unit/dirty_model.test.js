import { expect, test } from "@odoo/hoot";
import { createRelatedModels } from "@point_of_sale/app/models/related_models";
import { uuidv4 } from "@point_of_sale/utils";

const getModels = () =>
    createRelatedModels(
        {
            "pos.order": {
                price: {
                    name: "price",
                    type: "float",
                },
                lines: {
                    name: "lines",
                    model: "pos.order",
                    relation: "pos.order.line",
                    type: "one2many",
                    inverse_name: "order_id",
                },
                uuid: {
                    name: "uuid",
                    type: "char",
                },
            },
            "pos.order.line": {
                order_id: {
                    name: "order_id",
                    model: "pos.order.line",
                    relation: "pos.order",
                    type: "many2one",
                    ondelete: "cascade",
                },
                quantity: {
                    name: "quantity",
                    type: "float",
                },

                product_id: {
                    name: "product_id",
                    model: "pos.order.line",
                    relation: "pos.product",
                    type: "many2one",
                },
                uuid: {
                    name: "uuid",
                    type: "char",
                },
            },

            "pos.product": {
                name: {
                    name: "name",
                    type: "char",
                },
            },
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

test("field update", () => {
    const models = getModels();
    const order = models["pos.order"].create({});
    expect(order.isDirty()).toBe(true);
    order.price = 23.5;
    order.serialize({ orm: true, clear: true });
    // Setting the same value must not mark the record as dirty.
    expect(order.isDirty()).toBe(false);
    order.price = 23.5;
    expect(order.isDirty()).toBe(false);
    order.price = 25;
    expect(order.isDirty()).toBe(true);
    order.serialize({ orm: true, clear: true });
    expect(order.isDirty()).toBe(false);

    order.update({ price: 26 });
    expect(order.isDirty()).toBe(true);
});

test("model creation", () => {
    const models = getModels();
    // Models created with a numeric ID are not considered dirty by default
    const order = models["pos.order"].create({ id: 12 });
    expect(order.isDirty()).toBe(false);

    order.price = 23.5;
    expect(order.isDirty()).toBe(true);
});

test("load data", () => {
    const models = getModels();
    const sampleUUID = uuidv4();

    // When loading data, the dirty flag must not be updated.
    models.loadData({
        "pos.order": [
            {
                id: 13,
                price: 30,
                uuid: sampleUUID,
            },
        ],
    });

    const order = models["pos.order"].getBy("uuid", sampleUUID);
    expect(order.id).toBe(13);
    expect(order.price).toBe(30);
    expect(order.isDirty()).toBe(false);
});

test("related record update", () => {
    const models = getModels();

    const order = models["pos.order"].create({ id: 12 });
    expect(order.isDirty()).toBe(false);

    function clearOrder() {
        order.serialize({ orm: true, clear: true });
        expect(order.isDirty()).toBe(false);
    }

    // Add new line to the order
    const line = models["pos.order.line"].create({
        quantity: 1,
        order_id: order,
    });
    expect(line.isDirty()).toBe(true);
    expect(order.isDirty()).toBe(true);
    clearOrder();
    expect(line.isDirty()).toBe(false);

    // Assign a product to the line
    const sampleProduct = models["pos.product"].create({ name: "demo_product", id: 111 });
    line.product_id = sampleProduct;
    expect(line.isDirty()).toBe(true);
    expect(order.isDirty()).toBe(true);
    clearOrder();
    expect(line.isDirty()).toBe(false);

    // Update line quantity
    line.quantity = 10;
    expect(line.isDirty()).toBe(true);
    expect(order.isDirty()).toBe(true);
    clearOrder();

    order.lines[0].quantity = 1000;
    expect(line.isDirty()).toBe(true);
    expect(order.isDirty()).toBe(true);
    clearOrder();

    // Delete product from line
    sampleProduct.delete();
    expect(order.isDirty()).toBe(true);
    clearOrder();

    line.delete();
    expect(order.isDirty()).toBe(true);
    expect(order.lines.length).toBe(0);
});

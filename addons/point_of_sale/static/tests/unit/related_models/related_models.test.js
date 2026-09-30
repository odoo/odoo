import { expect, test, describe } from "@odoo/hoot";
import { createRelatedModels, Base } from "@point_of_sale/app/models/related_models";
import { serializeDateTime } from "@web/core/l10n/dates";
import { SERIALIZED_UI_STATE_PROP } from "@point_of_sale/app/models/related_models/utils";
import { getModelDefinitions, getRelatedModelsInstance } from "../data/get_model_definitions";
import { makeMockServer } from "@web/../tests/web_test_helpers";
import { definePosModels } from "../data/generate_model_definitions";

const { DateTime } = luxon;

definePosModels();

describe("Related Model", () => {
    test("Create simple model object", async () => {
        await makeMockServer();
        const models = getRelatedModelsInstance(false);
        const order = models["pos.order"].create({
            amount_total: 12,
        });

        // Id and uuid are generated
        expect(order.id).not.toBeEmpty();
        expect(order.isSynced).toBe(false);
        expect(order.uuid).not.toBeEmpty();

        // The generated id and uuid must be the same
        expect(order.id).toBe(order.uuid);

        expect(order.amount_total).toBe(12);
        order.amount_total = 20;
        expect(order.amount_total).toBe(20);

        // ID is generated even if no UUIDs are available.
        const attr = models["product.attribute"].create({});
        expect(attr.id).not.toBeEmpty();
    });

    test("Keep raw datas not defined in models fields", async () => {
        await makeMockServer();
        const models = getRelatedModelsInstance(false);
        models.loadConnectedData({
            "pos.order": [
                {
                    id: 1,
                    extraField: "Value",
                    _extra: "1",
                },
            ],
        });
        const order = models["pos.order"].get(1);
        expect(order.raw.extraField).toBe("Value");
        expect(order.extraField).toBe(undefined);
        expect(order.raw._extra).toBe("1");
        expect(order._extra).toBe("1"); //shortcut to raw data

        // Update (same order id)
        models.connectNewData({
            "pos.order": [
                {
                    id: 1,
                    extraField: "Value 2",
                    extraField2: "Value 3",
                    _extra: "2",
                    uuid: order.uuid,
                },
            ],
        });

        expect(order.raw.extraField).toBe("Value 2");
        expect(order.extraField).toBe(undefined);
        expect(order.raw.extraField2).toBe("Value 3");
        expect(order.extraField2).toBe(undefined);
        expect(order.raw._extra).toBe("2");
        expect(order._extra).toBe("2");

        // Manual record creation, raw data contains only the model fields
        const order2 = models["pos.order"].create({
            amount_total: 12,
            _additionalField: "Sample value",
            otherField: "Value 2",
        });

        expect(order2.raw.amount_total).toBe(12);
        expect(order2.amount_total).toBe(12);
        expect(order2.raw._additionalField).toBe(undefined);
        expect(order2._additionalField).toBe("Sample value");
        expect(order2.otherField).toBe(undefined);
        expect(order2.raw.otherField).toBe(undefined);
    });

    test("Ensure raw data is immutable", async () => {
        await makeMockServer();
        const models = getRelatedModelsInstance(false);
        models["pos.order.line"].create({
            id: 1,
            name: "Hello",
        });

        const order = models["pos.order"].create({
            amount_total: 12,
            lines: [1],
        });

        expect(order.raw.lines.length).toBe(1);
        expect(order.raw.lines[0]).toBe(1);

        expect(() => {
            order.raw.amount_total = 99;
        }).toThrow(/cannot be modified/i);

        expect(() => {
            order.raw = {};
        }).toThrow();

        expect(() => {
            order.raw.lines.push("a");
        }).toThrow(/cannot be modified/i);

        expect(() => {
            order.raw.lines[0] = "hello";
        }).toThrow(/cannot be modified/i);
    });

    test("one2many creation (by ids)", async () => {
        await makeMockServer();
        const models = getRelatedModelsInstance(false);
        const createdLine = models["pos.order.line"].create({
            id: 11,
        });

        const order = models["pos.order"].create({ id: 99, lines: [11], name: "Hello" });
        const line = order.lines[0];
        expect(line.id).toBe(11);
        expect(order.name).toBe("Hello");
        expect(line.order_id).toBe(order);
        expect(line.order_id.id).toBe(99);
        expect(line.qty).toBe(undefined);

        expect(line).toBe(createdLine);

        // Update child record
        order.name = "Hello world";
        expect(order.name).toBe("Hello world");

        order.name = "Hello 2";
        expect(order.name).toBe("Hello 2");

        createdLine.qty = 20;
        expect(order.lines[0].qty).toBe(20);
    });

    test("one2many creation", async () => {
        // Create an empty order
        await makeMockServer();
        const models = getRelatedModelsInstance(false);
        const order = models["pos.order"].create({});

        // Add line top order
        models["pos.order.line"].create({ order_id: order, full_product_name: "Line 1" });
        expect(order.lines.length).toBe(1);
        expect(order.lines[0].full_product_name).toBe("Line 1");

        // Use order id to link the line
        models["pos.order.line"].create({ order_id: order.id, full_product_name: "Line 2" });
        expect(order.lines.length).toBe(2);
        expect(order.lines[1].full_product_name).toBe("Line 2");

        // Disconnect the  line
        const line = order.lines[0];
        line.order_id = null;
        expect(order.lines.length).toBe(1);
        expect(order.lines[0].full_product_name).toBe("Line 2");

        // Assign the line to another order
        const order2 = models["pos.order"].create({});
        expect(order2.lines.length).toBe(0);
        order.lines[0].order_id = order2;
        expect(order2.lines.length).toBe(1);
        expect(order.lines.length).toBe(0);
        expect(order2.lines[0].full_product_name).toBe("Line 2");

        line.order_id = order2.id; //Assign by id
        expect(order2.lines.length).toBe(2);
        expect(order2.lines[1].full_product_name).toBe("Line 1");
    });

    test("x2many array is not modifiable", async () => {
        await makeMockServer();
        const models = getRelatedModelsInstance(false);
        const order = models["pos.order"].create({});

        expect(() => {
            order.lines.push("a");
        }).toThrow(/cannot be modified/i);
    });

    test("one2many update", async () => {
        await makeMockServer();
        const models = getRelatedModelsInstance(false);
        const line1 = models["pos.order.line"].create({ full_product_name: "Line 1" });
        const line2 = models["pos.order.line"].create({ full_product_name: "Line 2" });
        const line3 = models["pos.order.line"].create({ full_product_name: "Line 3" });

        const order = models["pos.order"].create({ lines: [["link", line1, line2]] });
        expect(order.lines.length).toBe(2);
        expect(order.lines[0].order_id).toBe(order);

        // Unlink
        order.update({ lines: [["unlink", line1]] });
        expect(order.lines.length).toBe(1);
        expect(line1.order_id).toBeEmpty();

        // Link
        order.update({ lines: [["link", line1]] }); //add a line
        expect(order.lines.length).toBe(2);
        expect(order.lines[1].full_product_name).toBe("Line 1");
        expect(order.lines[1].order_id).toBe(order);

        // Clear
        order.update({ lines: [["clear"]] });
        expect(order.lines.length).toBe(0);
        expect(line1.order_id).toBeEmpty();

        // Set
        order.update({ lines: [["link", line1]] });
        expect(order.lines.length).toBe(1);
        order.update({ lines: [["set", line2, line3]] });
        expect(order.lines.length).toBe(2);
        expect(order.lines[0].full_product_name).toBe("Line 2");
        expect(order.lines[0].order_id).toBe(order);
        expect(order.lines[1].full_product_name).toBe("Line 3");
        expect(order.lines[1].order_id).toBe(order);
        expect(line1.order_id).toBeEmpty(); //line 1 disconnected

        // Create
        order.update({ lines: [["create", { full_product_name: "Line new" }]] });
        expect(order.lines.length).toBe(3);
        expect(order.lines[2].full_product_name).toBe("Line new");
        expect(order.lines[2].order_id).toBe(order);

        // Test set default value
        order.update({ lines: [line1] });
        expect(order.lines.length).toBe(1);
    });

    test("many2one delete", async () => {
        await makeMockServer();
        const models = getRelatedModelsInstance(false);
        const order = models["pos.order"].create({});
        const line = models["pos.order.line"].create({ order_id: order, name: "Line 1" });
        expect(order.lines.length).toBe(1);

        expect(models["pos.order.line"].get(line.id)).not.toBeEmpty();
        expect(models["pos.order.line"].getBy("uuid", line.uuid)).not.toBeEmpty();

        line.delete();
        expect(order.lines.length).toBe(0);

        expect(models["pos.order.line"].get(line.id)).toBeEmpty();
        expect(models["pos.order.line"].getBy("uuid", line.uuid)).toBeEmpty();
    });

    test("many2many test", async () => {
        await makeMockServer();
        const models = getRelatedModelsInstance(false);
        const l1 = models["pos.order.line"].create({});
        const l2 = models["pos.order.line"].create({});
        const l3 = models["pos.order.line"].create({});

        {
            const o1 = models["pos.order"].create({
                lines: [l1, l2, l3],
            });
            expect(l1.order_id).toBe(o1);
            expect(l2.order_id).toBe(o1);
            expect(l3.order_id).toBe(o1);
        }

        {
            // Assign attribute upon creation using ids
            const l1 = models["pos.order.line"].create({});
            const l2 = models["pos.order.line"].create({});
            const l3 = models["pos.order.line"].create({});
            const o1 = models["pos.order"].create({
                lines: [l1.id, l2.id, l3.id],
            });
            expect(l1.order_id).toBe(o1);
            expect(l2.order_id).toBe(o1);
            expect(l3.order_id).toBe(o1);
        }

        {
            // Assign attribute upon creation using link command
            const o1 = models["pos.order"].create({
                lines: [["link", l1, l2, l3]],
            });
            expect(l1.order_id).toBe(o1);
            expect(l2.order_id).toBe(o1);
            expect(l3.order_id).toBe(o1);
        }

        {
            // Assign attribute upon creation using create command
            const o1 = models["pos.order"].create({
                lines: [
                    ["create", { full_product_name: "Line 1" }],
                    ["create", { full_product_name: "Line 2" }],
                ],
            });
            expect(o1.lines.length).toBe(2);
        }

        {
            // Manage attribute_ids using the update method
            const o1 = models["pos.order"].create({});
            const line = models["pos.order.line"].create({ full_product_name: "Line 1" });
            line.update({ order_id: o1 });
            expect(line.order_id).toBe(o1);

            const l1 = models["pos.order.line"].create({});
            const l2 = models["pos.order.line"].create({});
            o1.update({ lines: [["set", l1, l2]] });
            expect(o1.lines.length).toBe(2);
            expect(o1.lines).toInclude(l1);
            expect(o1.lines).toInclude(l2);

            o1.update({ lines: [["unlink", l1]] });
            expect(o1.lines.length).toBe(1);
            expect(o1.lines).toInclude(l2);

            l2.update({ order_id: [] });
            expect(o1.lines.length).toBe(0);
        }
    });

    test("x2many allow setter", async () => {
        await makeMockServer();
        const models = getRelatedModelsInstance(false);
        const line1 = models["pos.order.line"].create({ id: 11, full_product_name: "Line 1" });
        const line2 = models["pos.order.line"].create({ id: 12, full_product_name: "Line 2" });

        {
            //Link command
            const order = models["pos.order"].create({});
            order.lines = [["link", line1, line2.id]];
            expect(order.lines.length).toBe(2);
            expect(order.lines[0]).toBe(line1);
            expect(order.lines[1]).toBe(line2);
            expect(line1.order_id).toBe(order);
            expect(line2.order_id).toBe(order);
        }

        {
            // No command
            const order = models["pos.order"].create({});
            order.lines = [line1, line2.id];
            expect(order.lines.length).toBe(2);
            expect(order.lines[0]).toBe(line1);
            expect(order.lines[1]).toBe(line2);
            expect(line1.order_id).toBe(order);
            expect(line2.order_id).toBe(order);
        }

        {
            // MIX
            const order = models["pos.order"].create({});
            order.lines = [line1, ["link", line2.id], ["create", { full_product_name: "Line 3" }]];
            expect(order.lines.length).toBe(3);
            expect(order.lines[0]).toBe(line1);
            expect(order.lines[1]).toBe(line2);
            expect(order.lines[2].full_product_name).toBe("Line 3");
            expect(line1.order_id).toBe(order);
            expect(line2.order_id).toBe(order);
            expect(order.lines[2].order_id).toBe(order);
        }

        {
            // Empty
            const order = models["pos.order"].create({});
            order.lines = [line1, line2];
            expect(order.lines.length).toBe(2);
            order.lines = [];
            expect(order.lines.length).toBe(0);
            expect(line1.order_id).toBeEmpty();
            expect(line2.order_id).toBeEmpty();
        }
    });

    test("Load data without connect", async () => {
        await makeMockServer();
        const models = getRelatedModelsInstance(false);
        const result = models.loadConnectedData(
            {
                "pos.order": [
                    {
                        id: 1,
                        total: 10,
                        lines: [11, 12],
                        uuid: "42eb4cc3-2ec8-4a0b-9bca-0a2d8a98178c",
                    },
                ],

                "pos.order.line": [
                    {
                        id: 11,
                        order_id: 1,
                        full_product_name: "Line 1",
                        uuid: "5d3273af-c0f1-4008-9a1f-353841cf1a73",
                    },
                    {
                        id: 12,
                        order_id: 1,
                        full_product_name: "Line 2",
                        uuid: "0b6d3b25-3d5d-41a1-9357-059231a3cd82",
                    },
                ],
            },
            []
        );

        const order = models["pos.order"].get(1);
        expect(result["pos.order"][0]).toBe(order);
        expect(order.lines.length).toBe(2);
        expect(order.lines[0].full_product_name).toBe("Line 1");
        expect(order.lines[1].full_product_name).toBe("Line 2");
        const line2 = order.lines[1];
        expect(line2.order_id).toBe(order);
        models.loadConnectedData({
            "pos.order": [
                { id: 1, total: 10, lines: [12], uuid: "42eb4cc3-2ec8-4a0b-9bca-0a2d8a98178c" },
            ],
            "pos.order.line": [
                {
                    id: 12,
                    order_id: 1,
                    full_product_name: "Line 2",
                    uuid: "0b6d3b25-3d5d-41a1-9357-059231a3cd82",
                },
            ],
        });

        //The same order object
        const order2 = models["pos.order"].get(1);
        expect(order2).toBe(order);
        expect(order2.lines.length).toBe(1);
        expect(order2.lines[0]).toBe(line2);
    });

    test("Load data & connect records", async () => {
        await makeMockServer();
        const models = getRelatedModelsInstance(false);
        const result = models.connectNewData({
            "pos.order.line": [
                {
                    id: 11,
                    order_id: 1,
                    full_product_name: "Line 1",
                    uuid: "5d3273af-c0f1-4008-9a1f-353841cf1a73",
                },
                {
                    id: 12,
                    order_id: 1,
                    full_product_name: "Line 2",
                    uuid: "0b6d3b25-3d5d-41a1-9357-059231a3cd82",
                },
            ],
            "pos.order": [
                {
                    id: 1,
                    total: 10,
                    lines: [11, 12],
                    uuid: "42eb4cc3-2ec8-4a0b-9bca-0a2d8a98178c",
                },
            ],
        });

        const order = models["pos.order"].get(1);
        expect(order.lines.length).toBe(2);
        expect(order.lines[0].full_product_name).toBe("Line 1");
        expect(order.lines[1].full_product_name).toBe("Line 2");

        expect(result["pos.order"][0]).toBe(order);
    });

    test("Load data: connect new records", async () => {
        await makeMockServer();
        const models = getRelatedModelsInstance(false);
        const result = models.loadConnectedData({
            "pos.order": [
                {
                    id: 1,
                    total: 10,
                    uuid: "42eb4cc3-2ec8-4a0b-9bca-0a2d8a98178c",
                },
            ],
        });

        const order = models["pos.order"].get(1);
        expect(order.lines.length).toBe(0);

        models.connectNewData({
            "pos.order.line": [
                {
                    id: 11,
                    order_id: 1,
                    uuid: "5d3273af-c0f1-4008-9a1f-353841cf1a73",
                },
                {
                    id: 12,
                    order_id: 1,
                    uuid: "0b6d3b25-3d5d-41a1-9357-059231a3cd82",
                },
            ],
        });
        expect(order.lines.length).toBe(2);
        expect(order.lines[0].id).toBe(11);
        expect(order.lines[1].id).toBe(12);

        expect(models["pos.order"].get(1).lines.length).toBe(2);
        expect(result["pos.order"][0]).toBe(order);
    });

    test("Load data: connect records without many2one", async () => {
        // lines without order_id

        await makeMockServer();
        const models = getRelatedModelsInstance(false);
        models.connectNewData({
            "pos.order": [
                {
                    id: 1,
                    total: 10,
                    lines: [11, 12],
                    uuid: "42eb4cc3-2ec8-4a0b-9bca-0a2d8a98178c",
                },
            ],

            "pos.order.line": [
                {
                    id: 11,
                    uuid: "5d3273af-c0f1-4008-9a1f-353841cf1a73",
                },
                {
                    id: 12,
                    uuid: "0b6d3b25-3d5d-41a1-9357-059231a3cd82",
                },
            ],
        });
        const order = models["pos.order"].get(1);
        expect(order.lines.length).toBe(2);
    });

    test("Adding record to the store should not compute getter", async () => {
        await makeMockServer();
        const models = getRelatedModelsInstance(false);
        models.loadConnectedData({
            "pos.order.line": [
                {
                    id: 12,
                    order_id: 1,
                    attribute_ids: [91, 92],
                    uuid: "0b6d3b25-3d5d-41a1-9357-059231a3cd82",
                },
            ],

            "pos.order": [
                {
                    id: 1,
                    lines: [12, 13],
                    table_id: 99,
                },
            ],
        });
        const order = models["pos.order"].get(1);
        const line = models["pos.order.line"].get(12);
        expect(line.order_id).toBe(order);

        expect(order.lines.length).toBe(1); // line 13 is not yet loaded
        expect(order.lines[0].id).toBe(12);
    });

    test("Update newly created records with server data", async () => {
        await makeMockServer();
        const models = getRelatedModelsInstance(false);
        const order = models["pos.order"].create({ total: 30 });
        const line = models["pos.order.line"].create({
            order_id: order,
            full_product_name: "Line 1",
        });
        const oldOrderId = order.id;

        order.sampleData = "test";

        expect(order.lines.length).toBe(1);
        const oldLineId = order.lines[0].id;
        expect(order.isSynced).toBe(false);
        expect(models["pos.order"].get(oldOrderId)).not.toBeEmpty();

        models.connectNewData({
            "pos.order": [{ id: 100, amount_total: 50, lines: [12], uuid: order.uuid }],
            "pos.order.line": [
                {
                    id: 12,
                    order_id: 1,
                    full_product_name: "Line 1111",
                    uuid: line.uuid,
                },
            ],
        });

        expect(order.id).toBe(100);
        expect(order.amount_total).toBe(50);
        expect(order.sampleData).toBe("test");
        expect(order.lines.length).toBe(1);
        expect(order.lines[0]).toBe(line);
        expect(order.lines[0].id).toBe(12);
        expect(order.lines[0].full_product_name).toBe("Line 1111");

        //Find by ids, uuids
        expect(models["pos.order"].get(oldOrderId)).toBe(undefined);
        expect(models["pos.order"].get(order.id)).toBe(order);
        expect(models["pos.order"].getBy("uuid", order.uuid)).toBe(order);

        expect(models["pos.order.line"].get(oldLineId)).toBe(undefined);
        expect(models["pos.order.line"].get(line.id)).toBe(line);
        expect(models["pos.order.line"].getBy("uuid", line.uuid)).toBe(line);
    });

    test("Disallow record id update", async () => {
        await makeMockServer();
        const models = getRelatedModelsInstance(false);
        const order = models["pos.order"].create({ total: 30 });
        expect(order.isSynced).toBe(false);
        expect(models["pos.order"].get(order.id)).toBe(order);
        expect(models["pos.order"].getBy("uuid", order.uuid)).toBe(order);

        const oldId = order.id;
        order.update({ id: 12 });
        expect(order.id).toBe(oldId);

        expect(() => {
            order.id = 12;
        }).toThrow();
    });

    test("Ignoring update for unknown field", async () => {
        await makeMockServer();
        const models = getRelatedModelsInstance(false);
        const order = models["pos.order"].create({ total: 30 });

        expect(() => {
            order.update({ fake_field: 1 });
        }).toThrow();

        order.update({ fake_field: 1 }, { omitUnknownField: true });
        expect(order.fake_field).toBe(undefined);
        expect(order.raw.fake_field).toBe(undefined);
    });

    test("Deleting the root record must disconnect its child records", async () => {
        await makeMockServer();
        const models = getRelatedModelsInstance(false);
        const order = models["pos.order"].create({ total: 30 });
        const line1 = models["pos.order.line"].create({ order_id: order, name: "Line 1" });
        const line2 = models["pos.order.line"].create({ order_id: order, name: "Line 2" });

        expect(models["pos.order"].get(order.id)).toBe(order);
        expect(models["pos.order"].getBy("uuid", order.uuid)).toBe(order);

        order.delete();

        expect(models["pos.order"].get(order.id)).toBe(undefined);
        expect(models["pos.order"].getBy("uuid", order.uuid)).toBe(undefined);

        expect(line1.order_id).toBe(undefined);
        expect(line2.order_id).toBe(undefined);
    });

    test("DateTime in raw data must be stored in server format", async () => {
        await makeMockServer();
        const models = getRelatedModelsInstance(false);
        const orderDate = DateTime.now().set({ second: 0, millisecond: 0 });

        {
            const order = models["pos.order"].create({ total: 30, date_order: orderDate });
            // Stored as server date
            expect(order.raw.date_order).toBe(serializeDateTime(orderDate));
            expect(order.date_order.toMillis()).toBe(orderDate.toMillis());

            // Update date
            const newDate = orderDate.plus({ hours: 1 });
            order.update({ date_order: newDate });
            expect(order.date_order.toMillis()).toBe(newDate.toMillis());
        }

        {
            //Create with server date
            const newOrderDate = orderDate.plus({ hours: 2 });
            const serverValue = serializeDateTime(newOrderDate);
            const order = models["pos.order"].create({
                total: 30,
                date_order: serverValue,
            });
            expect(order.raw.date_order).toBe(serverValue);
            expect(order.date_order.toMillis()).toBe(newOrderDate.toMillis());
        }
    });

    test("Store updates must invalidate getters", async () => {
        await makeMockServer();
        const models = getRelatedModelsInstance(false);
        models.loadConnectedData({
            "pos.order.line": [
                {
                    id: 12,
                    order_id: 1,
                    name: "Line 1",
                    attribute_ids: [91, 92],
                    uuid: "0b6d3b25-3d5d-41a1-9357-059231a3cd82",
                },

                {
                    id: 99,
                    order_id: 2,
                    name: "Line Order2",
                },
            ],
            "pos.order": [
                {
                    id: 1,
                    lines: [12, 13],
                    table_id: 99,
                },
            ],
        });
        const order = models["pos.order"].get(1);
        const line = models["pos.order.line"].get(12);
        expect(line.order_id).toBe(order);

        expect(order.lines.length).toBe(1); // line 13 is not yet loaded  ...

        models.connectNewData({
            "pos.order.line": [
                {
                    id: 13,
                    order_id: 1,
                    name: "Line 1",
                    uuid: "zz3",
                },
            ],
        });
        expect(order.lines.length).toBe(2);
        expect(order.lines[0]).toBe(models["pos.order.line"].get(12));
        expect(order.lines[1]).toBe(models["pos.order.line"].get(13));

        const lineOrder2 = models["pos.order.line"].get(99);
        expect(lineOrder2.order_id).toBeEmpty(); //order 2 is not loaded

        models.connectNewData({
            "pos.order": [
                {
                    id: 2,
                    lines: [99],
                },
            ],
        });
        const order2 = models["pos.order"].get(2);
        expect(lineOrder2.order_id).toBe(order2); //order 2 is not loaded
        expect(order2.lines[0]).toBe(lineOrder2);
    });

    test("Backref lazy loading", async () => {
        await makeMockServer();
        const models = getRelatedModelsInstance(false);
        models.loadConnectedData({
            "product.template.attribute.value": [
                { id: 91, name: "Att 1" },
                { id: 92, name: "Att 2" },
            ],

            "pos.order.line": [
                {
                    id: 12,
                    name: "Line 1",
                    attribute_value_ids: [91, 92],
                    uuid: "0b6d3b25-3d5d-41a1-9357-059231a3cd82",
                },
                {
                    id: 13,
                    name: "Line 2",
                    attribute_value_ids: [92],
                    uuid: "qsdqsdq",
                },
            ],
        });

        const att1 = models["product.template.attribute.value"].get(91);
        const att2 = models["product.template.attribute.value"].get(92);

        const line1 = models["pos.order.line"].get(12);
        const line2 = models["pos.order.line"].get(13);

        {
            let lines = att1.backLink("<-pos.order.line.attribute_value_ids");
            expect(lines.length).toBe(1);
            expect(lines[0]).toBe(line1);

            // Nothing changes, the same lazy result is returned
            const sameLines = att1.backLink("<-pos.order.line.attribute_value_ids");
            expect(sameLines).toBe(lines);

            // Remove attributes
            line1.attribute_value_ids = [];
            lines = att1.backLink("<-pos.order.line.attribute_value_ids");
            expect(lines.length).toBe(0);

            // Add
            line1.attribute_value_ids = [att1, att2];
            lines = att1.backLink("<-pos.order.line.attribute_value_ids");
            expect(lines.length).toBe(1);
            expect(lines[0]).toBe(line1);

            // New Line
            const line3 = models["pos.order.line"].create({ attribute_value_ids: [91] });
            lines = att1.backLink("<-pos.order.line.attribute_value_ids");
            expect(lines.length).toBe(2);
            expect(lines[1]).toBe(line3);

            // Load from backend
            models.connectNewData({
                "pos.order.line": [
                    {
                        id: 14,
                        attribute_value_ids: [91],
                    },
                ],
            });

            lines = att1.backLink("<-pos.order.line.attribute_value_ids");
            expect(lines.length).toBe(3);
            expect(lines[1]).toBe(line3);
            expect(lines[2]).toBe(models["pos.order.line"].get(14));
        }

        {
            let lines = att2.backLink("pos.order.line.attribute_value_ids");
            expect(lines.length).toBe(2);
            expect(lines[0]).toBe(line2);
            expect(lines[1]).toBe(line1);

            line1.delete();
            lines = att2.backLink("pos.order.line.attribute_value_ids");
            expect(lines.length).toBe(1);
            expect(lines[0]).toBe(line2);
        }
    });

    test("Store: multi values index", async () => {
        await makeMockServer();
        const models = getRelatedModelsInstance(false);

        models.loadConnectedData({
            "product.template": [
                { id: 91, pos_categ_ids: [12, 13] },
                { id: 92, pos_categ_ids: [12] },
            ],
            "pos.category": [{ id: 12 }, { id: 13 }],
        });

        let records = models["product.template"].readAllBy("pos_categ_ids");
        const p1 = models["product.template"].get(91);
        const p2 = models["product.template"].get(92);
        expect(Object.keys(records).length).toBe(2);
        expect(records[12]).toHaveLength(2);
        expect(records[12]).toInclude(p1);
        expect(records[12]).toInclude(p2);
        expect(records[13].length).toBe(1);
        expect(records[13]).toInclude(p1);
        expect(records[13]).not.toInclude(p2);

        p1.delete();

        records = models["product.template"].getBy("pos_categ_ids", 12);
        expect(records.length).toBe(1);
        expect(records).toInclude(p2);

        p2.delete();
        records = models["product.template"].getBy("pos_categ_ids", 12);
        expect(records.length).toBe(0);
    });

    test("Store: multi value index update", async () => {
        await makeMockServer();
        const models = getRelatedModelsInstance(false);
        models.loadConnectedData({
            "product.template": [
                { id: 91, pos_categ_ids: [] },
                { id: 92, pos_categ_ids: [] },
            ],
            "pos.category": [{ id: 12 }, { id: 13 }],
        });

        let records = models["product.template"].getAllBy("pos_categ_ids");
        expect(records[12]).toBeEmpty();
        expect(records[13]).toBeEmpty();

        const p1 = models["product.template"].get(91);
        p1.pos_categ_ids = [12];
        records = models["product.template"].getAllBy("pos_categ_ids");
        expect(records[12].length).toBe(1);

        const product = models["product.template"].create({
            id: 93,
            pos_categ_ids: [12, 13],
        });
        records = models["product.template"].getAllBy("pos_categ_ids");
        expect(records[12]).toHaveLength(2);
        expect(records[12]).toInclude(p1);
        expect(records[12]).toInclude(product);

        models.connectNewData({
            "product.template": [
                {
                    id: 94,
                    pos_categ_ids: [12],
                },
            ],
        });
        records = models["product.template"].getAllBy("pos_categ_ids");
        expect(records[12]).toHaveLength(3);
        expect(records[12]).toInclude(p1);
        expect(records[12]).toInclude(product);
        expect(records[12]).toInclude(models["product.template"].get(94));

        // backend updated
        models.connectNewData({
            "product.template": [
                {
                    id: 91,
                    pos_categ_ids: [12, 13],
                },
            ],
        });

        records = models["product.template"].getAllBy("pos_categ_ids");
        expect(records[13]).toHaveLength(2);
    });

    test("Undefined models", async () => {
        await makeMockServer();
        const models = getRelatedModelsInstance(false);
        models.loadConnectedData({
            "pos.order": [
                {
                    id: 1,
                    message_ids: [1, 2, 3],
                    message_id: 99,
                },
            ],
        });
        const order = models["pos.order"].get(1);
        expect(order.message_ids).toEqual([1, 2, 3]);
        expect(order.message_id).toBe();
        expect(order.raw.message_ids).toEqual([1, 2, 3]);
        expect(order.raw.message_id).toBe(99);

        expect(() => {
            order.lines.push(3333);
        }).toThrow(/cannot be modified/i);

        order.message_ids = [1, 2];
        expect(order.message_ids).toEqual([1, 2]);
        expect(order.raw.message_ids).toEqual([1, 2]);

        order.message_id = 12;
        expect(order.message_id).toEqual(12);
        expect(order.raw.message_id).toEqual(99);

        const serialized = models.serializeForORM(order);

        // Not present in ORM serialization
        expect("message_ids" in serialized).toBe(false);
        expect("message_id" in serialized).toBe(false);
    });

    test("Base subclass must not override a field getter", async () => {
        await makeMockServer();
        class PosOrder extends Base {
            constructor(args) {
                super(args);
            }

            get lines() {
                return [];
            }
        }

        expect(() => {
            createRelatedModels(getModelDefinitions(), { "pos.order": PosOrder }, {});
        }).toThrow(/pos.order/i);
    });

    describe("setup must be called after connection / loading", () => {
        test("Simple create", async () => {
            await makeMockServer();
            const models = getRelatedModelsInstance(false);
            const line1 = models["pos.order.line"].create({
                id: 11,
                name: "Hello",
            });

            const order = models["pos.order"].create({ id: 99, lines: [11] });
            expect(order.lines).toInclude(line1);
        });

        test("Load connected data", async () => {
            await makeMockServer();
            const models = getRelatedModelsInstance(false);
            const results = models.loadConnectedData(
                {
                    "pos.order": [
                        {
                            id: 1,
                            total: 10,
                            lines: [11],
                            uuid: "42eb4cc3-2ec8-4a0b-9bca-0a2d8a98178c",
                        },
                    ],

                    "pos.order.line": [
                        {
                            id: 11,
                            order_id: 1,
                            name: "Line 1",
                            uuid: "5d3273af-c0f1-4008-9a1f-353841cf1a73",
                        },
                    ],
                },
                []
            );

            const order = models["pos.order"].get(1);
            expect(results["pos.order"][0]).toBe(order);
            expect(order.lines).toInclude(order.lines[0]);
        });

        test("Connect new data", async () => {
            await makeMockServer();
            const models = getRelatedModelsInstance(false);
            models["pos.order.line"].create({
                id: 12,
                name: "Hello",
            });

            models.connectNewData({
                "pos.order": [
                    {
                        id: 1,
                        total: 10,
                        lines: [11, 12],
                        uuid: "42eb4cc3-2ec8-4a0b-9bca-0a2d8a98178c",
                    },
                ],

                "pos.order.line": [
                    {
                        id: 11,
                        order_id: 1,
                        name: "Line 1",
                        uuid: "5d3273af-c0f1-4008-9a1f-353841cf1a73",
                    },
                ],
            });

            const order = models["pos.order"].get(1);
            expect(order.lines.length).toBe(2);
            expect(order.lines[0]).toBe(models["pos.order.line"].get(11));
            expect(order.lines[1]).toBe(models["pos.order.line"].get(12));
        });
    });

    test("Setup and State lifecycle execution order", async () => {
        await makeMockServer();
        let calls = [];

        class PosOrderDummy extends Base {
            setup(vals) {
                super.setup(vals);
                calls.push("setup");
            }
            initState() {
                super.initState();
                calls.push("initState");
            }

            restoreState(uiState) {
                super.restoreState(uiState);
                calls.push("restoreState");
            }
        }
        const defDummyOrder = {
            id: {
                name: "id",
                type: "integer",
            },
            total: {
                name: "total",
                type: "char",
            },
            uuid: {
                name: "uuid",
                type: "char",
            },
        };
        const { models } = createRelatedModels(
            { "pos.order.dummy": defDummyOrder },
            { "pos.order.dummy": PosOrderDummy },
            {
                dynamicModels: ["pos.order.dummy"],
                databaseIndex: {
                    "pos.order.dummy": ["uuid"],
                },
                databaseTable: {
                    "pos.order.dummy": { key: "uuid" },
                },
            }
        );

        // Create
        const order1 = models["pos.order.dummy"].create({});
        expect(calls).toEqual(["setup", "initState"]);

        // Update without state
        calls = [];
        models.loadConnectedData(
            {
                "pos.order.dummy": [
                    {
                        id: 1,
                        total: 10,
                        uuid: order1.uuid,
                    },
                ],
            },
            []
        );
        expect(calls).toEqual(["setup"]);

        // Update with state
        calls = [];
        models.loadConnectedData(
            {
                "pos.order.dummy": [
                    {
                        id: 1,
                        total: 10,
                        uuid: order1.uuid,
                        [SERIALIZED_UI_STATE_PROP]: '{"test":true}',
                    },
                ],
            },
            []
        );
        expect(calls).toEqual(["setup", "restoreState"]);
        expect(order1.uiState).toEqual({ test: true });

        //Loading new data
        calls = [];
        models.loadConnectedData(
            {
                "pos.order.dummy": [
                    {
                        id: 2,
                        total: 100,
                    },
                ],
            },
            []
        );
        expect(calls).toEqual(["setup", "initState"]);
    });
});

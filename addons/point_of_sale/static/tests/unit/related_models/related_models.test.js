import { expect, test, describe } from "@odoo/hoot";
import { createRelatedModels, Base } from "@point_of_sale/app/models/related_models";
import { serializeDateTime } from "@web/core/l10n/dates";
import { SERIALIZED_UI_STATE_PROP } from "@point_of_sale/app/models/related_models/utils";
import { MODEL_DEF as modelDefs, MODEL_OPTS as modelOpts } from "./utils";
const { DateTime } = luxon;

describe("Related Model", () => {
    test("Create simple model object", () => {
        const { models } = createRelatedModels(modelDefs, {}, modelOpts);

        const order = models["pos.order"].create({
            total: 12,
        });

        // Id and uuid are generated
        expect(order.id).not.toBeEmpty();
        expect(typeof order.id).toBe("string");
        expect(order.uuid).not.toBeEmpty();

        // The generated id and uuid must be the same
        expect(order.id).toBe(order.uuid);

        expect(order.total).toBe(12);
        order.total = 20;
        expect(order.total).toBe(20);

        // ID is generated even if no UUIDs are available.
        const attr = models["product.attribute"].create({});
        expect(attr.id).not.toBeEmpty();
    });

    test("Keep raw datas not defined in models fields", () => {
        const { models } = createRelatedModels(modelDefs, {}, modelOpts);
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
            total: 12,
            _additionalField: "Sample value",
            otherField: "Value 2",
        });

        expect(order2.raw.total).toBe(12);
        expect(order2.total).toBe(12);
        expect(order2.raw._additionalField).toBe(undefined);
        expect(order2._additionalField).toBe("Sample value");
        expect(order2.otherField).toBe(undefined);
        expect(order2.raw.otherField).toBe(undefined);
    });

    test("Ensure raw data is immutable", () => {
        const { models } = createRelatedModels(modelDefs, {}, modelOpts);
        models["pos.order.line"].create({
            id: 1,
            name: "Hello",
        });

        const order = models["pos.order"].create({
            total: 12,
            lines: [1],
        });

        expect(order.raw.lines.length).toBe(1);
        expect(order.raw.lines[0]).toBe(1);

        expect(() => {
            order.raw.total = 99;
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

    test("one2many creation (by ids)", () => {
        const { models } = createRelatedModels(modelDefs, {}, modelOpts);

        const createdLine = models["pos.order.line"].create({
            id: 11,
            name: "Hello",
        });

        const order = models["pos.order"].create({ id: 99, lines: [11] });
        const line = order.lines[0];
        expect(line.id).toBe(11);
        expect(line.name).toBe("Hello");
        expect(line.order_id).toBe(order);
        expect(line.order_id.id).toBe(99);
        expect(line.quantity).toBe(undefined);

        expect(line).toBe(createdLine);

        // Update child record
        line.name = "Hello world";
        expect(line.name).toBe("Hello world");

        createdLine.name = "Hello 2";
        expect(createdLine.name).toBe("Hello 2");
        expect(line.name).toBe("Hello 2");

        createdLine.name = "Hello 3";
        expect(order.lines[0].name).toBe("Hello 3");
    });

    test("one2many creation", () => {
        const { models } = createRelatedModels(modelDefs, {}, modelOpts);

        // Create an empty order
        const order = models["pos.order"].create({});

        // Add line top order
        models["pos.order.line"].create({ order_id: order, name: "Line 1" });
        expect(order.lines.length).toBe(1);
        expect(order.lines[0].name).toBe("Line 1");

        // Use order id to link the line
        models["pos.order.line"].create({ order_id: order.id, name: "Line 2" });
        expect(order.lines.length).toBe(2);
        expect(order.lines[1].name).toBe("Line 2");

        // Disconnect the  line
        const line = order.lines[0];
        line.order_id = null;
        expect(order.lines.length).toBe(1);
        expect(order.lines[0].name).toBe("Line 2");

        // Assign the line to another order
        const order2 = models["pos.order"].create({});
        expect(order2.lines.length).toBe(0);
        order.lines[0].order_id = order2;
        expect(order2.lines.length).toBe(1);
        expect(order.lines.length).toBe(0);
        expect(order2.lines[0].name).toBe("Line 2");

        line.order_id = order2.id; //Assign by id
        expect(order2.lines.length).toBe(2);
        expect(order2.lines[1].name).toBe("Line 1");
    });

    test("x2many array is not modifiable", () => {
        const { models } = createRelatedModels(modelDefs, {}, modelOpts);
        const order = models["pos.order"].create({});

        expect(() => {
            order.lines.push("a");
        }).toThrow(/cannot be modified/i);
    });

    test("one2many update", () => {
        const { models } = createRelatedModels(modelDefs, {}, modelOpts);
        const line1 = models["pos.order.line"].create({ name: "Line 1" });
        const line2 = models["pos.order.line"].create({ name: "Line 2" });
        const line3 = models["pos.order.line"].create({ name: "Line 3" });

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
        expect(order.lines[1].name).toBe("Line 1");
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
        expect(order.lines[0].name).toBe("Line 2");
        expect(order.lines[0].order_id).toBe(order);
        expect(order.lines[1].name).toBe("Line 3");
        expect(order.lines[1].order_id).toBe(order);
        expect(line1.order_id).toBeEmpty(); //line 1 disconnected

        // Create
        order.update({ lines: [["create", { name: "Line new" }]] });
        expect(order.lines.length).toBe(3);
        expect(order.lines[2].name).toBe("Line new");
        expect(order.lines[2].order_id).toBe(order);

        // Test set default value
        order.update({ lines: [line1] });
        expect(order.lines.length).toBe(1);
    });

    test("many2one delete", () => {
        const { models } = createRelatedModels(modelDefs, {}, modelOpts);
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

    test("many2many test", () => {
        const { models } = createRelatedModels(modelDefs, {}, modelOpts);
        const order = models["pos.order"].create({});
        const attr1 = models["product.attribute"].create({ name: "Attribute 1" });
        const attr2 = models["product.attribute"].create({ name: "Attribute 2" });
        const attr3 = models["product.attribute"].create({ name: "Attribute 3" });

        {
            // Assign attribute upon creation.
            const line = models["pos.order.line"].create({
                order_id: order,
                name: "Line",
                attribute_ids: [attr1, attr2],
            });
            expect(line.attribute_ids.length).toBe(2);
            expect(line.attribute_ids[0].name).toBe("Attribute 1");
            expect(line.attribute_ids[1].name).toBe("Attribute 2");
        }

        {
            // Assign attribute upon creation using ids
            const line = models["pos.order.line"].create({
                order_id: order,
                name: "Line",
                attribute_ids: [attr1.id, attr2.id],
            });
            expect(line.attribute_ids.length).toBe(2);
            expect(line.attribute_ids[0].name).toBe("Attribute 1");
            expect(line.attribute_ids[1].name).toBe("Attribute 2");
        }

        {
            // Assign attribute upon creation using link command
            const line = models["pos.order.line"].create({
                order_id: order,
                name: "Line",
                attribute_ids: [["link", attr1, attr2]], // by id
            });
            expect(line.attribute_ids.length).toBe(2);
            expect(line.attribute_ids[0].name).toBe("Attribute 1");
            expect(line.attribute_ids[1].name).toBe("Attribute 2");
        }

        {
            // Assign attribute upon creation using create command
            const line4 = models["pos.order.line"].create({
                order_id: order,
                name: "Line 3",
                attribute_ids: [["create", { name: "New" }]], // by id
            });
            expect(line4.attribute_ids.length).toBe(1);
            expect(line4.attribute_ids[0].name).toBe("New");
        }

        {
            // Manage attribute_ids using the update method
            const line = models["pos.order.line"].create({ order_id: order, name: "Line 1" });
            line.update({ attribute_ids: [["link", attr1]] });
            expect(line.attribute_ids.length).toBe(1);
            expect(line.attribute_ids[0].name).toBe("Attribute 1");

            line.update({ attribute_ids: [["set", attr2, attr3]] });
            expect(line.attribute_ids.length).toBe(2);
            expect(line.attribute_ids[0].name).toBe("Attribute 2");
            expect(line.attribute_ids[1].name).toBe("Attribute 3");

            line.update({ attribute_ids: [["unlink", attr2]] });
            expect(line.attribute_ids.length).toBe(1);
            expect(line.attribute_ids[0].name).toBe("Attribute 3");

            line.update({ attribute_ids: [["unlink", attr3]] });
            expect(line.attribute_ids.length).toBe(0);
        }
    });

    test("x2many allow setter", () => {
        const { models } = createRelatedModels(modelDefs, {}, modelOpts);

        const line1 = models["pos.order.line"].create({ id: 11, name: "Line 1" });
        const line2 = models["pos.order.line"].create({ id: 12, name: "Line 2" });

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
            order.lines = [line1, ["link", line2.id], ["create", { name: "Line 3" }]];
            expect(order.lines.length).toBe(3);
            expect(order.lines[0]).toBe(line1);
            expect(order.lines[1]).toBe(line2);
            expect(order.lines[2].name).toBe("Line 3");
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

    test("Load data without connect", () => {
        const { models } = createRelatedModels(modelDefs, {}, modelOpts);

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
                        name: "Line 1",
                        uuid: "5d3273af-c0f1-4008-9a1f-353841cf1a73",
                    },
                    {
                        id: 12,
                        order_id: 1,
                        name: "Line 2",
                        attribute_ids: [91, 92],
                        uuid: "0b6d3b25-3d5d-41a1-9357-059231a3cd82",
                    },
                ],
                "product.attribute": [
                    { id: 91, name: "Att 1" },
                    { id: 92, name: "Att 2" },
                ],
            },
            []
        );

        const order = models["pos.order"].get(1);
        expect(result["pos.order"][0]).toBe(order);
        expect(order.lines.length).toBe(2);
        expect(order.lines[0].name).toBe("Line 1");
        expect(order.lines[1].name).toBe("Line 2");
        const line2 = order.lines[1];
        expect(line2.order_id).toBe(order);
        expect(line2.attribute_ids.length).toBe(2);
        expect(line2.attribute_ids[0].name).toBe("Att 1");
        expect(line2.attribute_ids[1].name).toBe("Att 2");
        models.loadConnectedData({
            "pos.order": [
                { id: 1, total: 10, lines: [12], uuid: "42eb4cc3-2ec8-4a0b-9bca-0a2d8a98178c" },
            ],
            "pos.order.line": [
                {
                    id: 12,
                    order_id: 1,
                    name: "Line 2",
                    attribute_ids: [100],
                    uuid: "0b6d3b25-3d5d-41a1-9357-059231a3cd82",
                },
            ],
            "product.attribute": [{ id: 100, name: "Att 100" }],
        });

        //The same order object
        const order2 = models["pos.order"].get(1);
        expect(order2).toBe(order);
        expect(order2.lines.length).toBe(1);
        expect(order2.lines[0]).toBe(line2);
        expect(order2.lines[0].attribute_ids.length).toBe(1);
        expect(order2.lines[0].attribute_ids[0].id).toBe(100);
        expect(order2.lines[0].attribute_ids[0].name).toBe("Att 100");
    });

    test("Load data & connect records", () => {
        const { models } = createRelatedModels(modelDefs, {}, modelOpts);

        const result = models.connectNewData({
            "pos.order.line": [
                {
                    id: 11,
                    order_id: 1,
                    name: "Line 1",
                    uuid: "5d3273af-c0f1-4008-9a1f-353841cf1a73",
                },
                {
                    id: 12,
                    order_id: 1,
                    name: "Line 2",
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
        expect(order.lines[0].name).toBe("Line 1");
        expect(order.lines[1].name).toBe("Line 2");

        expect(result["pos.order"][0]).toBe(order);
    });

    test("Load data: connect new records", () => {
        const { models } = createRelatedModels(modelDefs, {}, modelOpts);

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
                    name: "Line 1",
                    uuid: "5d3273af-c0f1-4008-9a1f-353841cf1a73",
                },
                {
                    id: 12,
                    order_id: 1,
                    name: "Line 2",
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

    test("Load data: connect records without many2one", () => {
        const { models } = createRelatedModels(modelDefs, {}, modelOpts);
        // lines without order_id
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
                    name: "Line 1",
                    uuid: "5d3273af-c0f1-4008-9a1f-353841cf1a73",
                },
                {
                    id: 12,
                    name: "Line 2",
                    uuid: "0b6d3b25-3d5d-41a1-9357-059231a3cd82",
                },
            ],
        });
        const order = models["pos.order"].get(1);
        expect(order.lines.length).toBe(2);
    });

    test("Load partial data with backref", () => {
        const { models } = createRelatedModels(modelDefs, {}, modelOpts);
        const order = models["pos.order"].create({ id: 1 });
        const attr1 = models["product.attribute"].create({ id: 91, name: "Attribute 1" });
        const attr2 = models["product.attribute"].create({ id: 92, name: "Attribute 2" });
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
                    id: 13,
                    order_id: 1,
                    name: "Line 2",
                    attribute_ids: [91, 92],
                    uuid: "50a6efd0-b802-4e2d-a40e-b5b79f118721",
                },
            ],

            "pos.table": [
                {
                    id: 99,
                    name: "Table 1",
                },
            ],

            "pos.order": [
                {
                    id: 2,
                    lines: [12, 13],
                    table_id: 99,
                },
            ],
        });

        const line = models["pos.order.line"].get(12);
        const line2 = models["pos.order.line"].get(13);

        expect(line.order_id).toBe(order);
        expect(line2.order_id).toBe(order);

        expect(attr1.backLink("<-pos.order.line.attribute_ids")[0]).toBe(line);
        expect(attr1.backLink("<-pos.order.line.attribute_ids")[1]).toBe(line2);
        expect(attr2.backLink("<-pos.order.line.attribute_ids")[0]).toBe(line);
        expect(attr2.backLink("<-pos.order.line.attribute_ids")[1]).toBe(line2);

        // Create another lines
        const line3 = models["pos.order.line"].create({ attribute_ids: [92] });
        expect(attr2.backLink("<-pos.order.line.attribute_ids")[2]).toBe(line3);

        //Check table backref one2many
        {
            const order2 = models["pos.order"].get(2);
            const table = order2.table_id;
            expect(table.name).toBe("Table 1");
            expect(table.backLink("<-pos.order.table_id")[0]).toBe(order2);
        }
    });

    test("Adding record to the store should not compute getter", () => {
        const modelOpts2 = {
            ...modelOpts,
            databaseIndex: {
                "pos.order": ["uuid"],
                "pos.order.line": ["uuid", "order_id"],
            },
        };

        const { models } = createRelatedModels(modelDefs, {}, modelOpts2);

        models.loadConnectedData({
            "pos.order.line": [
                {
                    id: 12,
                    order_id: 1,
                    name: "Line 1",
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

    test("Update newly created records with server data", () => {
        const { models } = createRelatedModels(modelDefs, {}, modelOpts);
        const order = models["pos.order"].create({ total: 30 });
        const line = models["pos.order.line"].create({ order_id: order, name: "Line 1" });
        const oldOrderId = order.id;

        order.sampleData = "test";

        expect(order.lines.length).toBe(1);
        const oldLineId = order.lines[0].id;
        expect(typeof oldOrderId).toBe("string");
        expect(models["pos.order"].get(oldOrderId)).not.toBeEmpty();

        models.connectNewData({
            "pos.order": [{ id: 100, total: 50, lines: [12], uuid: order.uuid }],
            "pos.order.line": [
                {
                    id: 12,
                    order_id: 1,
                    name: "Line 1111",
                    uuid: line.uuid,
                },
            ],
        });

        expect(order.id).toBe(100);
        expect(order.total).toBe(50);
        expect(order.sampleData).toBe("test");
        expect(order.lines.length).toBe(1);
        expect(order.lines[0]).toBe(line);
        expect(order.lines[0].id).toBe(12);
        expect(order.lines[0].name).toBe("Line 1111");

        //Find by ids, uuids
        expect(models["pos.order"].get(oldOrderId)).toBe(undefined);
        expect(models["pos.order"].get(order.id)).toBe(order);
        expect(models["pos.order"].getBy("uuid", order.uuid)).toBe(order);

        expect(models["pos.order.line"].get(oldLineId)).toBe(undefined);
        expect(models["pos.order.line"].get(line.id)).toBe(line);
        expect(models["pos.order.line"].getBy("uuid", line.uuid)).toBe(line);
    });

    test("Disallow record id update", () => {
        const { models } = createRelatedModels(modelDefs, {}, modelOpts);
        const order = models["pos.order"].create({ total: 30 });
        expect(typeof order.id).toBe("string");
        expect(models["pos.order"].get(order.id)).toBe(order);
        expect(models["pos.order"].getBy("uuid", order.uuid)).toBe(order);

        const oldId = order.id;
        order.update({ id: 12 });
        expect(order.id).toBe(oldId);

        expect(() => {
            order.id = 12;
        }).toThrow();
    });

    test("Ignoring update for unknown field", () => {
        const { models } = createRelatedModels(modelDefs, {}, modelOpts);
        const order = models["pos.order"].create({ total: 30 });

        expect(() => {
            order.update({ fake_field: 1 });
        }).toThrow();

        order.update({ fake_field: 1 }, { omitUnknownField: true });
        expect(order.fake_field).toBe(undefined);
        expect(order.raw.fake_field).toBe(undefined);
    });

    test("Deleting the root record must disconnect its child records", () => {
        const { models } = createRelatedModels(modelDefs, {}, modelOpts);
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

    test("DateTime in raw data must be stored in server format", () => {
        const { models } = createRelatedModels(modelDefs, {}, modelOpts);
        const orderDate = DateTime.now().set({ second: 0, millisecond: 0 });

        {
            const order = models["pos.order"].create({ total: 30, date: orderDate });
            // Stored as server date
            expect(order.raw.date).toBe(serializeDateTime(orderDate));
            expect(order.date.toMillis()).toBe(orderDate.toMillis());

            // Update date
            const newDate = orderDate.plus({ hours: 1 });
            order.update({ date: newDate });
            expect(order.date.toMillis()).toBe(newDate.toMillis());
        }

        {
            //Create with server date
            const newOrderDate = orderDate.plus({ hours: 2 });
            const serverValue = serializeDateTime(newOrderDate);
            const order = models["pos.order"].create({
                total: 30,
                date: serverValue,
            });
            expect(order.raw.date).toBe(serverValue);
            expect(order.date.toMillis()).toBe(newOrderDate.toMillis());
        }
    });

    test("Store updates must invalidate getters", () => {
        const modelOpts2 = {
            ...modelOpts,
            databaseIndex: {
                "pos.order": ["uuid"],
                "pos.order.line": ["uuid", "order_id"],
            },
        };

        const { models } = createRelatedModels(modelDefs, {}, modelOpts2);

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

    test("Backref lazy loading", () => {
        const { models } = createRelatedModels(modelDefs, {}, modelOpts);

        models.loadConnectedData({
            "product.attribute": [
                { id: 91, name: "Att 1" },
                { id: 92, name: "Att 2" },
            ],

            "pos.order.line": [
                {
                    id: 12,
                    name: "Line 1",
                    attribute_ids: [91, 92],
                    uuid: "0b6d3b25-3d5d-41a1-9357-059231a3cd82",
                },
                {
                    id: 13,
                    name: "Line 2",
                    attribute_ids: [92],
                    uuid: "qsdqsdq",
                },
            ],
        });

        const att1 = models["product.attribute"].get(91);
        const att2 = models["product.attribute"].get(92);

        const line1 = models["pos.order.line"].get(12);
        const line2 = models["pos.order.line"].get(13);

        {
            let lines = att1.backLink("<-pos.order.line.attribute_ids");
            expect(lines.length).toBe(1);
            expect(lines[0]).toBe(line1);

            // Nothing changes, the same lazy result is returned
            let sameLines = att1.backLink("<-pos.order.line.attribute_ids");
            expect(sameLines).toBe(lines);

            // Somthing not related is added to the store, the same lazy result
            models["product.attribute"].create({});
            sameLines = att1.backLink("<-pos.order.line.attribute_ids");
            expect(sameLines).toBe(lines);

            // Remove attributes
            line1.attribute_ids = [];
            lines = att1.backLink("<-pos.order.line.attribute_ids");
            expect(lines.length).toBe(0);

            // Add
            line1.attribute_ids = [att1, att2];
            lines = att1.backLink("<-pos.order.line.attribute_ids");
            expect(lines.length).toBe(1);
            expect(lines[0]).toBe(line1);

            // New Line
            const line3 = models["pos.order.line"].create({ attribute_ids: [91] });
            lines = att1.backLink("<-pos.order.line.attribute_ids");
            expect(lines.length).toBe(2);
            expect(lines[1]).toBe(line3);

            // Load from backend
            models.connectNewData({
                "pos.order.line": [
                    {
                        id: 14,
                        attribute_ids: [91],
                    },
                ],
            });

            lines = att1.backLink("<-pos.order.line.attribute_ids");
            expect(lines.length).toBe(3);
            expect(lines[1]).toBe(line3);
            expect(lines[2]).toBe(models["pos.order.line"].get(14));
        }

        {
            let lines = att2.backLink("pos.order.line.attribute_ids");
            expect(lines.length).toBe(2);
            expect(lines[0]).toBe(line1);
            expect(lines[1]).toBe(line2);

            line1.delete();
            lines = att2.backLink("pos.order.line.attribute_ids");
            expect(lines.length).toBe(1);
            expect(lines[0]).toBe(line2);
        }
    });

    test("Store: multi values index", () => {
        const modelOpts2 = {
            ...modelOpts,
            databaseIndex: {
                "pos.order.line": ["uuid", "attribute_ids"],
            },
        };

        const { models } = createRelatedModels(modelDefs, {}, modelOpts2);

        models.loadConnectedData({
            "product.attribute": [
                { id: 91, name: "Att 1" },
                { id: 92, name: "Att 2" },
            ],
            "pos.order.line": [
                {
                    id: 12,
                    name: "Line 1",
                    attribute_ids: [91, 92],
                    uuid: "0b6d3b25-3d5d-41a1-9357-059231a3cd82",
                },
                {
                    id: 13,
                    name: "Line 2",
                    attribute_ids: [92],
                    uuid: "qsdqsdq",
                },
            ],
        });

        let records = models["pos.order.line"].readAllBy("attribute_ids");
        expect(Object.keys(records).length).toBe(2);
        expect(records[91].length).toBe(1);
        expect(records[91][0].name).toBe("Line 1");
        expect(records[92].length).toBe(2);
        expect(records[92][1].name).toBe("Line 2");
        expect(records[92][1].name).toBe("Line 2");

        // Delete line 1
        const line1 = models["pos.order.line"].get(12);
        line1.delete();

        records = models["pos.order.line"].getBy("attribute_ids", 92);
        expect(records.length).toBe(1);
        expect(records[0].name).toBe("Line 2");

        // Delete line 2
        const line2 = models["pos.order.line"].get(13);
        line2.delete();
        records = models["pos.order.line"].getBy("attribute_ids", 92);
        expect(records.length).toBe(0);
        expect(models["pos.order.line"].readBy("attribute_ids", 92).length).toBe(0);
    });

    test("Store: multi value index update", () => {
        const modelOpts2 = {
            ...modelOpts,
            databaseIndex: {
                "pos.order.line": ["uuid", "attribute_ids"],
            },
        };

        const { models } = createRelatedModels(modelDefs, {}, modelOpts2);

        models.loadConnectedData({
            "product.attribute": [
                { id: 91, name: "Att 1" },
                { id: 92, name: "Att 2" },
            ],
            "pos.order.line": [
                {
                    id: 12,
                    name: "Line 1",
                    attribute_ids: [],
                    uuid: "0b6d3b25-3d5d-41a1-9357-059231a3cd82",
                },
            ],
        });

        let records = models["pos.order.line"].getAllBy("attribute_ids");
        expect(Object.keys(records).length).toBe(0);

        // Update line
        const line1 = models["pos.order.line"].get(12);
        line1.attribute_ids = [91];
        records = models["pos.order.line"].getAllBy("attribute_ids");
        expect(Object.keys(records).length).toBe(1);

        //Create a new line
        const line2 = models["pos.order.line"].create({ attribute_ids: [91], uuid: "xxxline2" });
        records = models["pos.order.line"].getAllBy("attribute_ids");
        expect(records[91].length).toBe(2);
        expect(records[91][0].id).toBe(12);
        expect(records[91][1].id).toBe(line2.id);

        // Line id updated
        models.connectNewData({
            "pos.order.line": [
                {
                    id: 13,
                    name: "Line 1",
                    attribute_ids: [91, 92],
                    uuid: line2.uuid,
                },
            ],
        });
        expect(line2.id).toBe(13);
        records = models["pos.order.line"].getAllBy("attribute_ids");
        expect(records[91].length).toBe(2);
        expect(records[91][0].id).toBe(12);
        expect(records[91][1].id).toBe(13);
        expect(records[92][0].id).toBe(13);

        // backend updated
        models.connectNewData({
            "pos.order.line": [
                {
                    id: 13,
                    name: "Line 1",
                    attribute_ids: [],
                    uuid: line2.uuid,
                },
            ],
        });

        records = models["pos.order.line"].getAllBy("attribute_ids");
        expect(records[91].length).toBe(1);
        expect(records[91][0].id).toBe(12);
        expect(records[92].length).toBe(0);
    });

    test("Undefined models", () => {
        /// Undefined model relations should return an array of IDs instead of fetching record objects
        const modelDefs = {
            "pos.order": {
                id: { type: "integer", compute: false, related: false },
                message_ids: {
                    name: "message_ids",
                    model: "pos.order",
                    relation: "mail.message",
                    type: "one2many",
                    inverse_name: "res_id",
                },
                message_id: {
                    model: "pos.order",
                    relation: "mail.message",
                    type: "many2one",
                },
            },
        };

        const { models } = createRelatedModels(modelDefs, {}, modelOpts);

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
        expect(order.message_id).toBe(99);
        expect(order.raw.message_ids).toEqual([1, 2, 3]);
        expect(order.raw.message_id).toBe(99);

        expect(() => {
            order.message_ids.push(3333);
        }).toThrow(/cannot be modified/i);

        order.message_ids = [1, 2];
        expect(order.message_ids).toEqual([1, 2]);
        expect(order.raw.message_ids).toEqual([1, 2]);

        order.message_id = 12;
        expect(order.message_id).toEqual(12);
        expect(order.raw.message_id).toEqual(12);

        const serialized = models.serializeForORM(order);

        // Not present in ORM serialization
        expect("message_ids" in serialized).toBe(false);
        expect("message_id" in serialized).toBe(false);
    });

    test("Base subclass must not override a field getter", () => {
        class PosOrder extends Base {
            constructor(args) {
                super(args);
            }

            get lines() {
                return [];
            }
        }

        expect(() => {
            createRelatedModels(modelDefs, { "pos.order": PosOrder }, modelOpts);
        }).toThrow(/pos.order/i);
    });

    describe("setup must be called after connection / loading", () => {
        test("Simple create", () => {
            class PosOrder extends Base {
                setup(vals) {
                    this.__lineInSetup = this.lines[0];
                }
            }

            const { models } = createRelatedModels(modelDefs, { "pos.order": PosOrder }, modelOpts);

            const line1 = models["pos.order.line"].create({
                id: 11,
                name: "Hello",
            });

            const order = models["pos.order"].create({ id: 99, lines: [11] });
            expect(order.__lineInSetup).toBe(line1);
        });

        test("Load connected data", () => {
            class PosOrder extends Base {
                setup(vals) {
                    this.__lineInSetup = this.lines[0];
                }
            }

            const { models } = createRelatedModels(modelDefs, { "pos.order": PosOrder }, modelOpts);

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
            expect(order.__lineInSetup).toBe(order.lines[0]);
        });

        test("Connect new data", () => {
            class PosOrder extends Base {
                setup(vals) {
                    this.__linesInSetup = [...this.lines];
                }
            }

            const { models } = createRelatedModels(modelDefs, { "pos.order": PosOrder }, modelOpts);

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
            expect(order.__linesInSetup.length).toBe(2);
            expect(order.__linesInSetup[0]).toBe(models["pos.order.line"].get(11));
            expect(order.__linesInSetup[1]).toBe(models["pos.order.line"].get(12));
        });
    });

    test("Setup and State lifecycle execution order", () => {
        let calls = [];

        class PosOrder extends Base {
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
        const { models } = createRelatedModels(modelDefs, { "pos.order": PosOrder }, modelOpts);

        // Create
        const order1 = models["pos.order"].create({});
        expect(calls).toEqual(["setup", "initState"]);

        // Update without state
        calls = [];
        models.loadConnectedData(
            {
                "pos.order": [
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
                "pos.order": [
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
                "pos.order": [
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

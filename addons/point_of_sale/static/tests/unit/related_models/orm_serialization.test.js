import { expect, test, describe } from "@odoo/hoot";
import { createRelatedModels } from "@point_of_sale/app/models/related_models";

const getModels = () =>
    createRelatedModels(
        {
            "pos.order": {
                groups: {
                    name: "groups",
                    model: "pos.order",
                    relation: "pos.order.line.group",
                    type: "one2many",
                    inverse_name: "order_id",
                },

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

                combo_parent_id: {
                    name: "combo_parent_id",
                    model: "pos.order.line",
                    relation: "pos.order.line",
                    type: "many2one",
                },
                combo_line_ids: {
                    name: "combo_line_ids",
                    model: "pos.order.line",
                    relation: "pos.order.line",
                    type: "one2many",
                    inverse_name: "combo_parent_id",
                },
                group_id: {
                    name: "group_id",
                    model: "pos.order.line",
                    relation: "pos.order.line.group",
                    type: "many2one",
                    ondelete: "set null",
                },
                quantity: {
                    name: "quantity",
                    type: "float",
                },
                pack_lot_ids: {
                    name: "pack_lot_ids",
                    model: "pos.order.line",
                    relation: "pos.lot",
                    type: "one2many",
                    inverse_name: "line_id",
                },
                uuid: { type: "char" },
            },

            "pos.order.line.group": {
                order_id: {
                    name: "order_id",
                    model: "pos.order.line.group",
                    relation: "pos.order",
                    type: "many2one",
                },

                lines: {
                    name: "lines",
                    model: "pos.order.line.group",
                    relation: "pos.order.line",
                    type: "one2many",
                    inverse_name: "group_id",
                },

                index: {
                    name: "index",
                    type: "integer",
                },

                uuid: { type: "char" },
            },
            "product.attribute": {},
            "pos.lot": {
                line_id: {
                    name: "line_id",
                    model: "pos.lot",
                    relation: "pos.order.line",
                    type: "many2one",
                },
                lot_name: {
                    name: "lot_name",
                    type: "char",
                },
            },
        },
        {},
        {
            dynamicModels: ["pos.order", "pos.order.line", "pos.order.line.group", "pos.lot"],
            databaseIndex: {
                "pos.order": ["uuid"],
                "pos.order.line": ["uuid"],
                "pos.order.line.group": ["uuid"],
            },
            databaseTable: {
                "pos.order": { key: "uuid" },
                "pos.order.line": { key: "uuid" },
                "pos.order.line.group": { key: "uuid" },
            },
        }
    ).models;

describe("ORM serialization", () => {
    test("basic", () => {
        const models = getModels();
        const order = models["pos.order"].create({});
        const line1 = models["pos.order.line"].create({ order_id: order, quantity: 1 });
        const line2 = models["pos.order.line"].create({ order_id: order, quantity: 2 });
        order.total = 10;

        const result = models.serializeForORM(order);
        {
            expect(result.uuid).not.toBeEmpty();
            expect(result.total).toBe(10);
            expect(result.lines.length).toBe(2);

            expect(result.lines[0][0]).toBe(0);
            expect(result.lines[0][1]).toBe(0);
            expect(result.lines[0][2].id).toBe(undefined);
            expect(result.lines[0][2].uuid).toBe(line1.uuid);
            expect(result.lines[0][2].quantity).toBe(1);

            expect(result.lines[1][0]).toBe(0);
            expect(result.lines[1][1]).toBe(0);
            expect(result.lines[1][2].id).toBe(undefined);
            expect(result.lines[1][2].uuid).toBe(line2.uuid);
            expect(result.lines[1][2].quantity).toBe(2);

            expect(result.relations_uuid_mapping).toBe(undefined);
        }

        // Server results with ids
        models.connectNewData({
            "pos.order": [{ ...order.raw, id: 1, lines: [11, 12] }],
            "pos.order.line": [
                { ...line1.raw, id: 11, order_id: 1 },
                { ...line2.raw, id: 12, order_id: 1 },
            ],
        });

        line1.quantity = 99;
        {
            const result = models.serializeForORM(order);
            expect(result.lines.length).toBe(1);
            expect(result.lines[0][0]).toBe(1);
            expect(result.lines[0][1]).toBe(11);
            expect(result.lines[0][2].quantity).toBe(99);
        }

        // Delete line
        line1.delete();
        {
            const result = models.serializeForORM(order);
            expect(result.lines.length).toBe(1);
            expect(result.lines[0][0]).toBe(3);
            expect(result.lines[0][1]).toBe(11);
        }
    });

    test("serialization of non-dynamic model relationships", () => {
        const models = getModels();
        const order = models["pos.order"].create({});

        const att1 = models["product.attribute"].create({ id: 99 });
        const att2 = models["product.attribute"].create({ id: 999 });
        const line = models["pos.order.line"].create({ order_id: order, quantity: 1 });
        line.attribute_ids = [["link", att1, att2]];
        {
            const result = models.serializeForORM(order);
            expect(result.lines[0][2].attribute_ids).toEqual([99, 999]);
        }

        const att3 = models["product.attribute"].create({ id: 9999 });
        line.attribute_ids = [["link", att3]];
        {
            const result = models.serializeForORM(order);
            expect(result.lines[0][2].attribute_ids).toEqual([99, 999, 9999]);
        }

        line.attribute_ids = [["unlink", att3, att2]];
        {
            const result = models.serializeForORM(order);
            expect(result.lines[0][2].attribute_ids).toEqual([99]);
        }

        line.attribute_ids = [];
        {
            const result = models.serializeForORM(order);
            expect(result.lines[0][2].attribute_ids).toEqual([]);
        }
    });

    test("serialization of dynamic model without uuid", () => {
        const models = getModels();
        let order = models["pos.order"].create({});
        const orderUUID = order.uuid;

        let line1 = models["pos.order.line"].create({
            order_id: order,
        });
        const line1UUID = line1.uuid;

        models["pos.lot"].create({ line_id: line1, lot_name: "lot1" });
        {
            const result = models.serializeForORM(order);
            expect(result.lines.length).toBe(1);
            const pack_lot_ids = result.lines[0][2].pack_lot_ids;
            expect(pack_lot_ids.length).toBe(1);
            expect(pack_lot_ids[0][0]).toBe(0);
            expect(pack_lot_ids[0][0]).toBe(0);
            expect(pack_lot_ids[0][2]).toEqual({ lot_name: "lot1" });
        }

        models.connectNewData({
            "pos.order": [
                {
                    id: 1,
                    lines: [11],
                    uuid: order.uuid,
                },
            ],
            "pos.order.line": [
                {
                    id: 11,
                    pack_lot_ids: [99],
                    uuid: line1UUID,
                },
            ],
            "pos.lot": [
                {
                    id: 99,
                    lot_name: "lot1",
                },
            ],
        });

        order = models["pos.order"].getBy("uuid", orderUUID);
        line1 = models["pos.order.line"].getBy("uuid", line1UUID);

        models["pos.lot"].create({ line_id: line1, lot_name: "lot2" });
        {
            const result = models.serializeForORM(order);
            expect(result.lines.length).toBe(1);
            const pack_lot_ids = result.lines[0][2].pack_lot_ids;
            expect(pack_lot_ids.length).toBe(1);
            expect(pack_lot_ids[0][0]).toBe(0);
            expect(pack_lot_ids[0][1]).toBe(0);
            expect(pack_lot_ids[0][2].lot_name).toEqual("lot2");
        }

        models.connectNewData({
            "pos.order": [
                {
                    id: 1,
                    lines: [11],
                    uuid: order.uuid,
                },
            ],
            "pos.order.line": [
                {
                    id: 11,
                    order_id: 1,
                    pack_lot_ids: [99, 999],
                    uuid: line1UUID,
                },
            ],
            "pos.lot": [
                {
                    id: 99,
                    line_id: 11,
                    lot_name: "lot1",
                },
                {
                    id: 999,
                    line_id: 11,
                    lot_name: "lot2",
                },
            ],
        });
        order = models["pos.order"].getBy("uuid", orderUUID);
        order.lines[0].pack_lot_ids[1].delete();
        order.lines[0].pack_lot_ids[0].delete();
        {
            const result = models.serializeForORM(order);
            expect(result.lines.length).toBe(1);
            const pack_lot_ids = result.lines[0][2].pack_lot_ids;
            expect(pack_lot_ids.length).toBe(2);
            expect(pack_lot_ids).toEqual([
                [3, 999],
                [3, 99],
            ]);
        }
    });

    test("nested lines relationship", () => {
        const models = getModels();
        let order = models["pos.order"].create({});
        let parentLine = models["pos.order.line"].create({ order_id: order });
        let line1 = models["pos.order.line"].create({
            order_id: order,
            combo_parent_id: parentLine,
        });
        let line2 = models["pos.order.line"].create({
            order_id: order,
            combo_parent_id: parentLine,
        });

        {
            const result = models.serializeForORM(order);
            expect(result.lines.length).toBe(3);
            expect(result.lines[0][2].combo_line_ids).toBeEmpty();
            expect(result.lines[0][2].combo_parent_id).toBeEmpty();
            expect(result.lines[1][2].combo_line_ids).toBeEmpty();
            expect(result.lines[1][2].combo_parent_id).toBeEmpty();
            expect(result.lines[2][2].combo_line_ids).toBeEmpty();
            expect(result.lines[2][2].combo_parent_id).toBeEmpty();

            const { relations_uuid_mapping } = result;
            expect(Object.keys(relations_uuid_mapping["pos.order.line"]).length).toBe(2);
            expect(relations_uuid_mapping["pos.order.line"][line1.uuid]["combo_parent_id"]).toBe(
                parentLine.uuid
            );
            expect(relations_uuid_mapping["pos.order.line"][line2.uuid]["combo_parent_id"]).toBe(
                parentLine.uuid
            );
        }

        models.connectNewData({
            "pos.order": [
                {
                    id: 1,
                    lines: [11, 111],
                    uuid: order.uuid,
                },
            ],
            "pos.order.line": [
                {
                    id: 1,
                    uuid: parentLine.uuid,
                },
                {
                    id: 11,
                    uuid: line1.uuid,
                    combo_parent_id: 1,
                },
                {
                    id: 111,
                    uuid: line2.uuid,
                    combo_parent_id: 1,
                },
            ],
        });

        // Update line: the uuid mapping must be present
        order = models["pos.order"].getBy("uuid", order.uuid);
        line1 = models["pos.order.line"].getBy("uuid", line1.uuid);
        line2 = models["pos.order.line"].getBy("uuid", line2.uuid);
        parentLine = models["pos.order.line"].getBy("uuid", parentLine.uuid);

        line1.quantity = 99;
        {
            const result = models.serializeForORM(order);
            expect(result.lines.length).toBe(1);
            expect(result.lines[0][0]).toBe(1);
            expect(result.lines[0][1]).toBe(11);
            expect(result.lines[0][2].quantity).toBe(99);
            expect(result.relations_uuid_mapping).toBe(undefined);
        }
    });

    test("recursive relationship with group of lines", () => {
        const models = getModels();

        let order = models["pos.order"].create({});
        let group1 = models["pos.order.line.group"].create({
            order_id: order,
            index: 1,
        });
        let group2 = models["pos.order.line.group"].create({
            order_id: order,
            index: 2,
        });
        let line1 = models["pos.order.line"].create({
            order_id: order,
            group_id: group1,
        });
        let line2 = models["pos.order.line"].create({
            order_id: order,
            group_id: group1,
        });

        expect(order.lines.length).toBe(2);
        expect(order.groups.length).toBe(2);
        expect(order.groups[0].lines.length).toBe(2);

        {
            const result = models.serializeForORM(order);
            expect(result.lines.length).toBe(2);
            expect(result.lines[0][2].group_id).toBeEmpty();
            expect(result.lines[1][2].group_id).toBeEmpty();

            expect(result.groups.length).toBe(2);

            expect(result.groups[0][0]).toBe(0);
            expect(result.groups[0][1]).toBe(0);
            expect(result.groups[0][2].index).toBe(1);
            expect(result.groups[0][2].lines).toBeEmpty();

            expect(result.groups[1][0]).toBe(0);
            expect(result.groups[1][1]).toBe(0);
            expect(result.groups[1][2].index).toBe(2);
            expect(result.groups[0][2].lines).toBeEmpty();

            const { relations_uuid_mapping } = result;
            expect(Object.keys(relations_uuid_mapping["pos.order.line"]).length).toBe(2);
            expect(relations_uuid_mapping["pos.order.line"][line1.uuid]["group_id"]).toBe(
                group1.uuid
            );
            expect(relations_uuid_mapping["pos.order.line"][line2.uuid]["group_id"]).toBe(
                group1.uuid
            );
        }

        models.connectNewData({
            "pos.order": [
                {
                    id: 1,
                    lines: [110, 111],
                    groups: [210, 211],
                    uuid: order.uuid,
                },
            ],
            "pos.order.line": [
                {
                    id: 110,
                    order_id: 1,
                    group_id: 210,
                    uuid: line1.uuid,
                    combo_parent_id: 1,
                },
                {
                    id: 111,
                    order_id: 1,
                    group_id: 210,
                    uuid: line2.uuid,
                    combo_parent_id: 1,
                },
            ],
            "pos.order.line.group": [
                {
                    id: 210,
                    lines: [110, 111],
                    index: 1,
                    uuid: group1.uuid,
                },
                {
                    id: 211,
                    lines: [],
                    index: 2,
                    uuid: group2.uuid,
                },
            ],
        });

        order = models["pos.order"].getBy("uuid", order.uuid);
        line1 = models["pos.order.line"].getBy("uuid", line1.uuid);
        line2 = models["pos.order.line"].getBy("uuid", line2.uuid);
        group1 = models["pos.order.line.group"].getBy("uuid", group1.uuid);
        group2 = models["pos.order.line.group"].getBy("uuid", group2.uuid);

        // Move line2 to another group
        line2.update({ group_id: group2 });
        expect(order.groups[0].lines.length).toBe(1);
        expect(order.groups[1].lines.length).toBe(1);

        {
            const result = models.serializeForORM(order);
            expect(result.groups[0].lines).toBeEmpty();
            expect(result.groups[1].lines).toBeEmpty();
            expect(result.lines.length).toBe(1);
            expect(result.lines[0][0]).toBe(1);
            expect(result.lines[0][1]).toBe(111);
            expect(result.lines[0][2].group_id).toBe(group2.id);
            expect(result.relations_uuid_mapping).toBe(undefined);
        }

        // Delete line
        line1.delete();
        //update the group, to be sure the lines are empty
        group1.index = 3;
        group2.index = 4;
        {
            const result = models.serializeForORM(order);
            expect(result.groups.length).toBe(2);
            expect(result.groups[0][0]).toBe(1);
            expect(result.groups[0][1]).toBe(group1.id);
            expect(result.groups[0][2].index).toBe(3);
            expect(result.groups[0][2].lines).toBeEmpty();
            expect(result.groups[1][0]).toBe(1);
            expect(result.groups[1][1]).toBe(group2.id);
            expect(result.groups[1][2].index).toBe(4);
            expect(result.groups[1][2].lines).toBeEmpty();

            expect(result.lines.length).toBe(1);
            expect(result.lines[0][0]).toBe(3);
            expect(result.lines[0][1]).toBe(110);
            expect(result.relations_uuid_mapping).toBe(undefined);
        }

        {
            //All update/delete have been cleared
            const result = models.serializeForORM(order);
            expect(result.groups).toBeEmpty();
            expect(result.lines).toBeEmpty();
        }
    });

    test("grouped lines and nested lines", () => {
        const models = getModels();

        const order = models["pos.order"].create({});
        const group1 = models["pos.order.line.group"].create({
            order_id: order,
            index: 1,
        });
        const group2 = models["pos.order.line.group"].create({
            order_id: order,
            index: 2,
        });
        const parentLine = models["pos.order.line"].create({ order_id: order });
        const line1 = models["pos.order.line"].create({
            order_id: order,
            group_id: group1,
            combo_parent_id: parentLine,
        });
        const line2 = models["pos.order.line"].create({
            order_id: order,
            group_id: group1,
            combo_parent_id: parentLine,
        });
        const line3 = models["pos.order.line"].create({
            order_id: order,
            group_id: group2,
        });

        {
            const result = models.serializeForORM(order);

            expect(result.lines.length).toBe(4);
            expect(result.groups.length).toBe(2);
            const { relations_uuid_mapping } = result;
            expect(Object.keys(relations_uuid_mapping["pos.order.line"]).length).toBe(3);

            const lineMapping = relations_uuid_mapping["pos.order.line"];
            expect(lineMapping[line1.uuid]["group_id"]).toBe(group1.uuid);
            expect(lineMapping[line2.uuid]["group_id"]).toBe(group1.uuid);
            expect(lineMapping[line1.uuid]["combo_parent_id"]).toBe(parentLine.uuid);
            expect(lineMapping[line2.uuid]["combo_parent_id"]).toBe(parentLine.uuid);
            expect(lineMapping[line3.uuid]["combo_parent_id"]?.length).toBeEmpty();
            expect(lineMapping[line3.uuid]["group_id"]).toBe(group2.uuid);
        }
    });
});

import { expect, test } from "@odoo/hoot";
import { createRelatedModels } from "@point_of_sale/app/models/related_models";
import { uuidv4 } from "@point_of_sale/utils";

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

                // circular_ref: {
                //     name: "circular_ref",
                //     model: "pos.order",
                //     relation: "pos.order",
                //     type: "many2one",
                // },

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
                    ondelete: "cascade",
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
        { dynamicModels: ["pos.order", "pos.order.line", "pos.order.line.group", "pos.lot"] }
    ).models;

test("simple serialization", () => {
    const models = getModels();
    const order = models["pos.order"].create({ uuid: uuidv4() });
    const line1 = models["pos.order.line"].create({ order_id: order, uuid: uuidv4(), quantity: 1 });
    const line2 = models["pos.order.line"].create({ order_id: order, uuid: uuidv4(), quantity: 2 });
    order.total = 10;

    const result = order.serialize({ orm: true });
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

    // Update line
    line1.update({ id: 11 }, { silent: true });
    line2.update({ id: 111 }, { silent: true });

    line1.quantity = 99;
    {
        const result = order.serialize({ orm: true, clear: true });
        expect(result.lines.length).toBe(1);
        expect(result.lines[0][0]).toBe(1);
        expect(result.lines[0][1]).toBe(11);
        expect(result.lines[0][2].quantity).toBe(99);
    }

    // Delete line
    line1.delete();
    {
        const result = order.serialize({ orm: true });
        expect(result.lines.length).toBe(1);
        expect(result.lines[0][0]).toBe(3);
        expect(result.lines[0][1]).toBe(11);
    }
});

test("serialization of non-dynamic model relationships", () => {
    const models = getModels();
    const order = models["pos.order"].create({ uuid: uuidv4() });

    const att1 = models["product.attribute"].create({ id: 99 });
    const att2 = models["product.attribute"].create({ id: 999 });
    const line = models["pos.order.line"].create({ order_id: order, uuid: uuidv4(), quantity: 1 });
    line.attribute_ids.push(att1);
    line.attribute_ids.push(att2);
    {
        const result = order.serialize({ orm: true, clear: true });
        expect(result.lines[0][2].attribute_ids).toEqual([99, 999]);
    }

    const att3 = models["product.attribute"].create({ id: 9999 });
    line.attribute_ids.push(att3);
    {
        const result = order.serialize({ orm: true, clear: true });
        expect(result.lines[0][2].attribute_ids).toEqual([99, 999, 9999]);
    }

    line.attribute_ids.pop();
    line.attribute_ids.pop();
    {
        const result = order.serialize({ orm: true, clear: true });
        expect(result.lines[0][2].attribute_ids).toEqual([99]);
    }

    line.attribute_ids.pop();
    {
        const result = order.serialize({ orm: true, clear: true });
        expect(result.lines[0][2].attribute_ids).toEqual([]);
    }
});

test("serialization of dynamic model without uuid", () => {
    const models = getModels();
    const order = models["pos.order"].create({ uuid: uuidv4() });

    const line1 = models["pos.order.line"].create({
        order_id: order,
        uuid: uuidv4(),
    });

    const lot1 = models["pos.lot"].create({ line_id: line1, lot_name: "lot1" });
    {
        const result = order.serialize({ orm: true, clear: true });
        expect(result.lines.length).toBe(1);
        const pack_lot_ids = result.lines[0][2].pack_lot_ids;
        expect(pack_lot_ids.length).toBe(1);
        expect(pack_lot_ids[0][0]).toBe(0);
        expect(pack_lot_ids[0][0]).toBe(0);
        expect(pack_lot_ids[0][2]).toEqual({ lot_name: "lot1" });
    }

    lot1.update({ id: 99 }, { silent: true });

    const lot2 = models["pos.lot"].create({ line_id: line1, lot_name: "lot2" });
    {
        const result = order.serialize({ orm: true, clear: true });
        expect(result.lines.length).toBe(1);
        const pack_lot_ids = result.lines[0][2].pack_lot_ids;
        expect(pack_lot_ids.length).toBe(1);
        expect(pack_lot_ids[0][0]).toBe(0);
        expect(pack_lot_ids[0][1]).toBe(0);
        expect(pack_lot_ids[0][2]).toEqual({ lot_name: "lot2" });
    }

    lot2.update({ id: 999 }, { silent: true });
    lot2.delete();
    lot1.delete();

    {
        const result = order.serialize({ orm: true, clear: true });
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
    const order = models["pos.order"].create({ uuid: uuidv4() });
    const parentLine = models["pos.order.line"].create({ order_id: order, uuid: uuidv4() });
    const line1 = models["pos.order.line"].create({
        order_id: order,
        combo_parent_id: parentLine,
        uuid: uuidv4(),
    });
    const line2 = models["pos.order.line"].create({
        order_id: order,
        combo_parent_id: parentLine,
        uuid: uuidv4(),
    });

    {
        const result = order.serialize({ orm: true });
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

    // Update line: the uuid mapping must be present
    parentLine.update({ id: 11 }, { silent: true });
    line1.update({ id: 12 }, { silent: true });
    line2.update({ id: 13 }, { silent: true });

    line1.quantity = 99;
    {
        const result = order.serialize({ orm: true, clear: true });
        expect(result.lines.length).toBe(1);
        expect(result.lines[0][0]).toBe(1);
        expect(result.lines[0][1]).toBe(12);
        expect(result.lines[0][2].quantity).toBe(99);
        expect(result.relations_uuid_mapping).toBe(undefined);
    }
});

test("recursive relationship with group of lines", () => {
    const models = getModels();

    const order = models["pos.order"].create({ uuid: uuidv4() });
    const group1 = models["pos.order.line.group"].create({
        order_id: order,
        uuid: uuidv4(),
        index: 1,
    });
    const group2 = models["pos.order.line.group"].create({
        order_id: order,
        uuid: uuidv4(),
        index: 2,
    });

    const line1 = models["pos.order.line"].create({
        order_id: order,
        group_id: group1,
        uuid: uuidv4(),
    });
    const line2 = models["pos.order.line"].create({
        order_id: order,
        group_id: group1,
        uuid: uuidv4(),
    });

    expect(order.lines.length).toBe(2);
    expect(order.groups.length).toBe(2);
    expect(order.groups[0].lines.length).toBe(2);

    {
        const result = order.serialize({ orm: true });
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
        expect(relations_uuid_mapping["pos.order.line"][line1.uuid]["group_id"]).toBe(group1.uuid);
        expect(relations_uuid_mapping["pos.order.line"][line2.uuid]["group_id"]).toBe(group1.uuid);
    }

    group1.update({ id: 210 }, { silent: true });
    group2.update({ id: 211 }, { silent: true });
    line1.update({ id: 110 }, { silent: true });
    line2.update({ id: 111 }, { silent: true });

    // Move line2 to another group
    line2.update({ group_id: group2 });
    expect(order.groups[1].lines.length).toBe(1);
    {
        const result = order.serialize({ orm: true, clear: true });
        expect(result.groups).toBeEmpty();
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
        const result = order.serialize({ orm: true, clear: true });
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
        const result = order.serialize({ orm: true, clear: true });
        expect(result.groups).toBeEmpty();
        expect(result.lines).toBeEmpty();
    }
});

test("grouped lines and nested lines", () => {
    const models = getModels();

    const order = models["pos.order"].create({ uuid: uuidv4() });
    const group1 = models["pos.order.line.group"].create({
        order_id: order,
        uuid: uuidv4(),
        index: 1,
    });
    const group2 = models["pos.order.line.group"].create({
        order_id: order,
        uuid: uuidv4(),
        index: 2,
    });
    const parentLine = models["pos.order.line"].create({ order_id: order, uuid: uuidv4() });
    const line1 = models["pos.order.line"].create({
        order_id: order,
        group_id: group1,
        combo_parent_id: parentLine,
        uuid: uuidv4(),
    });
    const line2 = models["pos.order.line"].create({
        order_id: order,
        group_id: group1,
        combo_parent_id: parentLine,
        uuid: uuidv4(),
    });
    const line3 = models["pos.order.line"].create({
        order_id: order,
        group_id: group2,
        uuid: uuidv4(),
    });

    {
        const result = order.serialize({ orm: true, clear: true });

        expect(result.lines.length).toBe(4);
        expect(result.groups.length).toBe(2);
        const { relations_uuid_mapping } = result;
        expect(Object.keys(relations_uuid_mapping["pos.order.line"]).length).toBe(3);
        expect(relations_uuid_mapping["pos.order.line"][line1.uuid]["group_id"]).toBe(group1.uuid);
        expect(relations_uuid_mapping["pos.order.line"][line2.uuid]["group_id"]).toBe(group1.uuid);
        expect(relations_uuid_mapping["pos.order.line"][line1.uuid]["combo_parent_id"]).toBe(
            parentLine.uuid
        );
        expect(relations_uuid_mapping["pos.order.line"][line2.uuid]["combo_parent_id"]).toBe(
            parentLine.uuid
        );

        expect(relations_uuid_mapping["pos.order.line"][line3.uuid]["combo_parent_id"]).toBeEmpty();
        expect(relations_uuid_mapping["pos.order.line"][line3.uuid]["group_id"]).toBe(group2.uuid);
    }
});

// test("Circular reference handling", () => {
//     const models = getModels();

//     const order = models["pos.order"].create({ uuid: uuidv4() });
//     const line1 = models["pos.order.line"].create({ order_id: order, uuid: uuidv4(), quantity: 1 });

//     // const line = models["pos.order.line"].create({ order_id: order, uuid: uuidv4() });
//     // Creating a circular reference
//     order.update({ circular_ref: order });

//     const result = order.serialize({ orm: true });

//     debugger;

//     // Ensuring circular references are handled properly
//     // expect(result.circular_ref).toBe("[Circular]");
//     // expect(result.lines[0].circular_ref).toBe("[Circular]");
//     expect(getObjectDepth(result)).toBe(1); // Checking depth constraint
// });

// function getObjectDepth(obj, depth = 0, seen = new WeakSet()) {
//     if (obj === null || typeof obj !== "object" || seen.has(obj)) {
//         return depth;
//     }
//     seen.add(obj);
//     const depths = Object.values(obj).map((value) => getObjectDepth(value, depth + 1, seen));
//     return Math.max(depth, ...depths);
// }

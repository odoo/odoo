import { expect, test } from "@odoo/hoot";
import { getRelatedModelsInstance } from "../data/get_model_definitions";
import { makeMockServer } from "@web/../tests/web_test_helpers";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

test("basic", async () => {
    await makeMockServer();
    const models = getRelatedModelsInstance(false);
    const order = models["pos.order"].create({});
    const line1 = models["pos.order.line"].create({ order_id: order, qty: 1 });
    const line2 = models["pos.order.line"].create({ order_id: order, qty: 2 });
    order.amount_total = 10;

    const keepCommandResult = models.serializeForORM(order, { keepCommands: true });
    const result = models.serializeForORM(order);
    {
        expect(keepCommandResult).toEqual(result);
        expect(result.uuid).not.toBeEmpty();
        expect(result.amount_total).toBe(10);
        expect(result.lines.length).toBe(2);

        expect(result.lines[0][0]).toBe(0);
        expect(result.lines[0][1]).toBe(0);
        expect(result.lines[0][2].id).toBe(undefined);
        expect(result.lines[0][2].uuid).toBe(line1.uuid);
        expect(result.lines[0][2].qty).toBe(1);

        expect(result.lines[1][0]).toBe(0);
        expect(result.lines[1][1]).toBe(0);
        expect(result.lines[1][2].id).toBe(undefined);
        expect(result.lines[1][2].uuid).toBe(line2.uuid);
        expect(result.lines[1][2].qty).toBe(2);

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

    line1.qty = 99;
    {
        const keepCommandResult = models.serializeForORM(order, { keepCommands: true });
        const result = models.serializeForORM(order);
        expect(keepCommandResult).toEqual(result);
        expect(result.lines.length).toBe(1);
        expect(result.lines[0][0]).toBe(1);
        expect(result.lines[0][1]).toBe(11);
        expect(result.lines[0][2].qty).toBe(99);
    }

    // Delete line
    line1.delete();
    {
        const keepCommandResult = models.serializeForORM(order, { keepCommands: true });
        const result = models.serializeForORM(order);
        expect(keepCommandResult).toEqual(result);
        expect(result.lines.length).toBe(1);
        expect(result.lines[0][0]).toBe(3);
        expect(result.lines[0][1]).toBe(11);
    }
});

test("serialization of non-dynamic model relationships", async () => {
    await makeMockServer();
    const models = getRelatedModelsInstance(false);
    const order = models["pos.order"].create({});

    const tax1 = models["account.tax"].create({ id: 99 });
    const tax2 = models["account.tax"].create({ id: 999 });
    const line = models["pos.order.line"].create({ order_id: order, qty: 1 });
    line.tax_ids = [["link", tax1, tax2]];
    {
        const keepCommandResult = models.serializeForORM(order, { keepCommands: true });
        const result = models.serializeForORM(order);
        expect(keepCommandResult).toEqual(result);
        expect(result.lines[0][2].tax_ids).toEqual([99, 999]);
    }

    const tax3 = models["account.tax"].create({ id: 9999 });
    line.tax_ids = [["link", tax3]];
    {
        const keepCommandResult = models.serializeForORM(order, { keepCommands: true });
        const result = models.serializeForORM(order);
        expect(keepCommandResult).toEqual(result);
        expect(result.lines[0][2].tax_ids).toEqual([99, 999, 9999]);
    }

    line.tax_ids = [["unlink", tax3, tax2]];
    {
        const keepCommandResult = models.serializeForORM(order, { keepCommands: true });
        const result = models.serializeForORM(order);
        expect(keepCommandResult).toEqual(result);
        expect(result.lines[0][2].tax_ids).toEqual([99]);
    }

    line.tax_ids = [];
    {
        const keepCommandResult = models.serializeForORM(order, { keepCommands: true });
        const result = models.serializeForORM(order);
        expect(keepCommandResult).toEqual(result);
        expect(result.lines[0][2].tax_ids).toEqual([]);
    }
});

test("serialization of dynamic model without uuid", async () => {
    await makeMockServer();
    const models = getRelatedModelsInstance(false);
    let order = models["pos.order"].create({});
    const orderUUID = order.uuid;

    let line1 = models["pos.order.line"].create({
        order_id: order,
    });
    const line1UUID = line1.uuid;

    models["pos.pack.operation.lot"].create({ pos_order_line_id: line1, lot_name: "lot1" });
    {
        const keepCommandResult = models.serializeForORM(order, { keepCommands: true });
        const result = models.serializeForORM(order);
        expect(keepCommandResult).toEqual(result);
        expect(result.lines.length).toBe(1);
        const pack_lot_ids = result.lines[0][2].pack_lot_ids;
        expect(pack_lot_ids.length).toBe(1);
        expect(pack_lot_ids[0][0]).toBe(0);
        expect(pack_lot_ids[0][0]).toBe(0);
        expect(pack_lot_ids[0][2]).toEqual({ lot_name: "lot1", write_date: false });
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
        "pos.pack.operation.lot": [
            {
                id: 99,
                lot_name: "lot1",
            },
        ],
    });

    order = models["pos.order"].getBy("uuid", orderUUID);
    line1 = models["pos.order.line"].getBy("uuid", line1UUID);

    models["pos.pack.operation.lot"].create({ pos_order_line_id: line1, lot_name: "lot2" });
    {
        const keepCommandResult = models.serializeForORM(order, { keepCommands: true });
        const result = models.serializeForORM(order);
        expect(keepCommandResult).toEqual(result);
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
        "pos.pack.operation.lot": [
            {
                id: 99,
                pos_order_line_id: 11,
                lot_name: "lot1",
            },
            {
                id: 999,
                pos_order_line_id: 11,
                lot_name: "lot2",
            },
        ],
    });
    order = models["pos.order"].getBy("uuid", orderUUID);
    order.lines[0].pack_lot_ids[1].delete();
    order.lines[0].pack_lot_ids[0].delete();
    {
        const keepCommandResult = models.serializeForORM(order, { keepCommands: true });
        const result = models.serializeForORM(order);
        expect(keepCommandResult).toEqual(result);
        expect(result.lines.length).toBe(1);
        const pack_lot_ids = result.lines[0][2].pack_lot_ids;
        expect(pack_lot_ids.length).toBe(2);
        expect(pack_lot_ids).toEqual([
            [3, 999],
            [3, 99],
        ]);
    }
});

test("nested lines relationship", async () => {
    await makeMockServer();
    const models = getRelatedModelsInstance(false);
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
        const keepCommandResult = models.serializeForORM(order, { keepCommands: true });
        const result = models.serializeForORM(order);
        expect(keepCommandResult).toEqual(result);
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

    line1.qty = 99;
    {
        const keepCommandResult = models.serializeForORM(order, { keepCommands: true });
        const result = models.serializeForORM(order);
        expect(keepCommandResult).toEqual(result);
        expect(result.lines.length).toBe(1);
        expect(result.lines[0][0]).toBe(1);
        expect(result.lines[0][1]).toBe(11);
        expect(result.lines[0][2].qty).toBe(99);
        expect(result.relations_uuid_mapping).toBe(undefined);
    }
});

test("recursive relationship with group of lines", async () => {
    await makeMockServer();
    const models = getRelatedModelsInstance(false);
    let order = models["pos.order"].create({});
    let line1 = models["pos.order.line"].create({
        order_id: order,
    });
    let line2 = models["pos.order.line"].create({
        order_id: order,
        combo_parent_id: line1,
    });
    let line3 = models["pos.order.line"].create({
        order_id: order,
        combo_parent_id: line1,
    });
    models["pos.order.line"].create({
        order_id: order,
        combo_parent_id: line1,
    });

    expect(order.lines.length).toBe(4);
    expect(order.lines[0].combo_line_ids.length).toBe(3);

    {
        const keepCommandResult = models.serializeForORM(order, { keepCommands: true });
        const result = models.serializeForORM(order);
        expect(keepCommandResult).toEqual(result);
        expect(result.lines.length).toBe(4);
        expect(result.lines[0][2].combo_parent_id).toBeEmpty();
        expect(result.lines[1][2].combo_parent_id).toBeEmpty();

        const { relations_uuid_mapping } = result;
        expect(Object.keys(relations_uuid_mapping["pos.order.line"]).length).toBe(3);
        expect(relations_uuid_mapping["pos.order.line"][line2.uuid]["combo_parent_id"]).toBe(
            line1.uuid
        );
        expect(relations_uuid_mapping["pos.order.line"][line3.uuid]["combo_parent_id"]).toBe(
            line1.uuid
        );
    }

    models.connectNewData({
        "pos.order": [
            {
                id: 1,
                lines: [110, 111],
                uuid: order.uuid,
            },
        ],
        "pos.order.line": [
            {
                id: 1,
                uuid: line1.uuid,
            },
            {
                id: 110,
                order_id: 1,
                uuid: line2.uuid,
                combo_parent_id: 1,
            },
            {
                id: 111,
                order_id: 1,
                uuid: line3.uuid,
                combo_parent_id: 1,
            },
        ],
    });

    order = models["pos.order"].getBy("uuid", order.uuid);
    line1 = models["pos.order.line"].getBy("uuid", line1.uuid);
    line2 = models["pos.order.line"].getBy("uuid", line2.uuid);
    line3 = models["pos.order.line"].getBy("uuid", line3.uuid);

    {
        const keepCommandResult = models.serializeForORM(order, { keepCommands: true });
        const result = models.serializeForORM(order);
        expect(keepCommandResult).toEqual(result);
        expect(result.relations_uuid_mapping).toBe(undefined);
    }

    // Delete line
    line3.delete();
    {
        const keepCommandResult = models.serializeForORM(order, { keepCommands: true });
        const result = models.serializeForORM(order);
        expect(keepCommandResult).toEqual(result);

        expect(result.lines.length).toBe(2);
        expect(result.lines[0][0]).toBe(3);
        expect(result.lines[0][1]).toBe(111);
        expect(result.relations_uuid_mapping).toBe(undefined);
    }

    {
        //All update/delete have been cleared
        const keepCommandResult = models.serializeForORM(order, { keepCommands: true });
        const result = models.serializeForORM(order);
        expect(keepCommandResult).toEqual(result);
        expect(result.lines).toHaveLength(1);
    }
});

test("grouped lines and nested lines", async () => {
    await makeMockServer();
    const models = getRelatedModelsInstance(false);
    const order = models["pos.order"].create({});
    const parentLine = models["pos.order.line"].create({ order_id: order });
    const line1 = models["pos.order.line"].create({
        order_id: order,
        combo_parent_id: parentLine,
    });
    const line2 = models["pos.order.line"].create({
        order_id: order,
        combo_parent_id: parentLine,
    });
    const line3 = models["pos.order.line"].create({
        order_id: order,
    });

    {
        const keepCommandResult = models.serializeForORM(order, { keepCommands: true });
        const result = models.serializeForORM(order);
        expect(keepCommandResult).toEqual(result);

        expect(result.lines.length).toBe(4);
        const { relations_uuid_mapping } = result;
        expect(Object.keys(relations_uuid_mapping["pos.order.line"]).length).toBe(2);

        const lineMapping = relations_uuid_mapping["pos.order.line"];
        expect(lineMapping[line1.uuid]["combo_parent_id"]).toBe(parentLine.uuid);
        expect(lineMapping[line2.uuid]["combo_parent_id"]).toBe(parentLine.uuid);
        expect(lineMapping[line3.uuid]?.["combo_parent_id"]?.length).toBeEmpty();
    }
});

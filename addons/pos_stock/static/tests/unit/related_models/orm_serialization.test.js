import { expect, test } from "@odoo/hoot";
import { getRelatedModelsInstance } from "@point_of_sale/../tests/unit/data/get_model_definitions";
import { makeMockServer } from "@web/../tests/web_test_helpers";
import { definePosStockModels } from "@pos_stock/../tests/unit/data/generate_model_definitions";

definePosStockModels();

test("serialization of dynamic model with uuid (pack lots)", async () => {
    await makeMockServer();
    const models = getRelatedModelsInstance(false);
    let order = models["pos.order"].create({});
    const orderUUID = order.uuid;

    let line1 = models["pos.order.line"].create({
        order_id: order,
    });
    const line1UUID = line1.uuid;

    const lot1 = models["pos.pack.operation.lot"].create({
        pos_order_line_id: line1,
        lot_name: "lot1",
    });
    const lot1UUID = lot1.uuid;
    expect(lot1UUID).not.toBeEmpty();
    {
        const keepCommandResult = models.serializeForORM(order, { keepCommands: true });
        const result = models.serializeForORM(order);
        expect(keepCommandResult).toEqual(result);
        expect(result.lines.length).toBe(1);
        const pack_lot_ids = result.lines[0][2].pack_lot_ids;
        expect(pack_lot_ids.length).toBe(1);
        expect(pack_lot_ids[0][0]).toBe(0);
        expect(pack_lot_ids[0][1]).toBe(0);
        expect(pack_lot_ids[0][2]).toEqual({
            lot_name: "lot1",
            write_date: false,
            expiration_date: false,
            uuid: lot1UUID,
        });
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
                uuid: lot1UUID,
            },
        ],
    });

    order = models["pos.order"].getBy("uuid", orderUUID);
    line1 = models["pos.order.line"].getBy("uuid", line1UUID);

    expect(line1.pack_lot_ids.map((p) => p.id)).toEqual([99]);
    expect(models["pos.pack.operation.lot"].getBy("uuid", lot1UUID).id).toBe(99);

    const lot2 = models["pos.pack.operation.lot"].create({
        pos_order_line_id: line1,
        lot_name: "lot2",
    });
    const lot2UUID = lot2.uuid;
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
        expect(pack_lot_ids[0][2].uuid).toEqual(lot2UUID);
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
                uuid: lot1UUID,
            },
            {
                id: 999,
                pos_order_line_id: 11,
                lot_name: "lot2",
                uuid: lot2UUID,
            },
        ],
    });
    order = models["pos.order"].getBy("uuid", orderUUID);
    expect(order.lines[0].pack_lot_ids.map((p) => p.id)).toEqual([99, 999]);
    expect(models["pos.pack.operation.lot"].length).toBe(2);
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

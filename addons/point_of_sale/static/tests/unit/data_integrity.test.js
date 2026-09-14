import { expect, test } from "@odoo/hoot";
import { groupOrderlines } from "@point_of_sale/app/components/order_display/orderline_groups";
import IndexedDB from "@point_of_sale/app/models/utils/indexed_db";
import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { luxon } from "@web/core/l10n/luxon";
import { ConnectionLostError, RPCError } from "@web/core/network";

import { definePosModels } from "./data/generate_model_definitions.js";
import { getFilledOrder, setupPosEnv } from "./utils.js";

definePosModels();

async function openDatabase(name, stores) {
    let db;
    await new Promise((resolve) => {
        db = new IndexedDB(name, false, stores, resolve);
    });
    return db;
}

test("IndexedDB rejects malformed keys and persists valid orders", async () => {
    const name = `audit-challenge-${crypto.randomUUID()}`;
    const db = await openDatabase(name, [["uuid", "pos.order"]]);
    try {
        const good = await db.create("pos.order", [{ uuid: "valid", state: "paid" }]);
        expect(good[0].status).toBe("fulfilled");
        const bad = await db.create("pos.order", [{ state: "paid" }]);
        expect(bad[0].status).toBe("rejected");
        expect((await db.readAll())["pos.order"]).toEqual([
            { uuid: "valid", state: "paid" },
        ]);
        const realOrderStore = await setupPosEnv();
        const order = await getFilledOrder(realOrderStore);
        const serialized = order.serializeForIndexedDB();
        expect(typeof serialized.uuid).toBe("string");
        expect((await db.create("pos.order", [serialized]))[0].status).toBe(
            "fulfilled",
        );
        expect((await db.readAll())["pos.order"]).toHaveLength(2);
    } finally {
        db.db.close();
        window.indexedDB.deleteDatabase(name);
    }
});

test("legacy offline entries replay chronologically after reopening", async () => {
    const name = `audit-queue-${crypto.randomUUID()}`;
    let db = await openDatabase(name, [["uuid", "pos.unsync.queue"]]);
    const entries = [
        {
            uuid: "z",
            date: "2026-09-05T12:00:00Z",
            args: [
                {
                    type: "write",
                    model: "pos.category",
                    ids: [1],
                    values: { name: "old" },
                },
            ],
        },
        {
            uuid: "a",
            date: "2026-09-05T12:01:00Z",
            args: [
                {
                    type: "write",
                    model: "pos.category",
                    ids: [1],
                    values: { name: "new" },
                },
            ],
        },
    ];
    await db.create("pos.unsync.queue", entries);
    db.db.close();
    db = await openDatabase(name, [["uuid", "pos.unsync.queue"]]);
    try {
        const store = await setupPosEnv();
        const applied = [];
        patchWithCleanup(store.data, { indexedDB: db });
        patchWithCleanup(store.data.orm, {
            write: async (_model, _ids, values) => applied.push(values.name),
        });
        await store.data.restoreUnsyncQueue();
        expect(store.data.network.unsyncData.map((r) => r.uuid)).toEqual(["z", "a"]);
        await store.data.syncData();
        expect(applied).toEqual(["old", "new"]);
        expect(store.models["pos.category"].get(1).name).toBe("new");
    } finally {
        db.db.close();
        window.indexedDB.deleteDatabase(name);
    }
});

test("partial reads clear many-to-one relations", async () => {
    const store = await setupPosEnv();
    const partner = store.models["res.partner"].getAll()[0];
    const country = store.models["res.country"].getAll()[0];
    partner.country_id = country;
    patchWithCleanup(store.data.orm, {
        read: async () => [{ id: partner.id, country_id: false }],
    });
    await store.data.read("res.partner", [partner.id], ["id", "country_id"]);
    expect(Boolean(partner.country_id)).toBe(false);
    await store.data.read("res.partner", [partner.id]);
    expect(Boolean(partner.country_id)).toBe(false);
});

test("preset getters follow the clock and regenerate their horizon", async () => {
    patchWithCleanup(luxon.Settings, {
        now: () => Date.parse("2026-09-07T10:10:00Z"),
        defaultZone: luxon.FixedOffsetZone.instance(0),
    });
    const store = await setupPosEnv();
    const preset = store.models["pos.preset"].get(2);
    const attendance = store.models["resource.calendar.attendance"].getAll()[0];
    attendance.update({ dayofweek: "0", hour_from: 10, hour_to: 11 });
    preset.update({ attendance_ids: [["set", attendance]], interval_time: 20 });
    preset.computeAvailabilities();
    expect(preset.currentSlot.datetime.toISOTime()).toBe("10:00:00.000Z");
    expect(preset.nextSlot.datetime.toISOTime()).toBe("10:20:00.000Z");
    luxon.Settings.now = () => Date.parse("2026-09-07T10:20:00Z");
    expect(preset.currentSlot.datetime.toISOTime()).toBe("10:20:00.000Z");
    luxon.Settings.now = () => Date.parse("2026-09-14T10:30:00Z");
    expect(preset.currentSlot.datetime.toISODate()).toBe("2026-09-14");
    expect(preset.nextSlot.datetime.toISOTime()).toBe("10:40:00.000Z");
    luxon.Settings.now = () => Date.parse("2026-09-15T10:10:00Z");
    expect(preset.currentSlot).toBe(false);
    expect(preset.nextSlot).toBe(undefined);
    const coldPreset = store.models["pos.preset"].get(3);
    expect(() => coldPreset.currentSlot).not.toThrow();
});

test("partial reads replace nonempty and empty x2many relations", async () => {
    const store = await setupPosEnv();
    const product = store.models["product.template"].get(5);
    const categories = store.models["pos.category"].getAll().slice(0, 2);
    product.update({ pos_categ_ids: [["set", ...categories]] });
    expect(product.pos_categ_ids).toHaveLength(2);
    let serverIds = [categories[0].id];
    patchWithCleanup(store.data.orm, {
        read: async () => [{ id: product.id, pos_categ_ids: serverIds }],
    });
    await store.data.read("product.template", [product.id], ["id", "pos_categ_ids"]);
    expect(product.pos_categ_ids).toHaveLength(1);
    await store.data.read("product.template", [product.id]);
    expect(product.pos_categ_ids).toHaveLength(1);
    serverIds = [];
    await store.data.read("product.template", [product.id], ["id", "pos_categ_ids"]);
    expect(product.pos_categ_ids).toHaveLength(0);
});

test("multi-record writes use one RPC and roll back all local records on rejection", async () => {
    const store = await setupPosEnv();
    const records = store.models["pos.category"].getAll().slice(0, 2);
    const originalNames = records.map((r) => r.name);
    const committed = [];
    const error = new RPCError("rejected");
    patchWithCleanup(store.data.orm, {
        write: async (_model, ids) => {
            if (ids.includes(records[1].id)) {
                throw error;
            }
            committed.push(...ids);
            return true;
        },
    });
    let thrown;
    try {
        await store.data.write(
            "pos.category",
            records.map((r) => r.id),
            { name: "Changed" },
        );
    } catch (e) {
        thrown = e;
    }
    expect(thrown).toBe(error);
    expect(committed).toEqual([]);
    expect(records[0].name).toBe(originalNames[0]);
    expect(records[1].name).toBe(originalNames[1]);
});

test("an acknowledged optimistic write does not overwrite a newer local edit", async () => {
    const store = await setupPosEnv();
    const record = store.models["pos.category"].get(1);
    let resolveRequest;
    patchWithCleanup(store.data.orm, {
        write: () =>
            new Promise((resolve) => {
                resolveRequest = resolve;
            }),
    });
    const writing = store.data.write("pos.category", [record.id], { name: "Sent" });
    expect(record.name).toBe("Sent");
    record.update({ name: "Edited while waiting" });
    resolveRequest(true);
    await writing;
    expect(record.name).toBe("Edited while waiting");
});

test("direct ORM writes still update local records after acknowledgement", async () => {
    const store = await setupPosEnv();
    const record = store.models["pos.category"].get(1);
    patchWithCleanup(store.data.orm, { write: async () => true });
    await store.data.ormWrite("pos.category", [record.id], { name: "Acknowledged" });
    expect(record.name).toBe("Acknowledged");
});

test("replaying an optimistic write updates the restored local record", async () => {
    const store = await setupPosEnv();
    const record = store.models["pos.category"].get(1);
    let persisted;
    patchWithCleanup(store.data.indexedDB, {
        createOrdered: async (_store, row) => {
            persisted = structuredClone({ ...row, sequence: 1 });
            return persisted;
        },
        readAll: async () => ({ "pos.unsync.queue": [persisted] }),
    });
    patchWithCleanup(store.data.orm, {
        write: async () => {
            throw new ConnectionLostError();
        },
    });
    await store.data.write("pos.category", [record.id], { name: "Queued" });
    store.data.network.unsyncData.length = 0;
    await store.data.restoreUnsyncQueue();
    record.update({ name: "Restored cache" });
    patchWithCleanup(store.data.orm, { write: async () => true });
    await store.data.syncData();
    expect(record.name).toBe("Queued");
    expect(store.data.network.unsyncData).toHaveLength(0);
});

test("replaying a live optimistic write preserves edits made while offline", async () => {
    const store = await setupPosEnv();
    const record = store.models["pos.category"].get(1);
    patchWithCleanup(store.data.orm, {
        write: async () => {
            throw new ConnectionLostError();
        },
    });
    await store.data.write("pos.category", [record.id], { name: "Queued" });
    record.name = "Edited offline";
    const sent = [];
    patchWithCleanup(store.data.orm, {
        write: async (_model, _ids, values) => {
            sent.push(values.name);
            return true;
        },
    });
    await store.data.syncData();
    expect(sent).toEqual(["Queued"]);
    expect(record.name).toBe("Edited offline");
    expect(store.data.network.unsyncData).toHaveLength(0);
});

test("validation reports RPC rejection and blocks navigation", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const cash = store.models["pos.payment.method"].find((p) => p.is_cash_count);
    order.addPaymentline(cash);
    const validation = new OrderPaymentValidation({
        pos: store,
        orderUuid: order.uuid,
    });
    const navigations = [];
    patchWithCleanup(store, { navigate: (page) => navigations.push(page) });
    patchWithCleanup(store.config, { iface_print_auto: false });
    const error = new RPCError("rejected");
    error.data = { message: "Rejected by challenge", debug: "" };
    error.exceptionName = "odoo.exceptions.UserError";
    patchWithCleanup(store.data.orm, {
        call: async () => {
            throw error;
        },
    });
    const result = await validation.validateOrder();
    expect(order.state).toBe("draft");
    expect(navigations).toEqual([]);
    expect(result).toBe(false);
});

test("batch create assigns every returned identity", async () => {
    const store = await setupPosEnv();
    patchWithCleanup(store.data.orm, { create: async () => [801, 802] });
    const records = await store.data.create("pos.category", [
        { name: "Audit A" },
        { name: "Audit B" },
    ]);
    expect(records[0].id).toBe(801);
    expect(records[1].id).toBe(802);
    expect(store.models["pos.category"].get(802)).toBe(records[1]);
});

test("queue sequence is atomic across connections and survives a backwards clock", async () => {
    const name = `queue-sequence-${crypto.randomUUID()}`;
    const first = await openDatabase(name, [["uuid", "pos.unsync.queue"]]);
    const second = await openDatabase(name, [["uuid", "pos.unsync.queue"]]);
    try {
        patchWithCleanup(Date, { now: () => 1000 });
        const [a, b] = await Promise.all([
            first.createOrdered("pos.unsync.queue", { uuid: "z", args: [] }),
            second.createOrdered("pos.unsync.queue", { uuid: "a", args: [] }),
        ]);
        expect(a.sequence).toBeLessThan(b.sequence);
        Date.now = () => 1;
        const c = await first.createOrdered("pos.unsync.queue", {
            uuid: "c",
            args: [],
        });
        expect(c.sequence).toBeGreaterThan(b.sequence);
        const retry = await second.createOrdered("pos.unsync.queue", { ...a, try: 2 });
        expect(retry.sequence).toBe(a.sequence);
        expect((await first.readAll())["pos.unsync.queue"]).toHaveLength(3);
    } finally {
        first.db.close();
        second.db.close();
        window.indexedDB.deleteDatabase(name);
    }
});

test("offline queue snapshots caller arguments and refuses undurable writes", async () => {
    const store = await setupPosEnv();
    patchWithCleanup(store.data.network, { offline: true });
    const values = { name: "Queued" };
    await store.data.ormWrite("pos.category", [1], values);
    values.name = "Changed later";
    expect(store.data.network.unsyncData[0].args[0].values.name).toBe("Queued");
    const record = store.models["pos.category"].get(1);
    const original = record.name;
    const failure = new Error("Storage full");
    patchWithCleanup(store.data.indexedDB, {
        createOrdered: async () => {
            throw failure;
        },
    });
    let thrown;
    try {
        await store.data.write("pos.category", [1], { name: "Undurable" });
    } catch (error) {
        thrown = error;
    }
    expect(thrown).toBe(failure);
    expect(record.name).toBe(original);
    expect(store.data.network.unsyncData).toHaveLength(1);
});

test("failed deletion preserves local records", async () => {
    const store = await setupPosEnv();
    const record = store.models["pos.category"].get(1);
    const failure = new RPCError("Rejected");
    patchWithCleanup(store.data.orm, {
        unlink: async () => {
            throw failure;
        },
    });
    let thrown;
    try {
        await store.data.delete("pos.category", [record.id]);
    } catch (error) {
        thrown = error;
    }
    expect(thrown).toBe(failure);
    expect(store.models["pos.category"].get(record.id)).toBe(record);
});

test("partial dynamic reads retain the existing UUID and unspecified fields", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    await store.syncAllOrders({ orders: [order] });
    expect(typeof order.id).toBe("number");
    const count = store.models["pos.order"].length;
    const uuid = order.uuid;
    const lines = [...order.lines];
    patchWithCleanup(store.data.orm, {
        read: async () => [{ id: order.id, general_customer_note: "Server note" }],
    });
    const result = await store.data.read(
        "pos.order",
        [order.id],
        ["id", "general_customer_note"],
    );
    expect(result[0]).toBe(order);
    expect(order.uuid).toBe(uuid);
    expect(order.general_customer_note).toBe("Server note");
    expect(order.lines).toEqual(lines);
    expect(store.models["pos.order"].length).toBe(count);
});

test("foreground validation does not navigate after an explicit refusal", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    order.addPaymentline(
        store.models["pos.payment.method"].find((p) => p.is_cash_count),
    );
    const validation = new OrderPaymentValidation({
        pos: store,
        orderUuid: order.uuid,
    });
    const navigations = [];
    patchWithCleanup(store, { navigate: (page) => navigations.push(page) });
    patchWithCleanup(validation, { finalizeValidation: async () => false });
    expect(await validation.validateOrder()).toBe(false);
    expect(navigations).toEqual([]);
});

test("queued arguments reflect the request before a delayed connection failure", async () => {
    const store = await setupPosEnv();
    let rejectRequest;
    patchWithCleanup(store.data.orm, {
        write: () =>
            new Promise((_resolve, reject) => {
                rejectRequest = reject;
            }),
    });
    const values = { name: "Sent" };
    const writing = store.data.ormWrite("pos.category", [1], values);
    values.name = "Edited while waiting";
    rejectRequest(new ConnectionLostError());
    await writing;
    expect(store.data.network.unsyncData[0].args[0].values.name).toBe("Sent");
});

test("display grouping keeps different configured attributes visible", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const line = order.lines[0];
    const leather = store.models["product.template.attribute.value"].create({
        name: "Leather",
    });
    const wool = store.models["product.template.attribute.value"].create({
        name: "Wool",
    });
    line.update({ attribute_value_ids: [["set", leather]], qty: 0.1 });
    const second = store.models["pos.order.line"].create({
        order_id: order,
        product_id: line.product_id,
        price_unit: line.price_unit,
        qty: 0.7,
        attribute_value_ids: [["set", wool]],
    });
    expect(groupOrderlines([line, second]).lines).toHaveLength(2);
    second.update({ attribute_value_ids: [["set", leather]] });
    const grouped = groupOrderlines([line, second]);
    expect(grouped.lines).toHaveLength(1);
    expect(grouped.groupOf.get(grouped.lines[0].uuid).quantity).toBeCloseTo(0.8);
});

test("display grouping keeps distinct lots independently selectable", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const line = order.lines[0];
    line.product_id.product_tmpl_id.tracking = "lot";
    line.update({ pack_lot_ids: [["create", { lot_name: "LOT-A" }]] });
    const second = store.models["pos.order.line"].create({
        order_id: order,
        product_id: line.product_id,
        price_unit: line.price_unit,
        qty: 1,
        pack_lot_ids: [["create", { lot_name: "LOT-B" }]],
    });
    expect(groupOrderlines([line, second]).lines).toEqual([line, second]);
});

test("display grouping keeps the lines of a non-groupable unit apart", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const line = order.lines[0];
    line.product_id.uom_id = store.models["uom.uom"].get(5);
    const second = store.models["pos.order.line"].create({
        order_id: order,
        product_id: line.product_id,
        price_unit: line.price_unit,
        qty: 1,
    });
    expect(groupOrderlines([line, second]).lines).toEqual([line, second]);
});

test("a partial read fetches complete data before loading an unknown record", async () => {
    const store = await setupPosEnv();
    const partner = store.models["res.partner"].getAll()[0];
    const id = partner.id;
    const originalName = partner.name;
    partner.delete();
    const calls = [];
    const read = store.data.orm.read.bind(store.data.orm);
    patchWithCleanup(store.data.orm, {
        read: async (model, ids, fields, options) => {
            calls.push([...fields]);
            return read(model, ids, fields, options);
        },
    });
    const records = await store.data.read("res.partner", [id], ["id"]);
    expect(calls).toHaveLength(2);
    expect(calls[1]).toEqual(store.data.fields["res.partner"]);
    expect(records[0].name).toBe(originalName);
    expect(store.models["res.partner"].get(id)).toBe(records[0]);
});

import { describe, expect, test } from "@odoo/hoot";
import { computed } from "@odoo/owl";

import { toCommands } from "@web/model/store/commands";
import { fields } from "@web/model/store/fields";
import { Model } from "@web/model/store/model";
import { RecordStore } from "@web/model/store/store";

describe.current.tags("headless");

class Partner extends Model {
    static _name = "res.partner";

    name = fields.Char();
    order_ids = fields.One2many("sale.order", { inverse: "partner_id" });
    tag_ids = fields.Many2many("res.partner.tag", { inverse: "partner_ids" });

    get label() {
        return `[${this.id}] ${this.name}`;
    }
}

class Tag extends Model {
    static _name = "res.partner.tag";

    name = fields.Char();
    partner_ids = fields.Many2many("res.partner");
}

class Order extends Model {
    static _name = "sale.order";
    static _tracked = true;

    name = fields.Char();
    partner_id = fields.Many2one("res.partner");
    line_ids = fields.One2many("sale.order.line", { inverse: "order_id" });
    tag_ids = fields.Many2many("res.partner.tag");

    get total() {
        return this.line_ids.reduce((sum, line) => sum + line.qty * line.price, 0);
    }
}

class Line extends Model {
    static _name = "sale.order.line";
    static _tracked = true;

    order_id = fields.Many2one("sale.order");
    product = fields.Char();
    qty = fields.Integer({ default: 1 });
    price = fields.Float();
}

function makeStore(definitions) {
    return new RecordStore({ models: [Partner, Tag, Order, Line], definitions });
}

/**
 * @param {RecordStore} store
 */
function loadOrder(store) {
    return store.load("sale.order", {
        id: 1,
        name: "SO1",
        partner_id: { id: 5, name: "Bob", order_ids: [1] },
        line_ids: [
            { id: 11, product: "Desk", qty: 1, price: 100 },
            { id: 12, product: "Chair", qty: 4, price: 50 },
        ],
    });
}

describe("declarations", () => {
    test("fields are accessors, class members work", () => {
        const store = makeStore();
        const partner = store.create("res.partner", { name: "Alice" });
        expect(partner.name).toBe("Alice");
        expect(partner.label).toBe("[virtual_1] Alice");
        expect(partner).toBeInstanceOf(Partner);
        // records carry no own string keys: fields live on the prototype
        expect(Object.keys(partner)).toEqual([]);
    });

    test("server definitions are merged under JS declarations", () => {
        const store = makeStore({
            "res.partner": {
                fields: {
                    name: { type: "char", string: "Name", required: true },
                    email: { type: "char", string: "Email" },
                },
            },
            "res.country": { fields: { code: { type: "char" } } },
        });
        const partnerFields = store.model("res.partner").fieldsByName;
        expect(partnerFields.name.required).toBe(true);
        expect(partnerFields.email.type).toBe("char");
        // models known only from the server get a generic class
        const country = store.create("res.country", { code: "BE" });
        expect(country.code).toBe("BE");
    });

    test("inverses come from the get_definitions format", () => {
        const store = new RecordStore({
            definitions: {
                "res.partner": {
                    fields: {
                        name: { type: "char" },
                        parent_id: {
                            type: "many2one",
                            relation: "res.partner",
                            inverse_fname_by_model_name: { "res.partner": "child_ids" },
                        },
                        child_ids: {
                            type: "one2many",
                            relation: "res.partner",
                            inverse_fname_by_model_name: { "res.partner": "parent_id" },
                        },
                    },
                },
            },
        });
        const [parent, child] = store.load("res.partner", [
            { id: 1, name: "Parent", child_ids: [] },
            { id: 2, name: "Child", parent_id: 1 },
        ]);
        expect(parent.child_ids).toEqual([child]);
    });

    test("extension classes are chained like _inherit", () => {
        class Thing extends Model {
            static _name = "x.thing";
            name = fields.Char();
            get label() {
                return this.name;
            }
        }
        class ThingA extends Thing {
            static _inherit = "x.thing";
            color = fields.Char();
            get label() {
                return super.label + "+a";
            }
        }
        class ThingB extends Thing {
            static _inherit = "x.thing";
            size = fields.Integer();
            get label() {
                return super.label + "+b";
            }
        }
        const store = new RecordStore({ models: [Thing, ThingA, ThingB] });
        const thing = store.create("x.thing", { name: "t", color: "red", size: 3 });
        expect(thing.label).toBe("t+a+b");
        expect(thing).toBeInstanceOf(ThingA);
        expect(thing).toBeInstanceOf(ThingB);
        expect([thing.color, thing.size]).toEqual(["red", 3]);
    });

    test("class fields must be field declarations", () => {
        class Bad extends Model {
            static _name = "x.bad";
            count = 0;
        }
        expect(() => new RecordStore({ models: [Bad] })).toThrow(/not a field declaration/);
    });
});

describe("identity and loading", () => {
    test("loading merges into one object per record", () => {
        const store = makeStore();
        const partner = store.load("res.partner", { id: 1, name: "Alice" });
        expect(store.load("res.partner", { id: 1, tag_ids: [] })).toBe(partner);
        expect(partner.name).toBe("Alice");
        expect(partner.tag_ids).toEqual([]);
        expect(store.records("res.partner")).toEqual([partner]);
    });

    test("unknown ids become stubs, filled when loaded", () => {
        const store = makeStore();
        const order = store.load("sale.order", { id: 1, partner_id: 5 });
        const bob = order.partner_id;
        expect(bob).toBe(store.get("res.partner", 5));
        expect(bob.name).toBe(undefined);
        expect(store.records("res.partner")).toEqual([]);
        store.load("res.partner", { id: 5, name: "Bob" });
        expect(order.partner_id).toBe(bob);
        expect(bob.name).toBe("Bob");
        expect(store.records("res.partner")).toEqual([bob]);
    });

    test("web_read values: many2one objects and x2many lists", () => {
        const store = makeStore();
        const order = loadOrder(store);
        expect(order.partner_id.name).toBe("Bob");
        expect(order.line_ids.map((line) => line.product)).toEqual(["Desk", "Chair"]);
        expect(order.line_ids[0].order_id).toBe(order);
        expect(order.total).toBe(300);
        expect(store.isDirty(order)).toBe(false);
        expect(store.isDirty(order.line_ids[0])).toBe(false);
    });
});

describe("relations", () => {
    test("many2one and one2many stay in sync", () => {
        const store = makeStore();
        const [alice, bob] = store.load("res.partner", [
            { id: 1, name: "Alice", order_ids: [] },
            { id: 2, name: "Bob", order_ids: [] },
        ]);
        const order = store.create("sale.order", { name: "SO", partner_id: 1 });
        expect(alice.order_ids).toEqual([order]);
        order.partner_id = bob;
        expect(alice.order_ids).toEqual([]);
        expect(bob.order_ids).toEqual([order]);
    });

    test("moving a line to another order through the one2many", () => {
        const store = makeStore();
        const order1 = loadOrder(store);
        const order2 = store.load("sale.order", { id: 2, line_ids: [] });
        const [desk, chair] = order1.line_ids;
        order2.line_ids = [...order2.line_ids, desk];
        expect(desk.order_id).toBe(order2);
        expect(order1.line_ids).toEqual([chair]);
    });

    test("many2many inverse", () => {
        const store = makeStore();
        const partner = store.load("res.partner", { id: 1, tag_ids: [] });
        const [vip, stub] = store.load("res.partner.tag", [{ id: 1, partner_ids: [] }, { id: 2 }]);
        partner.tag_ids = [vip, stub];
        expect(vip.partner_ids).toEqual([partner]);
        // a list that is not loaded is left alone
        expect(stub.partner_ids).toBe(undefined);
        partner.tag_ids = [stub];
        expect(vip.partner_ids).toEqual([]);
    });

    test("one2many lists that are not loaded are left alone", () => {
        const store = makeStore();
        const order = store.load("sale.order", { id: 1, name: "SO1" });
        const line = store.create("sale.order.line", { order_id: order });
        expect(line.order_id).toBe(order);
        expect(order.line_ids).toBe(undefined);
    });
});

describe("reactivity", () => {
    test("field mode: a computation only depends on the fields it reads", () => {
        const store = makeStore();
        const order = store.load("sale.order", { id: 1, name: "SO1", partner_id: 5 });
        let runs = 0;
        const name = computed(() => {
            runs++;
            return order.name;
        });
        expect(name()).toBe("SO1");
        order.partner_id = 6;
        expect(name()).toBe("SO1");
        expect(runs).toBe(1);
        order.name = "SO1b";
        expect(name()).toBe("SO1b");
        expect(runs).toBe(2);
    });

    test("record, model and none modes", () => {
        class ByRecord extends Model {
            static _name = "x.by.record";
            static _reactivity = "record";
            a = fields.Char();
            b = fields.Char();
        }
        class ByModel extends Model {
            static _name = "x.by.model";
            static _reactivity = "model";
            a = fields.Char();
        }
        class Untracked extends Model {
            static _name = "x.untracked";
            static _reactivity = "none";
            a = fields.Char();
        }
        const store = new RecordStore({ models: [ByRecord, ByModel, Untracked] });
        const [r1, r2] = store.load("x.by.record", [{ id: 1 }, { id: 2 }]);
        const [m1, m2] = store.load("x.by.model", [{ id: 1 }, { id: 2 }]);
        const [u1] = store.load("x.untracked", [{ id: 1, a: "x" }]);
        const runs = { record: 0, model: 0, none: 0 };
        const counted = (key, read) =>
            computed(() => {
                runs[key]++;
                return read();
            });
        const byRecord = counted("record", () => r1.a);
        const byModel = counted("model", () => m1.a);
        const untracked = counted("none", () => u1.a);
        byRecord();
        byModel();
        untracked();

        r1.b = "changed"; // same record, other field
        r2.a = "changed"; // other record
        m2.a = "changed"; // other record, same model
        u1.a = "changed";
        byRecord();
        byModel();
        untracked();
        expect(runs).toEqual({ record: 2, model: 2, none: 1 });
    });

    test("records() reacts to creations and deletions", () => {
        const store = makeStore();
        store.load("res.partner", [{ id: 1, name: "Alice" }]);
        let runs = 0;
        const count = computed(() => {
            runs++;
            return store.records("res.partner").length;
        });
        expect(count()).toBe(1);
        store.get("res.partner", 1).name = "Alice B.";
        expect(count()).toBe(1);
        expect(runs).toBe(1);
        const bob = store.create("res.partner", { name: "Bob" });
        expect(count()).toBe(2);
        store.delete(bob);
        expect(count()).toBe(1);
    });

    test("dirty state is reactive", () => {
        const store = makeStore();
        const order = loadOrder(store);
        const dirty = computed(() => store.isDirty(order));
        expect(dirty()).toBe(false);
        order.name = "SO1b";
        expect(dirty()).toBe(true);
        store.discard(order);
        expect(dirty()).toBe(false);
    });
});

describe("change tracking", () => {
    test("local writes are changes, server loads are not", () => {
        const store = makeStore();
        const order = loadOrder(store);
        order.name = "SO1b";
        expect(store.isDirty(order)).toBe(true);
        // a server value under a local change: the change keeps showing
        store.load("sale.order", { id: 1, name: "SO1 (server)" });
        expect(order.name).toBe("SO1b");
        store.discard(order);
        expect(order.name).toBe("SO1 (server)");
        expect(store.isDirty(order)).toBe(false);
    });

    test("untracked models write directly", () => {
        const store = makeStore();
        const partner = store.load("res.partner", { id: 1, name: "Alice" });
        partner.name = "Alice B.";
        expect(partner.name).toBe("Alice B.");
        expect(store.isDirty(partner)).toBe(false);
    });

    test("discard restores the record and its lines", () => {
        const store = makeStore();
        const order = loadOrder(store);
        const [desk, chair] = order.line_ids;
        desk.qty = 10;
        store.delete(chair);
        const lamp = store.create("sale.order.line", { order_id: order, product: "Lamp" });
        expect(order.line_ids).toEqual([desk, lamp]);

        store.discard(order);
        expect(order.line_ids).toEqual([desk, chair]);
        expect(desk.qty).toBe(1);
        expect(store.get("sale.order.line", 12)).toBe(chair);
        expect(store.get("sale.order.line", lamp.id)).toBe(null);
        expect(store.isDirty(order)).toBe(false);
    });

    test("deletions stay pending until acknowledged", () => {
        const store = makeStore();
        const order = loadOrder(store);
        const chair = order.line_ids[1];
        store.delete(chair);
        expect(store.get("sale.order.line", 12)).toBe(null);
        expect(store.isDirty(chair)).toBe(true);
        const { vals, version } = toCommands(order);
        expect(vals).toEqual({ line_ids: [[2, 12]] });
        store.ack(order, version);
        expect(store.isDirty(order)).toBe(false);
        expect(store.model("sale.order.line").records.has(12)).toBe(false);
    });
});

describe("commands", () => {
    test("new record: nested CREATE", () => {
        const store = makeStore();
        store.load("res.partner", { id: 5, name: "Bob" });
        const order = store.create("sale.order", { name: "SO", partner_id: 5 });
        const line = store.create("sale.order.line", {
            order_id: order,
            product: "Desk",
            price: 100,
        });
        expect(toCommands(order).vals).toEqual({
            name: "SO",
            partner_id: 5,
            line_ids: [[0, line.id, { product: "Desk", qty: 1, price: 100 }]],
        });
    });

    test("existing record: UPDATE, CREATE and DELETE from the diff", () => {
        const store = makeStore();
        const order = loadOrder(store);
        const [desk, chair] = order.line_ids;
        desk.qty = 3;
        store.delete(chair);
        const lamp = store.create("sale.order.line", {
            order_id: order,
            product: "Lamp",
            price: 20,
        });
        expect(toCommands(order).vals).toEqual({
            line_ids: [
                [1, 11, { qty: 3 }],
                [0, lamp.id, { product: "Lamp", qty: 1, price: 20 }],
                [2, 12],
            ],
        });
        const untouched = store.load("sale.order", { id: 2, name: "SO2", line_ids: [] });
        expect(toCommands(untouched).vals).toEqual({});
    });

    test("many2many as LINK and UNLINK", () => {
        const store = makeStore();
        const order = store.load("sale.order", { id: 1, tag_ids: [1, 2] });
        order.tag_ids = [store.get("res.partner.tag", 2), store.get("res.partner.tag", 3, true)];
        expect(toCommands(order).vals).toEqual({
            tag_ids: [
                [3, 1],
                [4, 3],
            ],
        });
    });

    test("ack keeps edits made during the save", () => {
        const store = makeStore();
        const order = loadOrder(store);
        const desk = order.line_ids[0];
        order.name = "A";
        const { version } = toCommands(order);
        // edits while the save is in flight
        order.name = "B";
        desk.qty = 2;
        store.ack(order, version);
        expect(store.isDirty(order)).toBe(true);
        expect(toCommands(order).vals).toEqual({ name: "B", line_ids: [[1, 11, { qty: 2 }]] });
    });

    test("saving a new record: ack, then swap virtual ids for server ids", () => {
        const store = makeStore();
        const order = store.create("sale.order", { name: "SO" });
        const line = store.create("sale.order.line", { order_id: order, product: "Desk" });
        const { version } = toCommands(order);
        // server answered: order 42 with line 101
        store.ack(order, version);
        store.rekey(order, 42);
        store.rekey(line, 101);
        store.load("sale.order", { id: 42, name: "SO/0042" });
        expect(store.get("sale.order", 42)).toBe(order);
        expect(store.isNew(order)).toBe(false);
        expect(line.order_id).toBe(order);
        expect(order.name).toBe("SO/0042");
        expect(toCommands(order).vals).toEqual({});
    });
});

describe("drafts", () => {
    test("a draft reads through and keeps its own changes", () => {
        const store = makeStore();
        const order = loadOrder(store);
        const draft = store.draft();
        const draftOrder = draft.own(order);
        expect(draftOrder).not.toBe(order);
        expect(draftOrder.name).toBe("SO1");
        draftOrder.name = "Draft";
        expect(order.name).toBe("SO1");
        expect(draft.isDirty()).toBe(true);
        expect(store.isDirty(order)).toBe(false);
        // changes in the parent show through fields the draft did not touch
        order.partner_id = 6;
        expect(draftOrder.partner_id.id).toBe(6);

        draft.commit();
        expect(order.name).toBe("Draft");
        expect(store.isDirty(order)).toBe(true);
        expect(draft.isDirty()).toBe(false);
        expect(draftOrder.name).toBe("Draft");
    });

    test("relations inside a draft are draft records", () => {
        const store = makeStore();
        const order = loadOrder(store);
        const draft = store.draft();
        const draftOrder = draft.get("sale.order", 1);
        const draftDesk = draftOrder.line_ids[0];
        expect(draftDesk).not.toBe(order.line_ids[0]);
        expect(draftDesk.order_id).toBe(draftOrder);

        draft.create("sale.order.line", { order_id: draftOrder, product: "Lamp" });
        expect(draftOrder.line_ids.map((l) => l.product)).toEqual(["Desk", "Chair", "Lamp"]);
        expect(order.line_ids.length).toBe(2);

        draft.discard();
        expect(draftOrder.line_ids.map((l) => l.product)).toEqual(["Desk", "Chair"]);
    });

    test("commit creates draft records in the parent, with their relations", () => {
        const store = makeStore();
        const order = loadOrder(store);
        const draft = store.draft();
        const draftOrder = draft.own(order);
        const draftLamp = draft.create("sale.order.line", {
            order_id: draftOrder,
            product: "Lamp",
            price: 20,
        });
        draft.commit();
        const lamp = order.line_ids[2];
        expect(lamp.product).toBe("Lamp");
        expect(lamp.order_id).toBe(order);
        expect(store.isNew(lamp)).toBe(true);
        // the draft's object now reads through to the parent record
        expect(draftLamp.price).toBe(20);
        expect(toCommands(order).vals).toEqual({
            line_ids: [[0, lamp.id, { product: "Lamp", qty: 1, price: 20 }]],
        });
    });

    test("nested drafts, like a dialog opened from a dialog", () => {
        const store = makeStore();
        const order = loadOrder(store);
        const level1 = store.draft();
        level1.own(order).name = "level 1";
        const level2 = level1.draft();
        const order2 = level2.own(order);
        expect(order2.name).toBe("level 1");

        order2.name = "level 2";
        level2.discard();
        expect(level1.own(order).name).toBe("level 1");

        order2.name = "level 2";
        level2.commit();
        expect(level1.own(order).name).toBe("level 2");
        expect(order.name).toBe("SO1");
        level1.commit();
        expect(order.name).toBe("level 2");
    });

    test("computations on a draft record see draft and parent changes", () => {
        const store = makeStore();
        const order = loadOrder(store);
        const draftOrder = store.draft().own(order);
        const name = computed(() => draftOrder.name);
        expect(name()).toBe("SO1");
        order.name = "from parent";
        expect(name()).toBe("from parent");
        draftOrder.name = "from draft";
        expect(name()).toBe("from draft");
        expect(order.name).toBe("from parent");
    });
});

describe("indexes", () => {
    test("unique indexes follow writes and deletions", () => {
        class Product extends Model {
            static _name = "product.product";
            static _indexes = ["barcode"];
            name = fields.Char();
            barcode = fields.Char();
        }
        const store = new RecordStore({ models: [Product] });
        store.load("product.product", [{ id: 1, name: "Desk", barcode: "111" }]);
        const desk = store.getBy("product.product", "barcode", "111");
        expect(desk.name).toBe("Desk");
        desk.barcode = "222";
        expect(store.getBy("product.product", "barcode", "111")).toBe(null);
        expect(store.getBy("product.product", "barcode", "222")).toBe(desk);
        store.delete(desk);
        expect(store.getBy("product.product", "barcode", "222")).toBe(null);
    });
});

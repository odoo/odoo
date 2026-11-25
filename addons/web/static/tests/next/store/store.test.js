import { animationFrame, describe, expect, test } from "@odoo/hoot";
import { Component, computed, onPatched, signal, useEffect, useScope, xml } from "@odoo/owl";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";

import { toCommands } from "@web/next/store/commands";
import { fieldFromDefinition, fields } from "@web/next/store/fields";
import { Model } from "@web/next/store/model";
import { Store } from "@web/next/store/store";

/** @import { Many2many, Many2one, One2many } from "@web/next/store/fields" */
/** @import { Extension } from "@web/next/store/model" */

describe.current.tags("headless");

/** @extends {Model<typeof Partner.fields>} */
class Partner extends Model {
    static _name = "res.partner";
    static fields = {
        name: fields.Char(),
        order_ids: /** @type {One2many<Order>} */ (
            fields.One2many("sale.order", { inverse: "partner_id" })
        ),
        tag_ids: /** @type {Many2many<Tag>} */ (
            fields.Many2many("res.partner.tag", { inverse: "partner_ids" })
        ),
    };

    label = computed(() => `[${this.id}] ${this.name()}`);
}

/** @extends {Model<typeof Tag.fields>} */
class Tag extends Model {
    static _name = "res.partner.tag";
    static fields = {
        name: fields.Char(),
        partner_ids: /** @type {Many2many<Partner>} */ (fields.Many2many("res.partner")),
    };
}

/** @extends {Model<typeof Order.fields>} */
class Order extends Model {
    static _name = "sale.order";
    static _editable = true;
    static fields = {
        name: fields.Char(),
        partner_id: /** @type {Many2one<Partner>} */ (fields.Many2one("res.partner")),
        line_ids: /** @type {One2many<Line>} */ (
            fields.One2many("sale.order.line", { inverse: "order_id" })
        ),
        tag_ids: /** @type {Many2many<Tag>} */ (fields.Many2many("res.partner.tag")),
    };

    get total() {
        return this.line_ids().reduce((sum, line) => sum + line.qty() * line.price(), 0);
    }
}

/** @extends {Model<typeof Line.fields>} */
class Line extends Model {
    static _name = "sale.order.line";
    static _editable = true;
    static fields = {
        order_id: /** @type {Many2one<Order>} */ (fields.Many2one("sale.order")),
        product: fields.Char(),
        qty: fields.Integer({ default: 1 }),
        price: fields.Float(),
    };
}

function makeStore() {
    return new Store({ models: [Partner, Tag, Order, Line] });
}

/**
 * @param {Store} store
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
    test("fields are called to read, set to write, class members work", () => {
        const store = makeStore();
        const partner = store.create("res.partner", { name: "Alice" });
        expect(partner.name()).toBe("Alice");
        partner.name.set("Alice B.");
        expect(partner.name()).toBe("Alice B.");
        expect(partner.label()).toBe("[virtual_1] Alice B.");
        expect(partner).toBeInstanceOf(Partner);
        // fields live on the prototype: the own string keys are the class fields
        expect(Object.keys(partner)).toEqual(["label"]);
        // assigning a field is an error, not a silent shadowing
        expect(() => {
            partner.name = "Bob";
        }).toThrow();
    });

    test("a field signal is stable and can be passed around", () => {
        const store = makeStore();
        const [alice, bob] = store.load("res.partner", [
            { id: 1, name: "Alice" },
            { id: 2, name: "Bob" },
        ]);
        expect(alice.name).toBe(alice.name);
        expect(alice.name).not.toBe(bob.name);
        // e.g. what t-model receives: a function with a `set` method
        const name = alice.name;
        name.set("Alice B.");
        expect(alice.name()).toBe("Alice B.");
        const upper = computed(() => name().toUpperCase());
        expect(upper()).toBe("ALICE B.");
    });

    test("fields can be declared from server definitions", () => {
        // e.g. the fields of a view, or the result of /web/model/get_definitions
        const definitions = {
            name: { type: "char", string: "Name", required: true },
            parent_id: {
                type: "many2one",
                relation: "res.partner",
                inverse_fname_by_model_name: { "res.partner": "child_ids" },
            },
            child_ids: { type: "one2many", relation: "res.partner", relation_field: "parent_id" },
        };
        class ViewPartner extends Model {
            static _name = "res.partner";
            static fields = Object.fromEntries(
                Object.entries(definitions).map(([name, definition]) => [
                    name,
                    fieldFromDefinition(definition),
                ])
            );
        }
        const store = new Store({ models: [ViewPartner] });
        const [parent, child] = store.load("res.partner", [
            { id: 1, name: "Parent", child_ids: [] },
            { id: 2, name: "Child", parent_id: 1 },
        ]);
        expect(parent.child_ids()).toEqual([child]);
        // the store only keeps what it needs to hold records
        expect("required" in store.model("res.partner").fieldsByName.name).toBe(false);
    });

    test("extensions are chained in registration order", () => {
        /** @extends {Model<typeof Thing.fields>} */
        class Thing extends Model {
            static _name = "x.thing";
            static fields = { name: fields.Char() };

            get label() {
                return this.name();
            }
        }
        // two addons extend the same model, without knowing each other
        const thingAFields = { color: fields.Char() };
        class ThingA extends /** @type {Extension<typeof Thing, typeof thingAFields>} */ (Thing) {
            static _inherit = "x.thing";
            static fields = thingAFields;

            get label() {
                return super.label + "+a";
            }
        }
        const thingBFields = { size: fields.Integer() };
        class ThingB extends /** @type {Extension<typeof Thing, typeof thingBFields>} */ (Thing) {
            static _inherit = "x.thing";
            static fields = thingBFields;

            get label() {
                return super.label + "+b";
            }
        }
        const store = new Store({ models: [Thing, ThingA, ThingB] });
        const thing = /** @type {ThingA & ThingB} */ (
            store.create("x.thing", { name: "t", color: "red", size: 3 })
        );
        expect(thing.label).toBe("t+a+b");
        expect(thing).toBeInstanceOf(ThingA);
        expect(thing).toBeInstanceOf(ThingB);
        expect([thing.color(), thing.size()]).toEqual(["red", 3]);
        // any class of the model refers to it
        expect(store.get(Thing, thing.id)).toBe(thing);
        // the base class does not have to be listed
        const store2 = new Store({ models: [ThingB] });
        expect(store2.create("x.thing", { name: "u" }).label).toBe("u+a+b");
    });

    test("an extension does not have to derive from the class it extends", () => {
        class Thing extends Model {
            static _name = "x.thing";
            static fields = { name: fields.Char() };

            get label() {
                return this.name();
            }
        }
        class ThingExtension extends Model {
            static _inherit = "x.thing";
            static fields = { color: fields.Char() };

            get label() {
                return `${super.label} (${this.color()})`;
            }
        }
        const store = new Store({ models: [Thing, ThingExtension] });
        const thing = store.create("x.thing", { name: "t", color: "red" });
        expect(thing).toBeInstanceOf(Thing);
        expect(thing).toBeInstanceOf(ThingExtension);
        expect(thing.label).toBe("t (red)");
    });

    test("the classes of a store are checked", () => {
        class NoModel extends Model {}
        expect(() => new Store({ models: [NoModel] })).toThrow(/has no model/);

        class Partner2 extends Partner {
            static _name = "res.partner2";
        }
        expect(() => new Store({ models: [Partner2] })).toThrow(
            /cannot derive from a class of model "res.partner"/
        );

        class BadField extends Model {
            static _name = "x.bad";
            static fields = { count: 0 };
        }
        expect(() => new Store({ models: [BadField] })).toThrow(
            /"x.bad.count" is not a field declaration/
        );

        class BadReactivity extends Model {
            static _name = "x.bad";
            static _reactivity = "record";
        }
        expect(() => new Store({ models: [BadReactivity] })).toThrow(/Invalid reactivity "record"/);

        class Other extends Model {
            static _name = "res.partner";
        }
        expect(() => new Store({ models: [Partner, Other] })).toThrow(/declared twice/);

        class Extension extends Model {
            static _inherit = "x.thing";
        }
        class Thing extends Model {
            static _name = "x.thing";
        }
        expect(() => new Store({ models: [Extension] })).toThrow(/no class declares it/);
        expect(() => new Store({ models: [Extension, Thing] })).toThrow(
            /extended before it is declared/
        );

        class Orphan extends Model {
            static _name = "x.orphan";
            static fields = { partner_id: fields.Many2one("res.partner") };
        }
        expect(() => new Store({ models: [Orphan] })).toThrow(
            /"x.orphan.partner_id" targets unknown model "res.partner"/
        );
    });

    test("an extension can make a model editable", () => {
        class Thing extends Model {
            static _name = "x.thing";
            static fields = { name: fields.Char() };
        }
        class EditableThing extends Thing {
            static _inherit = "x.thing";
            static _editable = true;
        }
        const plain = new Store({ models: [Thing] });
        const editable = new Store({ models: [Thing, EditableThing] });
        const [a, b] = [plain, editable].map((store) => store.load("x.thing", { id: 1 }));
        a.name.set("a");
        b.name.set("b");
        expect(plain.isDirty(a)).toBe(false);
        expect(editable.isDirty(b)).toBe(true);
    });

    test("a model class refers to its model", () => {
        /** @extends {Model<typeof Country.fields>} */
        class Country extends Model {
            static _name = "res.country";
            static fields = { code: fields.Char() };
        }
        const store = new Store({ models: [Country] });
        const country = store.create(Country, { code: "BE" });
        expect(country.code()).toBe("BE");
        expect(store.get(Country, country.id)).toBe(country);
    });

    test("class fields hold per-record state", () => {
        /** @extends {Model<typeof Counter.fields>} */
        class Counter extends Model {
            static _name = "x.counter";
            static fields = { step: fields.Integer({ default: 2 }) };

            clicks = signal(0);
            total = computed(() => this.clicks() * this.step());
        }
        const store = new Store({ models: [Counter] });
        const [a, b] = [store.create(Counter), store.create(Counter, { step: 5 })];
        a.clicks.set(3);
        expect([a.total(), b.total()]).toEqual([6, 0]);
        b.clicks.set(1);
        a.step.set(10);
        expect([a.total(), b.total()]).toEqual([30, 5]);
    });

    test("a class field cannot hide a field", () => {
        class Bad extends Model {
            static _name = "x.bad";
            static fields = { name: fields.Char() };

            name = signal("");
        }
        const store = new Store({ models: [Bad] });
        expect(() => store.create(Bad)).toThrow(/hidden by a class field/);
    });

    test("records are only built by a store", () => {
        expect(() => new Partner()).toThrow(/built by a store/);
        const store = makeStore();
        const partner = store.create(Partner, { name: "Alice" });
        expect(partner.store).toBe(store);
        const draft = store.draft();
        expect(draft.own(partner).store).toBe(draft);
    });

    test("models are given by class or by name", () => {
        const store = makeStore();
        const partner = store.load(Partner, { id: 1, name: "Alice" });
        expect(store.get(Partner, 1)).toBe(partner);
        expect(store.get("res.partner", 1)).toBe(partner);
        expect(store.records(Partner)).toEqual([partner]);
        expect(store.model(Partner)).toBe(store.model("res.partner"));
    });
});

describe("identity and loading", () => {
    test("loading merges into one object per record", () => {
        const store = makeStore();
        const partner = store.load("res.partner", { id: 1, name: "Alice" });
        expect(store.load("res.partner", { id: 1, tag_ids: [] })).toBe(partner);
        expect(partner.name()).toBe("Alice");
        expect(partner.tag_ids()).toEqual([]);
        expect(store.records("res.partner")).toEqual([partner]);
    });

    test("unknown ids become stubs, filled when loaded", () => {
        const store = makeStore();
        const order = store.load("sale.order", { id: 1, partner_id: 5 });
        const bob = order.partner_id();
        expect(bob).toBe(store.get("res.partner", 5));
        expect(bob.name()).toBe(undefined);
        expect(store.records("res.partner")).toEqual([]);
        store.load("res.partner", { id: 5, name: "Bob" });
        expect(order.partner_id()).toBe(bob);
        expect(bob.name()).toBe("Bob");
        expect(store.records("res.partner")).toEqual([bob]);
    });

    test("web_read values: many2one objects and x2many lists", () => {
        const store = makeStore();
        const order = loadOrder(store);
        expect(order.partner_id().name()).toBe("Bob");
        expect(order.line_ids().map((line) => line.product())).toEqual(["Desk", "Chair"]);
        expect(order.line_ids()[0].order_id()).toBe(order);
        expect(order.total).toBe(300);
        expect(store.isDirty(order)).toBe(false);
        expect(store.isDirty(order.line_ids()[0])).toBe(false);
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
        expect(alice.order_ids()).toEqual([order]);
        order.partner_id.set(bob);
        expect(alice.order_ids()).toEqual([]);
        expect(bob.order_ids()).toEqual([order]);
    });

    test("moving a line to another order through the one2many", () => {
        const store = makeStore();
        const order1 = loadOrder(store);
        const order2 = store.load("sale.order", { id: 2, line_ids: [] });
        const [desk, chair] = order1.line_ids();
        order2.line_ids.set([...order2.line_ids(), desk]);
        expect(desk.order_id()).toBe(order2);
        expect(order1.line_ids()).toEqual([chair]);
    });

    test("many2many inverse", () => {
        const store = makeStore();
        const partner = store.load("res.partner", { id: 1, tag_ids: [] });
        const [vip, stub] = store.load("res.partner.tag", [{ id: 1, partner_ids: [] }, { id: 2 }]);
        partner.tag_ids.set([vip, stub]);
        expect(vip.partner_ids()).toEqual([partner]);
        // a list that is not loaded is left alone
        expect(stub.partner_ids()).toBe(undefined);
        partner.tag_ids.set([stub]);
        expect(vip.partner_ids()).toEqual([]);
    });

    test("one2many lists that are not loaded are left alone", () => {
        const store = makeStore();
        const order = store.load("sale.order", { id: 1, name: "SO1" });
        const line = store.create("sale.order.line", { order_id: order });
        expect(line.order_id()).toBe(order);
        expect(order.line_ids()).toBe(undefined);
    });
});

describe("reactivity", () => {
    test("per field: a computation only depends on the fields it reads", () => {
        const store = makeStore();
        const order = store.load("sale.order", {
            id: 1,
            name: "SO1",
            partner_id: 5,
        });
        let runs = 0;
        const name = computed(() => {
            runs++;
            return order.name();
        });
        expect(name()).toBe("SO1");
        order.partner_id.set(6);
        expect(name()).toBe("SO1");
        expect(runs).toBe(1);
        order.name.set("SO1b");
        expect(name()).toBe("SO1b");
        expect(runs).toBe(2);
    });

    test("per model: one subscription for all records of the model", () => {
        class Product extends Model {
            static _name = "product.product";
            static _reactivity = "model";
            static fields = { name: fields.Char() };
        }
        const store = new Store({ models: [Product] });
        const [desk, chair] = store.load("product.product", [
            { id: 1, name: "Desk" },
            { id: 2, name: "Chair" },
        ]);
        let runs = 0;
        const name = computed(() => {
            runs++;
            return desk.name();
        });
        name();
        chair.name.set("Armchair");
        name();
        expect(runs).toBe(2);
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
        store.get("res.partner", 1).name.set("Alice B.");
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
        order.name.set("SO1b");
        expect(dirty()).toBe(true);
        store.discard(order);
        expect(dirty()).toBe(false);
    });
});

describe("change tracking", () => {
    test("local writes are changes, server loads are not", () => {
        const store = makeStore();
        const order = loadOrder(store);
        order.name.set("SO1b");
        expect(store.isDirty(order)).toBe(true);
        // a server value under a local change: the change keeps showing
        store.load("sale.order", { id: 1, name: "SO1 (server)" });
        expect(order.name()).toBe("SO1b");
        store.discard(order);
        expect(order.name()).toBe("SO1 (server)");
        expect(store.isDirty(order)).toBe(false);
    });

    test("models that are not editable write directly", () => {
        const store = makeStore();
        const partner = store.load("res.partner", { id: 1, name: "Alice" });
        partner.name.set("Alice B.");
        expect(partner.name()).toBe("Alice B.");
        expect(store.isDirty(partner)).toBe(false);
    });

    test("discard restores the record and its lines", () => {
        const store = makeStore();
        const order = loadOrder(store);
        const [desk, chair] = order.line_ids();
        desk.qty.set(10);
        store.delete(chair);
        const lamp = store.create("sale.order.line", {
            order_id: order,
            product: "Lamp",
        });
        expect(order.line_ids()).toEqual([desk, lamp]);

        store.discard(order);
        expect(order.line_ids()).toEqual([desk, chair]);
        expect(desk.qty()).toBe(1);
        expect(store.get("sale.order.line", 12)).toBe(chair);
        expect(store.get("sale.order.line", lamp.id)).toBe(null);
        expect(store.isDirty(order)).toBe(false);
    });

    test("deletions stay pending until acknowledged", () => {
        const store = makeStore();
        const order = loadOrder(store);
        const chair = order.line_ids()[1];
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
        const [desk, chair] = order.line_ids();
        desk.qty.set(3);
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
        const untouched = store.load("sale.order", {
            id: 2,
            name: "SO2",
            line_ids: [],
        });
        expect(toCommands(untouched).vals).toEqual({});
    });

    test("many2many as LINK and UNLINK", () => {
        const store = makeStore();
        const order = store.load("sale.order", { id: 1, tag_ids: [1, 2] });
        order.tag_ids.set([store.get("res.partner.tag", 2), store.get("res.partner.tag", 3, true)]);
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
        const desk = order.line_ids()[0];
        order.name.set("A");
        const { version } = toCommands(order);
        // edits while the save is in flight
        order.name.set("B");
        desk.qty.set(2);
        store.ack(order, version);
        expect(store.isDirty(order)).toBe(true);
        expect(toCommands(order).vals).toEqual({
            name: "B",
            line_ids: [[1, 11, { qty: 2 }]],
        });
    });

    test("saving a new record: ack, then swap virtual ids for server ids", () => {
        const store = makeStore();
        const order = store.create("sale.order", { name: "SO" });
        const line = store.create("sale.order.line", {
            order_id: order,
            product: "Desk",
        });
        const { version } = toCommands(order);
        // server answered: order 42 with line 101
        store.ack(order, version);
        store.rekey(order, 42);
        store.rekey(line, 101);
        store.load("sale.order", { id: 42, name: "SO/0042" });
        expect(store.get("sale.order", 42)).toBe(order);
        expect(store.isNew(order)).toBe(false);
        expect(line.order_id()).toBe(order);
        expect(order.name()).toBe("SO/0042");
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
        expect(draftOrder.name()).toBe("SO1");
        draftOrder.name.set("Draft");
        expect(order.name()).toBe("SO1");
        expect(draft.isDirty()).toBe(true);
        expect(store.isDirty(order)).toBe(false);
        // changes in the parent show through fields the draft did not touch
        order.partner_id.set(6);
        expect(draftOrder.partner_id().id).toBe(6);

        draft.commit();
        expect(order.name()).toBe("Draft");
        expect(store.isDirty(order)).toBe(true);
        expect(draft.isDirty()).toBe(false);
        expect(draftOrder.name()).toBe("Draft");
    });

    test("the copy of a record in a draft has its own class fields", () => {
        const store = makeStore();
        const partner = store.load(Partner, { id: 1, name: "Alice" });
        const draft = store.draft();
        const draftPartner = draft.own(partner);
        expect(draftPartner).toBeInstanceOf(Partner);
        draftPartner.name.set("Bob");
        expect(draftPartner.label()).toBe("[1] Bob");
        expect(partner.label()).toBe("[1] Alice");
        draft.commit();
        expect(partner.label()).toBe("[1] Bob");
    });

    test("relations inside a draft are draft records", () => {
        const store = makeStore();
        const order = loadOrder(store);
        const draft = store.draft();
        const draftOrder = draft.get("sale.order", 1);
        const draftDesk = draftOrder.line_ids()[0];
        expect(draftDesk).not.toBe(order.line_ids()[0]);
        expect(draftDesk.order_id()).toBe(draftOrder);

        draft.create("sale.order.line", { order_id: draftOrder, product: "Lamp" });
        expect(draftOrder.line_ids().map((l) => l.product())).toEqual(["Desk", "Chair", "Lamp"]);
        expect(order.line_ids().length).toBe(2);

        draft.discard();
        expect(draftOrder.line_ids().map((l) => l.product())).toEqual(["Desk", "Chair"]);
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
        const lamp = order.line_ids()[2];
        expect(lamp.product()).toBe("Lamp");
        expect(lamp.order_id()).toBe(order);
        expect(store.isNew(lamp)).toBe(true);
        // the draft's object now reads through to the parent record
        expect(draftLamp.price()).toBe(20);
        expect(toCommands(order).vals).toEqual({
            line_ids: [[0, lamp.id, { product: "Lamp", qty: 1, price: 20 }]],
        });
    });

    test("nested drafts, like a dialog opened from a dialog", () => {
        const store = makeStore();
        const order = loadOrder(store);
        const level1 = store.draft();
        level1.own(order).name.set("level 1");
        const level2 = level1.draft();
        const order2 = level2.own(order);
        expect(order2.name()).toBe("level 1");

        order2.name.set("level 2");
        level2.discard();
        expect(level1.own(order).name()).toBe("level 1");

        order2.name.set("level 2");
        level2.commit();
        expect(level1.own(order).name()).toBe("level 2");
        expect(order.name()).toBe("SO1");
        level1.commit();
        expect(order.name()).toBe("level 2");
    });

    test("computations on a draft record see draft and parent changes", () => {
        const store = makeStore();
        const order = loadOrder(store);
        const draftOrder = store.draft().own(order);
        const name = computed(() => draftOrder.name());
        expect(name()).toBe("SO1");
        order.name.set("from parent");
        expect(name()).toBe("from parent");
        draftOrder.name.set("from draft");
        expect(name()).toBe("from draft");
        expect(order.name()).toBe("from parent");
    });
});

describe("indexes", () => {
    test("an extension adds its indexes to the ones of the model", () => {
        class Product extends Model {
            static _name = "product.product";
            static _indexes = ["barcode"];
            static fields = { barcode: fields.Char() };
        }
        class StockProduct extends Model {
            static _inherit = "product.product";
            static _indexes = ["lot"];
            static fields = { lot: fields.Char() };
        }
        const store = new Store({ models: [Product, StockProduct] });
        const desk = store.load(Product, { id: 1, barcode: "111", lot: "A" });
        expect(store.getBy(Product, "barcode", "111")).toBe(desk);
        expect(store.getBy(Product, "lot", "A")).toBe(desk);
    });

    test("unique indexes follow writes and deletions", () => {
        class Product extends Model {
            static _name = "product.product";
            static _indexes = ["barcode"];
            static fields = { name: fields.Char(), barcode: fields.Char() };
        }
        const store = new Store({ models: [Product] });
        store.load("product.product", [{ id: 1, name: "Desk", barcode: "111" }]);
        const desk = store.getBy("product.product", "barcode", "111");
        expect(desk.name()).toBe("Desk");
        desk.barcode.set("222");
        expect(store.getBy("product.product", "barcode", "111")).toBe(null);
        expect(store.getBy("product.product", "barcode", "222")).toBe(desk);
        store.delete(desk);
        expect(store.getBy("product.product", "barcode", "222")).toBe(null);
    });
});

describe("components", () => {
    test("records are built in the scope the store was created in", async () => {
        class Thing extends Model {
            static _name = "x.thing";
            static fields = { name: fields.Char() };

            // a hook, as `usePlugin` would be
            scope = useScope();
        }
        let store, scope;
        class Parent extends Component {
            static template = xml`<div/>`;
            setup() {
                scope = useScope();
                store = new Store({ models: [Thing] });
            }
        }
        await mountWithCleanup(Parent);
        // built later, outside of any setup
        const thing = store.create(Thing, { name: "a" });
        expect(thing.scope).toBe(scope);
        expect(store.draft().own(thing).scope).toBe(scope);
    });

    test("a component re-renders when a field it read changes, not for other fields", async () => {
        const store = makeStore();
        const partner = store.load("res.partner", {
            id: 1,
            name: "Alice",
            tag_ids: [],
        });
        class PartnerCard extends Component {
            static template = xml`<div class="name" t-out="this.partner.name()"/>`;
            partner = partner;
            setup() {
                onPatched(() => expect.step("patched"));
            }
        }
        await mountWithCleanup(PartnerCard);
        expect(".name").toHaveText("Alice");

        partner.name.set("Bob");
        await animationFrame();
        expect(".name").toHaveText("Bob");
        expect.verifySteps(["patched"]);

        partner.tag_ids.set([1]);
        await animationFrame();
        expect.verifySteps([]);
    });

    test("useEffect re-runs when a field it read changes", async () => {
        const store = makeStore();
        const partner = store.load("res.partner", {
            id: 1,
            name: "Alice",
            tag_ids: [],
        });
        class Watcher extends Component {
            static template = xml`<div/>`;
            setup() {
                useEffect(() => expect.step(`name: ${partner.name()}`));
            }
        }
        await mountWithCleanup(Watcher);
        expect.verifySteps(["name: Alice"]);

        partner.name.set("Bob");
        await animationFrame();
        expect.verifySteps(["name: Bob"]);

        partner.tag_ids.set([1]);
        await animationFrame();
        expect.verifySteps([]);
    });

    test("t-model binds an input to a field", async () => {
        const store = makeStore();
        const partner = store.load("res.partner", { id: 1, name: "Alice" });
        class PartnerEditor extends Component {
            static template = xml`<input t-model="this.partner.name"/>`;
            partner = partner;
        }
        await mountWithCleanup(PartnerEditor);
        expect("input").toHaveValue("Alice");

        await contains("input").edit("Bob");
        expect(partner.name()).toBe("Bob");

        partner.name.set("Carol");
        await animationFrame();
        expect("input").toHaveValue("Carol");
    });

    test("a component on a draft record sees draft changes only", async () => {
        const store = makeStore();
        const order = loadOrder(store);
        const draft = store.draft();
        const draftOrder = draft.own(order);
        class OrderTitle extends Component {
            static template = xml`<div class="title" t-out="this.order.name()"/>`;
            order = draftOrder;
        }
        await mountWithCleanup(OrderTitle);
        expect(".title").toHaveText("SO1");

        draftOrder.name.set("Draft title");
        await animationFrame();
        expect(".title").toHaveText("Draft title");
        expect(order.name()).toBe("SO1");

        draft.discard();
        await animationFrame();
        expect(".title").toHaveText("SO1");
    });
});

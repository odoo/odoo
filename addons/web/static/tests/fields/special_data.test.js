// @ts-check

import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, EventBus, reactive, useState, xml } from "@odoo/owl";
import {
    defineModels,
    fields,
    models,
    mountWithCleanup,
    onRpc,
} from "@web/../tests/web_test_helpers";
import { useSpecialData } from "@web/fields/relational/special_data";

class Sub extends models.Model {
    _name = "sub";
    name = fields.Char();
    _records = [{ id: 1, name: "s1" }];
}

defineModels([Sub]);

/**
 * @param {number} id
 * @param {Record<string, any>} data
 */
function makeRecord(id, data) {
    return reactive({
        id,
        data,
        model: { specialDataCaches: new Map(), bus: new EventBus() },
    });
}

/** @returns {Promise<{ state: any, counts: { loadFn: number, rpc: number } }>} */
async function mountSpecialData() {
    const counts = { loadFn: 0, rpc: 0 };
    onRpc("sub", "name_search", () => {
        counts.rpc++;
        return [[1, "s1"]];
    });

    /** @type {any} */
    let state;

    class Child extends Component {
        static template = xml`<span class="child"/>`;
        static props = ["record", "domain"];
        setup() {
            useSpecialData((/** @type {any} */ orm, /** @type {any} */ props) => {
                counts.loadFn++;
                return orm.call("sub", "name_search", ["", props.domain], {});
            });
        }
    }

    class Parent extends Component {
        static template = xml`<span t-out="this.state.tick"/><Child record="this.state.record" domain="this.state.domain"/>`;
        static components = { Child };
        /** @type {any} */
        static props = [];
        setup() {
            this.state = useState({
                record: makeRecord(1, { foo: 1 }),
                tick: 0,
                domain: "a",
            });
            state = this.state;
        }
    }

    await mountWithCleanup(Parent);
    await animationFrame();
    return { state, counts };
}

test("loads once on mount", async () => {
    const { counts } = await mountSpecialData();
    expect(counts.loadFn).toBe(1);
    expect(counts.rpc).toBe(1);
});

test("a parent re-render that changes no child prop does not reload", async () => {
    const { state, counts } = await mountSpecialData();
    for (let i = 1; i <= 3; i++) {
        state.tick = i;
        await animationFrame();
    }
    expect(counts.loadFn).toBe(1);
    expect(counts.rpc).toBe(1);
});

test("a props update that changes a loadFn input does reload", async () => {
    const { state, counts } = await mountSpecialData();
    state.domain = "b";
    await animationFrame();
    expect(counts.loadFn).toBe(2);
    expect(counts.rpc).toBe(2);
});

test("a new record still reloads", async () => {
    const { state, counts } = await mountSpecialData();
    state.record = makeRecord(2, { foo: 2 });
    await animationFrame();
    expect(counts.loadFn).toBe(2);
});

test("a reloaded record -- new object, same id -- reloads once, not twice", async () => {
    const { state, counts } = await mountSpecialData();
    state.record = makeRecord(1, { foo: 2 });
    await animationFrame();
    expect(counts.loadFn).toBe(2);
});

test("the shape Field actually mounts: t-props with a fresh context each render", async () => {
    const counts = { loadFn: 0 };
    onRpc("sub", "name_search", () => [[1, "s1"]]);

    /** @type {any} */
    let state;

    class Child extends Component {
        static template = xml`<span class="child"/>`;
        static props = ["*"];
        setup() {
            useSpecialData((/** @type {any} */ orm) => {
                counts.loadFn++;
                return orm.call("sub", "name_search", ["", []], {});
            });
        }
    }

    class Parent extends Component {
        static template = xml`<span t-out="this.state.tick"/><Child t-props="this.childProps"/>`;
        static components = { Child };
        /** @type {any} */
        static props = [];
        /** @type {any} */
        state;
        setup() {
            this.state = useState({ record: makeRecord(1, { foo: 1 }), tick: 0 });
            state = this.state;
        }
        get childProps() {
            return {
                record: this.state.record,
                context: {},
                domain: () => /** @type {any[]} */ ([]),
            };
        }
    }

    await mountWithCleanup(Parent);
    await animationFrame();
    expect(counts.loadFn).toBe(1);

    for (let i = 1; i <= 3; i++) {
        state.tick = i;
        await animationFrame();
    }
    expect(counts.loadFn).toBe(4);
});

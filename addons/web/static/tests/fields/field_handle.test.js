// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, useState, xml } from "@odoo/owl";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { SignalStore } from "@web/core/utils/reactive";
import { fieldHandle, fieldHandleFor } from "@web/fields/field_handle";

describe.current.tags("headless");

class FakeRecord extends SignalStore {
    constructor(data = { foo: "a", bar: "b" }) {
        super();
        this.data = data;
        this.fields = { foo: { type: "char", string: "Foo" }, bar: { type: "char" } };
        /** @type {any[][]} */
        this.written = [];
    }
    /**
     * @param {any} changes
     * @param {any} [options]
     */
    update(changes, options) {
        this.written.push([changes, options]);
        Object.assign(this.data, changes);
    }
}

class Widget extends Component {
    static template = xml`<span t-out="this.handle.value"/>`;
    static props = ["record", "name", "readonly?"];
    get handle() {
        return fieldHandle(this);
    }
}

async function mountWidget(/** @type {any} */ record, name = "foo") {
    class Parent extends Component {
        static template = xml`<Widget record="this.state.record" name="this.state.name"/>`;
        static components = { Widget };
        static props = {};
        setup() {
            this.state = useState({ record, name });
        }
    }
    return mountWithCleanup(Parent);
}

test("value reads the widget's own field", async () => {
    await mountWidget(new FakeRecord());
    expect("span").toHaveText("a");
});

test("a write to the field re-renders the widget", async () => {
    const record = new FakeRecord();
    await mountWidget(record);
    record.update({ foo: "z" });
    await animationFrame();
    expect("span").toHaveText("z");
});

test("a write to a SIBLING field does not re-render the widget", async () => {
    const record = new FakeRecord();
    await mountWidget(record);
    record.update({ bar: "changed" });
    await animationFrame();
    expect("span").toHaveText("a", {
        message: "the handle subscribes to one field, which is the point of it",
    });
});

test("update writes the widget's own field", async () => {
    const record = new FakeRecord();
    const parent = await mountWidget(record);
    /** @type {any} */ (parent).__owl__.children;
    record.data.foo = "a";
    const widget = Object.values(/** @type {any} */ (parent).__owl__.children)[0];
    /** @type {any} */ (widget).component.handle.update("written", { save: true });
    expect(record.written.at(-1)).toEqual([{ foo: "written" }, { save: true }]);
});

test("field and type come from the record's field definitions", async () => {
    const record = new FakeRecord();
    const parent = await mountWidget(record);
    const widget = Object.values(/** @type {any} */ (parent).__owl__.children)[0];
    const handle = /** @type {any} */ (widget).component.handle;
    expect(handle.definition.string).toBe("Foo");
    expect(handle.type).toBe("char");
    expect(handle.name).toBe("foo");
});

test("the handle follows a swapped record prop", async () => {
    const first = new FakeRecord();
    const second = new FakeRecord({ foo: "second", bar: "b" });
    const parent = await mountWidget(first);
    expect("span").toHaveText("a");

    /** @type {any} */ (parent).state.record = second;
    await animationFrame();
    expect("span").toHaveText("second", {
        message: "reads must be lazy — an x2many row reuses a component instance",
    });

    second.update({ foo: "changed" });
    await animationFrame();
    expect("span").toHaveText("changed", {
        message: "and must subscribe to the NEW record, not the one seen at setup",
    });
});

test("the handle follows a swapped name prop", async () => {
    const record = new FakeRecord();
    const parent = await mountWidget(record);
    expect("span").toHaveText("a");
    /** @type {any} */ (parent).state.name = "bar";
    await animationFrame();
    expect("span").toHaveText("b");
});

test("a parent-built handle does NOT subscribe the child", async () => {
    const record = new FakeRecord();
    class Leaf extends Component {
        static template = xml`<span t-out="this.props.handle.value"/>`;
        static props = ["handle"];
    }
    class Parent extends Component {
        static template = xml`<Leaf handle="this.handle"/>`;
        static components = { Leaf };
        static props = {};
        setup() {
            const rec = record;
            this.handle = {
                get value() {
                    return rec.data.foo;
                },
            };
        }
    }
    await mountWithCleanup(Parent);
    expect("span").toHaveText("a");
    record.update({ foo: "z" });
    await animationFrame();
    expect("span").toHaveText("a", {
        message:
            "if this ever passes, a `field` prop became possible — re-read field_handle.js",
    });
});

test("wrapping the record in useState in the PARENT does not fix it", async () => {
    const record = new FakeRecord();
    class Leaf extends Component {
        static template = xml`<span t-out="this.props.handle.value"/>`;
        static props = ["handle"];
    }
    class Parent extends Component {
        static template = xml`<Leaf handle="this.handle"/>`;
        static components = { Leaf };
        static props = {};
        setup() {
            const rec = useState(record);
            this.handle = {
                get value() {
                    return rec.data.foo;
                },
            };
        }
    }
    await mountWithCleanup(Parent);
    expect("span").toHaveText("a");
    record.update({ foo: "z" });
    await animationFrame();
    expect("span").toHaveText("a", {
        message: "it subscribes the parent, whose child props are unchanged",
    });
});

test("the handle survives a subclass that overrides setup without super", async () => {
    const record = new FakeRecord();

    class Base extends Component {
        static template = xml`<span t-out="this.field.value"/>`;
        static props = ["record", "name"];
        setup() {
            this.fromBase = true;
        }
        get field() {
            return fieldHandle(this);
        }
    }
    class Derived extends Base {
        setup() {}
    }
    class Parent extends Component {
        static template = xml`<Derived record="this.record" name="'foo'"/>`;
        static components = { Derived };
        static props = {};
        setup() {
            this.record = record;
        }
    }

    await mountWithCleanup(Parent);
    expect("span").toHaveText("a");
    record.update({ foo: "z" });
    await animationFrame();
    expect("span").toHaveText("z");
});

test("the handle exposes no readonly, on either constructor", () => {
    const record = new FakeRecord();
    const handle = fieldHandleFor(record, "foo");

    expect("readonly" in handle).toBe(false, {
        message: "a handle member restating props.readonly has no reader",
    });
    expect(Object.keys(handle).sort()).toEqual([
        "definition",
        "name",
        "type",
        "update",
        "value",
    ]);
    expect(fieldHandleFor(record, "foo")).toBe(handle);
    expect(fieldHandleFor(record, "bar")).not.toBe(handle);
});

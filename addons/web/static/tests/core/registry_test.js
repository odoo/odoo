/** @odoo-module **/

import { Registry } from "@web/core/registry";

QUnit.module("Registry");

QUnit.test("key set and get", function (assert) {
    const registry = new Registry();
    const foo = {};

    registry.add("foo", foo);

    assert.strictEqual(registry.get("foo"), foo);
});

QUnit.test("can set and get falsy values", function (assert) {
    const registry = new Registry();
    registry.add("foo1", false);
    registry.add("foo2", 0);
    registry.add("foo3", "");
    registry.add("foo4", undefined);
    registry.add("foo5", null);
    assert.strictEqual(registry.get("foo1"), false);
    assert.strictEqual(registry.get("foo2"), 0);
    assert.strictEqual(registry.get("foo3"), "");
    assert.strictEqual(registry.get("foo4"), undefined);
    assert.strictEqual(registry.get("foo5"), null);
});

QUnit.test("can set and get falsy values with default value", function (assert) {
    const registry = new Registry();
    registry.add("foo1", false);
    registry.add("foo2", 0);
    registry.add("foo3", "");
    registry.add("foo4", undefined);
    registry.add("foo5", null);
    assert.strictEqual(registry.get("foo1", 1), false);
    assert.strictEqual(registry.get("foo2", 1), 0);
    assert.strictEqual(registry.get("foo3", 1), "");
    assert.strictEqual(registry.get("foo4", 1), undefined);
    assert.strictEqual(registry.get("foo5", 1), null);
});

QUnit.test("can get a default value when missing key", function (assert) {
    const registry = new Registry();
    assert.strictEqual(registry.get("missing", "default"), "default");
    assert.strictEqual(registry.get("missing", null), null);
    assert.strictEqual(registry.get("missing", false), false);
});

QUnit.test("throws if key is missing", function (assert) {
    const registry = new Registry();
    assert.throws(() => registry.get("missing"));
});

QUnit.test("contains method", function (assert) {
    const registry = new Registry();

    registry.add("foo", 1);

    assert.ok(registry.contains("foo"));
    assert.notOk(registry.contains("bar"));
});

QUnit.test("can set and get a value, with an order arg", function (assert) {
    const registry = new Registry();
    const foo = {};

    registry.add("foo", foo, { sequence: 24 });

    assert.strictEqual(registry.get("foo"), foo);
});

QUnit.test("can get ordered list of elements", function (assert) {
    const registry = new Registry();

    registry
        .add("foo1", "foo1", { sequence: 1 })
        .add("foo2", "foo2", { sequence: 2 })
        .add("foo5", "foo5", { sequence: 5 })
        .add("foo3", "foo3", { sequence: 3 });

    assert.deepEqual(registry.getAll(), ["foo1", "foo2", "foo3", "foo5"]);
});

QUnit.test("can get ordered list of entries", function (assert) {
    const registry = new Registry();

    registry
        .add("foo1", "foo1", { sequence: 1 })
        .add("foo2", "foo2", { sequence: 2 })
        .add("foo5", "foo5", { sequence: 5 })
        .add("foo3", "foo3", { sequence: 3 });

    assert.deepEqual(registry.getEntries(), [
        ["foo1", "foo1"],
        ["foo2", "foo2"],
        ["foo3", "foo3"],
        ["foo5", "foo5"],
    ]);
});

QUnit.test("getAll and getEntries returns shallow copies", function (assert) {
    const registry = new Registry();

    registry.add("foo1", "foo1");

    const all = registry.getAll();
    const entries = registry.getEntries();

    assert.deepEqual(all, ["foo1"]);
    assert.deepEqual(entries, [["foo1", "foo1"]]);

    all.push("foo2");
    entries.push(["foo2", "foo2"]);

    assert.deepEqual(all, ["foo1", "foo2"]);
    assert.deepEqual(entries, [
        ["foo1", "foo1"],
        ["foo2", "foo2"],
    ]);
    assert.deepEqual(registry.getAll(), ["foo1"]);
    assert.deepEqual(registry.getEntries(), [["foo1", "foo1"]]);
});

QUnit.test("can override element with sequence", function (assert) {
    const registry = new Registry();

    registry
        .add("foo1", "foo1", { sequence: 1 })
        .add("foo2", "foo2", { sequence: 2 })
        .add("foo1", "foo3", { force: true });

    assert.deepEqual(registry.getEntries(), [
        ["foo1", "foo3"],
        ["foo2", "foo2"],
    ]);
});

QUnit.test("can override element with sequence 2 ", function (assert) {
    const registry = new Registry();

    registry
        .add("foo1", "foo1", { sequence: 1 })
        .add("foo2", "foo2", { sequence: 2 })
        .add("foo1", "foo3", { force: true, sequence: 3 });

    assert.deepEqual(registry.getEntries(), [
        ["foo2", "foo2"],
        ["foo1", "foo3"],
    ]);
});

QUnit.test("can recursively open sub registry", function (assert) {
    const registry = new Registry();

    registry.category("sub").add("a", "b");
    assert.deepEqual(registry.category("sub").get("a"), "b");
});

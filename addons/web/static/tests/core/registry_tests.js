odoo.define('web.registry_tests', function (require) {
"use strict";

var Registry = require('web.Registry');

QUnit.module('core', {}, function () {

    QUnit.module('Registry');

    QUnit.test('key set', function (assert) {
        assert.expect(1);

        var registry = new Registry();
        var foo = {};

        registry
            .add('foo', foo);

        assert.strictEqual(registry.get('foo'), foo);
    });

    QUnit.test('get initial keys', function (assert) {
        assert.expect(1);

        var registry = new Registry({ a: 1, });
        assert.deepEqual(
            registry.keys(),
            ['a'],
            "keys on prototype should be returned"
        );
    });

    QUnit.test('get initial entries', function (assert) {
        assert.expect(1);

        var registry = new Registry({ a: 1, });
        assert.deepEqual(
            registry.entries(),
            { a: 1, },
            "entries on prototype should be returned"
        );
    });

    QUnit.test('multiget', function (assert) {
        assert.expect(1);

        var foo = {};
        var bar = {};
        var registry = new Registry({
            foo: foo,
            bar: bar,
        });
        assert.strictEqual(
            registry.getAny(['qux', 'grault', 'bar', 'foo']),
            bar,
            "Registry getAny should find first defined key");
    });

    QUnit.test('keys and values are properly ordered', function (assert) {
        assert.expect(2);

        var registry = new Registry();

        registry
            .add('fred', 'foo', 3)
            .add('george', 'bar', 2)
            .add('ronald', 'qux', 4);

        assert.deepEqual(registry.keys(), ['george', 'fred', 'ronald']);
        assert.deepEqual(registry.values(), ['bar', 'foo', 'qux']);
    });

    QUnit.test("predicate prevents invalid values", function (assert) {
        assert.expect(5);

        const predicate = value => typeof value === "number";
        const registry = new Registry(null, predicate);
        registry.onAdd((key) => assert.step(key));

        assert.ok(registry.add("age", 23));
        assert.throws(
            () => registry.add("name", "Fred"),
            new Error(`Value of key "name" does not pass the addition predicate.`)
        );
        assert.deepEqual(registry.entries(), { age: 23 });
        assert.verifySteps(["age"]);
    });
});

});

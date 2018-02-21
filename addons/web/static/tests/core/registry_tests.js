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

    QUnit.test('extension', function (assert) {
        assert.expect(2);

        var foo = {};
        var foo2 = {};
        var registry = new Registry({
            foo: foo,
        });
        var registry2 = registry.extend({foo: foo2});
        assert.strictEqual(registry.get('foo'), foo);
        assert.strictEqual(registry2.get('foo'), foo2);
    });

    QUnit.test('remain-linked', function (assert) {
        assert.expect(2);

        var foo = {};
        var foo2 = {};
        var registry = new Registry({
            foo: foo,
        });

        var registry2 = registry.extend();

        registry.add('foo2', foo2);

        assert.strictEqual(registry.get('foo2'), foo2);
        assert.strictEqual(registry2.get('foo2'), foo2);
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

    QUnit.test('extended-multiget', function (assert) {
        assert.expect(1);

        var foo = {};
        var bar = {};
        var registry = new Registry({
            foo: foo,
            bar: bar,
        });
        var registry2 = registry.extend();
        assert.strictEqual(registry2.getAny(['qux', 'grault', 'bar', 'foo']), bar);
    });

});

});


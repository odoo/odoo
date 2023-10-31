odoo.define('web.class_tests', function (require) {
"use strict";

var Class = require('web.Class');

QUnit.module('core', {}, function () {

    QUnit.module('Class');


    QUnit.test('Basic class creation', function (assert) {
        assert.expect(2);

        var C = Class.extend({
            foo: function () {
                return this.somevar;
            }
        });
        var i = new C();
        i.somevar = 3;

        assert.ok(i instanceof C);
        assert.strictEqual(i.foo(), 3);
    });

    QUnit.test('Class initialization', function (assert) {
        assert.expect(2);

        var C1 = Class.extend({
            init: function () {
                this.foo = 3;
            }
        });
        var C2 = Class.extend({
            init: function (arg) {
                this.foo = arg;
            }
        });

        var i1 = new C1(),
            i2 = new C2(42);

        assert.strictEqual(i1.foo, 3);
        assert.strictEqual(i2.foo, 42);
    });

    QUnit.test('Inheritance', function (assert) {
        assert.expect(3);

        var C0 = Class.extend({
            foo: function () {
                return 1;
            }
        });
        var C1 = C0.extend({
            foo: function () {
                return 1 + this._super();
            }
        });
        var C2 = C1.extend({
            foo: function () {
                return 1 + this._super();
            }
        });

        assert.strictEqual(new C0().foo(), 1);
        assert.strictEqual(new C1().foo(), 2);
        assert.strictEqual(new C2().foo(), 3);
    });

    QUnit.test('In-place extension', function (assert) {
        assert.expect(4);

        var C0 = Class.extend({
            foo: function () {
                return 3;
            },
            qux: function () {
                return 3;
            },
            bar: 3
        });

        C0.include({
            foo: function () {
                return 5;
            },
            qux: function () {
                return 2 + this._super();
            },
            bar: 5,
            baz: 5
        });

        assert.strictEqual(new C0().bar, 5);
        assert.strictEqual(new C0().baz, 5);
        assert.strictEqual(new C0().foo(), 5);
        assert.strictEqual(new C0().qux(), 5);
    });

    QUnit.test('In-place extension and inheritance', function (assert) {
        assert.expect(4);

        var C0 = Class.extend({
            foo: function () { return 1; },
            bar: function () { return 1; }
        });
        var C1 = C0.extend({
            foo: function () { return 1 + this._super(); }
        });
        assert.strictEqual(new C1().foo(), 2);
        assert.strictEqual(new C1().bar(), 1);

        C1.include({
            foo: function () { return 2 + this._super(); },
            bar: function () { return 1 + this._super(); }
        });
        assert.strictEqual(new C1().foo(), 4);
        assert.strictEqual(new C1().bar(), 2);
    });

    QUnit.test('In-place extensions alter existing instances', function (assert) {
        assert.expect(4);

        var C0 = Class.extend({
            foo: function () { return 1; },
            bar: function () { return 1; }
        });
        var i = new C0();
        assert.strictEqual(i.foo(), 1);
        assert.strictEqual(i.bar(), 1);

        C0.include({
            foo: function () { return 2; },
            bar: function () { return 2 + this._super(); }
        });
        assert.strictEqual(i.foo(), 2);
        assert.strictEqual(i.bar(), 3);
    });

    QUnit.test('In-place extension of subclassed types', function (assert) {
        assert.expect(3);

        var C0 = Class.extend({
            foo: function () { return 1; },
            bar: function () { return 1; }
        });
        var C1 = C0.extend({
            foo: function () { return 1 + this._super(); },
            bar: function () { return 1 + this._super(); }
        });
        var i = new C1();

        assert.strictEqual(i.foo(), 2);

        C0.include({
            foo: function () { return 2; },
            bar: function () { return 2 + this._super(); }
        });

        assert.strictEqual(i.foo(), 3);
        assert.strictEqual(i.bar(), 4);
    });


});

});

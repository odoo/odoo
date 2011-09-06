$(document).ready(function () {
    var openerp;
    module('web-class', {
        setup: function () {
            openerp = window.openerp.init();
            window.openerp.web.core(openerp);
        }
    });
    test('Basic class creation', function () {
        var C = openerp.web.Class.extend({
            foo: function () {
                return this.somevar;
            }
        });
        var instance = new C();
        instance.somevar = 3;

        ok(instance instanceof C);
        strictEqual(instance.foo(), 3);
    });
    test('Class initialization', function () {
        var C1 = openerp.web.Class.extend({
            init: function () {
                this.foo = 3;
            }
        });
        var C2 = openerp.web.Class.extend({
            init: function (arg) {
                this.foo = arg;
            }
        });

        var i1 = new C1(),
            i2 = new C2(42);

        strictEqual(i1.foo, 3);
        strictEqual(i2.foo, 42);
    });
    test('Inheritance', function () {
        var C0 = openerp.web.Class.extend({
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

        strictEqual(new C0().foo(), 1);
        strictEqual(new C1().foo(), 2);
        strictEqual(new C2().foo(), 3);
    });
    test('In-place extension', function () {
        var C0 = openerp.web.Class.extend({
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

        strictEqual(new C0().bar, 5);
        strictEqual(new C0().baz, 5);
        strictEqual(new C0().foo(), 5);
        strictEqual(new C0().qux(), 5);
    });
    test('In-place extension and inheritance', function () {
        var C0 = openerp.web.Class.extend({
            foo: function () { return 1; },
            bar: function () { return 1; }
        });
        var C1 = C0.extend({
            foo: function () { return 1 + this._super(); }
        });
        strictEqual(new C1().foo(), 2);
        strictEqual(new C1().bar(), 1);

        C1.include({
            foo: function () { return 2 + this._super(); },
            bar: function () { return 1 + this._super(); }
        });
        strictEqual(new C1().foo(), 4);
        strictEqual(new C1().bar(), 2);
    });
    test('In-place extensions alter existing instances', function () {
        var C0 = openerp.web.Class.extend({
            foo: function () { return 1; },
            bar: function () { return 1; }
        });
        var instance = new C0();
        strictEqual(instance.foo(), 1);
        strictEqual(instance.bar(), 1);

        C0.include({
            foo: function () { return 2; },
            bar: function () { return 2 + this._super(); }
        });
        strictEqual(instance.foo(), 2);
        strictEqual(instance.bar(), 3);
    });
    test('In-place extension of subclassed types', function () {
        var C0 = openerp.web.Class.extend({
            foo: function () { return 1; },
            bar: function () { return 1; }
        });
        var C1 = C0.extend({
            foo: function () { return 1 + this._super(); },
            bar: function () { return 1 + this._super(); }
        });
        var instance = new C1();
        strictEqual(instance.foo(), 2);
        C0.include({
            foo: function () { return 2; },
            bar: function () { return 2 + this._super(); }
        });
        strictEqual(instance.foo(), 3);
        strictEqual(instance.bar(), 4);
    });
});

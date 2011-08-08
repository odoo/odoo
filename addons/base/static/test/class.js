$(document).ready(function () {
    var openerp;
    module('Base Class', {
        setup: function () {
            openerp = window.openerp.init();
            window.openerp.base.core(openerp);
        }
    });
    test('Basic class creation', function () {
        var C = openerp.base.Class.extend({
            foo: function () {
                return this.somevar;
            }
        });
        var i1 = new C();
        i1.somevar = 3;

        ok(i1 instanceof C);
        strictEqual(i1.foo(), 3);
    });
    test('Class initialization', function () {
        var C1 = openerp.base.Class.extend({
            init: function () {
                this.foo = 3;
            }
        });
        var C2 = openerp.base.Class.extend({
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
        var C0 = openerp.base.Class.extend({
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
});

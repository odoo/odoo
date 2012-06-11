$(document).ready(function () {
    var $fix = $('#qunit-fixture');
    var mod = {
        setup: function () {
            instance = window.openerp.init([]);
            window.openerp.web.corelib(instance);
        }
    };
    var instance;

    module('Widget.proxy', mod);
    test('(String)', function () {
        var W = instance.web.Widget.extend({
            exec: function () {
                this.executed = true;
            }
        });
        var w = new W;
        var fn = w.proxy('exec');
        fn();
        ok(w.executed, 'should execute the named method in the right context');
    });
    test('(String)(*args)', function () {
        var W = instance.web.Widget.extend({
            exec: function (arg) {
                this.executed = arg;
            }
        });
        var w = new W;
        var fn = w.proxy('exec');
        fn(42);
        ok(w.executed, "should execute the named method in the right context");
        equal(w.executed, 42, "should be passed the proxy's arguments");
    });
    test('(String), include', function () {
        // the proxy function should handle methods being changed on the class
        // and should always proxy "by name", to the most recent one
        var W = instance.web.Widget.extend({
            exec: function () {
                this.executed = 1;
            }
        });
        var w = new W;
        var fn = w.proxy('exec');
        W.include({
            exec: function () { this.executed = 2; }
        });

        fn();
        equal(w.executed, 2, "should be lazily resolved");
    });

    test('(Function)', function () {
        var w = new (instance.web.Widget.extend({ }));

        var fn = w.proxy(function () { this.executed = true; });
        fn();
        ok(w.executed, "should set the function's context (like Function#bind)");
    });
    test('(Function)(*args)', function () {
        var w = new (instance.web.Widget.extend({ }));

        var fn = w.proxy(function (arg) { this.executed = arg; });
        fn(42);
        equal(w.executed, 42, "should be passed the proxy's arguments");
    });
});

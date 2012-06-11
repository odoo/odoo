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

    module('Widget.renderElement', mod);
    test('no template, default', function () {
        var w = new (instance.web.Widget.extend({ }));

        ok(!w.$el, "should not initially have a root element");
        w.renderElement();
        ok(w.$el, "should have generated a root element");
        strictEqual(w.$element, w.$el, "should provide $element alias");
        ok(w.$el.is(w.el), "should provide raw DOM alias");

        equal(w.el.nodeName, 'DIV', "should have generated the default element");
        equal(w.el.attributes.length, 0, "should not have generated any attribute");
        ok(_.isEmpty(w.$el.html(), "should not have generated any content"));
    });
    test('no template, custom tag', function () {
        var w = new (instance.web.Widget.extend({
            tagName: 'ul'
        }));
        w.renderElement();

        equal(w.el.nodeName, 'UL', "should have generated the custom element tag");
    });
    test('no template, @id', function () {
        var w = new (instance.web.Widget.extend({
            id: 'foo'
        }));
        w.renderElement();

        equal(w.el.attributes.length, 1, "should have one attribute");
        equal(w.$el.attr('id'), 'foo', "should have generated the id attribute");
        equal(w.el.id, 'foo', "should also be available via property");
    });
    test('no template, @className', function () {
        var w = new (instance.web.Widget.extend({
            className: 'oe_some_class'
        }));
        w.renderElement();

        equal(w.el.className, 'oe_some_class', "should have the right property");
        equal(w.$el.attr('class'), 'oe_some_class', "should have the right attribute");
    });
    test('no template, bunch of attributes', function () {
        var w = new (instance.web.Widget.extend({
            attributes: {
                'id': 'some_id',
                'class': 'some_class',
                'data-foo': 'data attribute',
                'clark': 'gable',
                'spoiler': 'snape kills dumbledore'
            }
        }));
        w.renderElement();

        equal(w.el.attributes.length, 5, "should have all the specified attributes");

        equal(w.el.id, 'some_id');
        equal(w.$el.attr('id'), 'some_id');

        equal(w.el.className, 'some_class');
        equal(w.$el.attr('class'), 'some_class');

        equal(w.$el.attr('data-foo'), 'data attribute');
        equal(w.$el.data('foo'), 'data attribute');

        equal(w.$el.attr('clark'), 'gable');
        equal(w.$el.attr('spoiler'), 'snape kills dumbledore');
    });
});

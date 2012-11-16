openerp.testing.section('Widget.proxy', {
    dependencies: ['web.corelib']
}, function (test) {
    test('(String)', function (instance) {
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
    test('(String)(*args)', function (instance) {
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
    test('(String), include', function (instance) {
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

    test('(Function)', function (instance) {
        var w = new (instance.web.Widget.extend({ }));

        var fn = w.proxy(function () { this.executed = true; });
        fn();
        ok(w.executed, "should set the function's context (like Function#bind)");
    });
    test('(Function)(*args)', function (instance) {
        var w = new (instance.web.Widget.extend({ }));

        var fn = w.proxy(function (arg) { this.executed = arg; });
        fn(42);
        equal(w.executed, 42, "should be passed the proxy's arguments");
    });
});
openerp.testing.section('Widget.renderElement', {
    dependencies: ['web.corelib'],
    setup: function (instance) {
        instance.web.qweb = new QWeb2.Engine();
        instance.web.qweb.add_template(
            '<no>' +
                '<t t-name="test.widget.template">' +
                    '<ol>' +
                        '<li t-foreach="5" t-as="counter" ' +
                            't-attf-class="class-#{counter}">' +
                            '<input/>' +
                            '<t t-esc="counter"/>' +
                        '</li>' +
                    '</ol>' +
                '</t>' +
                '<t t-name="test.widget.template-value">' +
                    '<p><t t-esc="widget.value"/></p>' +
                '</t>' +
            '</no>');
    }
}, function (test) {
    test('no template, default', function (instance) {
        var w = new (instance.web.Widget.extend({ }));

        var $original = w.$el;
        ok($original, "should initially have a root element");
        w.renderElement();
        ok(w.$el, "should have generated a root element");
        ok($original !== w.$el, "should have generated a new root element");
        strictEqual(w.$el, w.$el, "should provide $el alias");
        ok(w.$el.is(w.el), "should provide raw DOM alias");

        equal(w.el.nodeName, 'DIV', "should have generated the default element");
        equal(w.el.attributes.length, 0, "should not have generated any attribute");
        ok(_.isEmpty(w.$el.html(), "should not have generated any content"));
    });
    test('no template, custom tag', function (instance) {
        var w = new (instance.web.Widget.extend({
            tagName: 'ul'
        }));
        w.renderElement();

        equal(w.el.nodeName, 'UL', "should have generated the custom element tag");
    });
    test('no template, @id', function (instance) {
        var w = new (instance.web.Widget.extend({
            id: 'foo'
        }));
        w.renderElement();

        equal(w.el.attributes.length, 1, "should have one attribute");
        equal(w.$el.attr('id'), 'foo', "should have generated the id attribute");
        equal(w.el.id, 'foo', "should also be available via property");
    });
    test('no template, @className', function (instance) {
        var w = new (instance.web.Widget.extend({
            className: 'oe_some_class'
        }));
        w.renderElement();

        equal(w.el.className, 'oe_some_class', "should have the right property");
        equal(w.$el.attr('class'), 'oe_some_class', "should have the right attribute");
    });
    test('no template, bunch of attributes', function (instance) {
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

    test('template', function (instance) {
        var w = new (instance.web.Widget.extend({
            template: 'test.widget.template'
        }));
        w.renderElement();

        equal(w.el.nodeName, 'OL');
        equal(w.$el.children().length, 5);
        equal(w.el.textContent, '01234');
    });
    test('repeated', { asserts: 4 }, function (instance, $fix) {
        var w = new (instance.web.Widget.extend({
            template: 'test.widget.template-value'
        }));
        w.value = 42;
        return w.appendTo($fix)
            .done(function () {
                equal($fix.find('p').text(), '42', "DOM fixture should contain initial value");
                equal(w.$el.text(), '42', "should set initial value");
                w.value = 36;
                w.renderElement();
                equal($fix.find('p').text(), '36', "DOM fixture should use new value");
                equal(w.$el.text(), '36', "should set new value");
            });
    });
});
openerp.testing.section('Widget.$', {
    dependencies: ['web.corelib'],
    setup: function (instance) {
        instance.web.qweb = new QWeb2.Engine();
        instance.web.qweb.add_template(
            '<no>' +
                '<t t-name="test.widget.template">' +
                    '<ol>' +
                        '<li t-foreach="5" t-as="counter" ' +
                            't-attf-class="class-#{counter}">' +
                            '<input/>' +
                            '<t t-esc="counter"/>' +
                        '</li>' +
                    '</ol>' +
                '</t>' +
            '</no>');
    }
}, function (test) {
    test('basic-alias', function (instance) {
        var w = new (instance.web.Widget.extend({
            template: 'test.widget.template'
        }));
        w.renderElement();

        ok(w.$('li:eq(3)').is(w.$el.find('li:eq(3)')),
           "should do the same thing as calling find on the widget root");
    });
});
openerp.testing.section('Widget.events', {
    dependencies: ['web.corelib'],
    setup: function (instance) {
        instance.web.qweb = new QWeb2.Engine();
        instance.web.qweb.add_template(
            '<no>' +
                '<t t-name="test.widget.template">' +
                    '<ol>' +
                        '<li t-foreach="5" t-as="counter" ' +
                            't-attf-class="class-#{counter}">' +
                            '<input/>' +
                            '<t t-esc="counter"/>' +
                        '</li>' +
                    '</ol>' +
                '</t>' +
            '</no>');
    }
}, function (test) {
    test('delegate', function (instance) {
        var a = [];
        var w = new (instance.web.Widget.extend({
            template: 'test.widget.template',
            events: {
                'click': function () {
                    a[0] = true;
                    strictEqual(this, w, "should trigger events in widget")
                },
                'click li.class-3': 'class3',
                'change input': function () { a[2] = true; }
            },
            class3: function () { a[1] = true; }
        }));
        w.renderElement();

        w.$el.click();
        w.$('li:eq(3)').click();
        w.$('input:last').val('foo').change();

        for(var i=0; i<3; ++i) {
            ok(a[i], "should pass test " + i);
        }
    });
    test('undelegate', function (instance) {
        var clicked = false, newclicked = false;
        var w = new (instance.web.Widget.extend({
            template: 'test.widget.template',
            events: { 'click li': function () { clicked = true; } }
        }));
        w.renderElement();
        w.$el.on('click', 'li', function () { newclicked = true });

        w.$('li').click();
        ok(clicked, "should trigger bound events");
        ok(newclicked, "should trigger bound events");
        clicked = newclicked = false;

        w.undelegateEvents();
        w.$('li').click();
        ok(!clicked, "undelegate should unbind events delegated");
        ok(newclicked, "undelegate should only unbind events it created");
    });
});

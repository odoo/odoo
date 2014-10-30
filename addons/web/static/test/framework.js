(function() {

var ropenerp = window.openerp;

var openerp = ropenerp.declare($, _, QWeb2);

ropenerp.testing.section('class', {
    dependencies: ['web.core']
}, function (test) {
    test('Basic class creation', function () {
        var C = openerp.Class.extend({
            foo: function () {
                return this.somevar;
            }
        });
        var i = new C();
        i.somevar = 3;

        ok(i instanceof C);
        strictEqual(i.foo(), 3);
    });
    test('Class initialization', function () {
        var C1 = openerp.Class.extend({
            init: function () {
                this.foo = 3;
            }
        });
        var C2 = openerp.Class.extend({
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
        var C0 = openerp.Class.extend({
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
        var C0 = openerp.Class.extend({
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
        var C0 = openerp.Class.extend({
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
        var C0 = openerp.Class.extend({
            foo: function () { return 1; },
            bar: function () { return 1; }
        });
        var i = new C0();
        strictEqual(i.foo(), 1);
        strictEqual(i.bar(), 1);

        C0.include({
            foo: function () { return 2; },
            bar: function () { return 2 + this._super(); }
        });
        strictEqual(i.foo(), 2);
        strictEqual(i.bar(), 3);
    });
    test('In-place extension of subclassed types', function () {
        var C0 = openerp.Class.extend({
            foo: function () { return 1; },
            bar: function () { return 1; }
        });
        var C1 = C0.extend({
            foo: function () { return 1 + this._super(); },
            bar: function () { return 1 + this._super(); }
        });
        var i = new C1();
        strictEqual(i.foo(), 2);
        C0.include({
            foo: function () { return 2; },
            bar: function () { return 2 + this._super(); }
        });
        strictEqual(i.foo(), 3);
        strictEqual(i.bar(), 4);
    });
});


ropenerp.testing.section('Widget.proxy', {
}, function (test) {
    test('(String)', function () {
        var W = openerp.Widget.extend({
            exec: function () {
                this.executed = true;
            }
        });
        var w = new W();
        var fn = w.proxy('exec');
        fn();
        ok(w.executed, 'should execute the named method in the right context');
    });
    test('(String)(*args)', function () {
        var W = openerp.Widget.extend({
            exec: function (arg) {
                this.executed = arg;
            }
        });
        var w = new W();
        var fn = w.proxy('exec');
        fn(42);
        ok(w.executed, "should execute the named method in the right context");
        equal(w.executed, 42, "should be passed the proxy's arguments");
    });
    test('(String), include', function () {
        // the proxy function should handle methods being changed on the class
        // and should always proxy "by name", to the most recent one
        var W = openerp.Widget.extend({
            exec: function () {
                this.executed = 1;
            }
        });
        var w = new W();
        var fn = w.proxy('exec');
        W.include({
            exec: function () { this.executed = 2; }
        });

        fn();
        equal(w.executed, 2, "should be lazily resolved");
    });

    test('(Function)', function () {
        var w = new (openerp.Widget.extend({ }))();

        var fn = w.proxy(function () { this.executed = true; });
        fn();
        ok(w.executed, "should set the function's context (like Function#bind)");
    });
    test('(Function)(*args)', function () {
        var w = new (openerp.Widget.extend({ }))();

        var fn = w.proxy(function (arg) { this.executed = arg; });
        fn(42);
        equal(w.executed, 42, "should be passed the proxy's arguments");
    });
});
ropenerp.testing.section('Widget.renderElement', {
    setup: function () {
        openerp.qweb = new QWeb2.Engine();
        openerp.qweb.add_template(
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
    test('no template, default', function () {
        var w = new (openerp.Widget.extend({ }))();

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
    test('no template, custom tag', function () {
        var w = new (openerp.Widget.extend({
            tagName: 'ul'
        }))();
        w.renderElement();

        equal(w.el.nodeName, 'UL', "should have generated the custom element tag");
    });
    test('no template, @id', function () {
        var w = new (openerp.Widget.extend({
            id: 'foo'
        }))();
        w.renderElement();

        equal(w.el.attributes.length, 1, "should have one attribute");
        equal(w.$el.attr('id'), 'foo', "should have generated the id attribute");
        equal(w.el.id, 'foo', "should also be available via property");
    });
    test('no template, @className', function () {
        var w = new (openerp.Widget.extend({
            className: 'oe_some_class'
        }))();
        w.renderElement();

        equal(w.el.className, 'oe_some_class', "should have the right property");
        equal(w.$el.attr('class'), 'oe_some_class', "should have the right attribute");
    });
    test('no template, bunch of attributes', function () {
        var w = new (openerp.Widget.extend({
            attributes: {
                'id': 'some_id',
                'class': 'some_class',
                'data-foo': 'data attribute',
                'clark': 'gable',
                'spoiler': 'snape kills dumbledore'
            }
        }))();
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

    test('template', function () {
        var w = new (openerp.Widget.extend({
            template: 'test.widget.template'
        }))();
        w.renderElement();

        equal(w.el.nodeName, 'OL');
        equal(w.$el.children().length, 5);
        equal(w.el.textContent, '01234');
    });
    test('repeated', { asserts: 4 }, function (_unused, $fix) {
        var w = new (openerp.Widget.extend({
            template: 'test.widget.template-value'
        }))();
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
ropenerp.testing.section('Widget.$', {
    setup: function () {
        openerp.qweb = new QWeb2.Engine();
        openerp.qweb.add_template(
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
    test('basic-alias', function () {
        var w = new (openerp.Widget.extend({
            template: 'test.widget.template'
        }))();
        w.renderElement();

        ok(w.$('li:eq(3)').is(w.$el.find('li:eq(3)')),
           "should do the same thing as calling find on the widget root");
    });
});
ropenerp.testing.section('Widget.events', {
    setup: function () {
        openerp.qweb = new QWeb2.Engine();
        openerp.qweb.add_template(
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
    test('delegate', function () {
        var a = [];
        var w = new (openerp.Widget.extend({
            template: 'test.widget.template',
            events: {
                'click': function () {
                    a[0] = true;
                    strictEqual(this, w, "should trigger events in widget");
                },
                'click li.class-3': 'class3',
                'change input': function () { a[2] = true; }
            },
            class3: function () { a[1] = true; }
        }))();
        w.renderElement();

        w.$el.click();
        w.$('li:eq(3)').click();
        w.$('input:last').val('foo').change();

        for(var i=0; i<3; ++i) {
            ok(a[i], "should pass test " + i);
        }
    });
    test('undelegate', function () {
        var clicked = false, newclicked = false;
        var w = new (openerp.Widget.extend({
            template: 'test.widget.template',
            events: { 'click li': function () { clicked = true; } }
        }))();
        w.renderElement();
        w.$el.on('click', 'li', function () { newclicked = true; });

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
ropenerp.testing.section('Widget.async', {

}, function (test) {
    test("alive(alive)", {asserts: 1}, function () {
        var w = new (openerp.Widget.extend({}));
        return $.async_when(w.start())
        .then(function () { return w.alive($.async_when()) })
        .then(function () { ok(true); });
    });
    test("alive(dead)", {asserts: 1}, function () {
        var w = new (openerp.Widget.extend({}));

        return $.Deferred(function (d) {
            $.async_when(w.start())
            .then(function () {
                // destroy widget
                w.destroy();
                var promise = $.async_when();
                // leave time for alive() to do its stuff
                promise.then(function () {
                    return $.async_when();
                }).then(function () {
                    ok(true);
                    d.resolve();
                });
                // ensure that w.alive() refuses to resolve or reject
                return w.alive(promise);
            }).always(function () {
                d.reject();
                ok(false, "alive() should not terminate by default");
            })
        });
    });


    test("alive(alive, true)", {asserts: 1}, function () {
        var w = new (openerp.Widget.extend({}));
        return $.async_when(w.start())
        .then(function () { return w.alive($.async_when(), true) })
        .then(function () { ok(true); });
    });
    test("alive(dead, true)", {asserts: 1, fail_on_rejection: false}, function () {
        var w = new (openerp.Widget.extend({}));

        return $.async_when(w.start())
        .then(function () {
            // destroy widget
            w.destroy();
            console.log('destroyed');
            return w.alive($.async_when().done(function () { console.log('when'); }), true);
        }).then(function () {
            console.log('unfailed')
            ok(false, "alive(p, true) should fail its promise");
        }, function () {
            console.log('failed')
            ok(true, "alive(p, true) should fail its promise");
        });
    });

});

    ropenerp.testing.section('server-formats', {
    dependencies: ['web.core', 'web.dates']
}, function (test) {
    test('Parse server datetime', function () {
        var date = openerp.str_to_datetime("2009-05-04 12:34:23");
        deepEqual(
            [date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate(),
             date.getUTCHours(), date.getUTCMinutes(), date.getUTCSeconds()],
            [2009, 5 - 1, 4, 12, 34, 23]);
        deepEqual(
            [date.getFullYear(), date.getMonth(), date.getDate(),
             date.getHours(), date.getMinutes(), date.getSeconds()],
            [2009, 5 - 1, 4, 12 - (date.getTimezoneOffset() / 60), 34, 23]);

        var date2 = openerp.str_to_datetime('2011-12-10 00:00:00');
        deepEqual(
            [date2.getUTCFullYear(), date2.getUTCMonth(), date2.getUTCDate(),
             date2.getUTCHours(), date2.getUTCMinutes(), date2.getUTCSeconds()],
            [2011, 12 - 1, 10, 0, 0, 0]);

        var date3 = openerp.str_to_datetime("2009-05-04 12:34:23.84565");
        deepEqual(
            [date3.getUTCFullYear(), date3.getUTCMonth(), date3.getUTCDate(),
             date3.getUTCHours(), date3.getUTCMinutes(), date3.getUTCSeconds(), date3.getUTCMilliseconds()],
            [2009, 5 - 1, 4, 12, 34, 23, 845]);
    });
    test('Parse server datetime on 31', {asserts: 1}, function() {
        var wDate = window.Date;
        var s = ropenerp.testing.Stack();
        return s.push(function() {
            window.Date = function(v) {
                if (_.isUndefined(v)) {
                    v = '2013-10-31 12:34:56';
                }
                return new wDate(v);
            };
        }, function() {
            window.Date = wDate;
        }).execute(function() {
            return openerp.str_to_datetime('2013-11-11 02:45:21');
        }).then(function(date) {
            deepEqual(
                [date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate(),
                 date.getUTCHours(), date.getUTCMinutes(), date.getUTCSeconds()],
                [2013, 11 - 1, 11, 2, 45, 21]);
        });

    });
    test('Parse server date', function () {
        var date = openerp.str_to_date("2009-05-04");
        deepEqual(
            [date.getFullYear(), date.getMonth(), date.getDate()],
            [2009, 5 - 1, 4]);
    });
    test('Parse server date on 31', {asserts: 1}, function() {
        var wDate = window.Date;
        var s = ropenerp.testing.Stack();
        return s.push(function() {
            window.Date = function(v) {
                if (_.isUndefined(v)) {
                    v = '2013-10-31 12:34:56';
                }
                return new wDate(v);
            };
        }, function() {
            window.Date = wDate;
        }).execute(function() {
            return openerp.str_to_date('2013-11-21');
        }).then(function(date) {
            deepEqual(
                [date.getFullYear(), date.getMonth(), date.getDate()],
                [2013, 11 - 1, 21]);
        });

    });
    test('Parse server time', function () {
        var date = openerp.str_to_time("12:34:23");
        deepEqual(
            [date.getHours(), date.getMinutes(), date.getSeconds()],
            [12, 34, 23]);

        date = openerp.str_to_time("12:34:23.5467");
        deepEqual(
            [date.getHours(), date.getMinutes(), date.getSeconds(), date.getMilliseconds()],
            [12, 34, 23, 546]);
    });
    test('Format server datetime', function () {
        var date = new Date();
        date.setUTCFullYear(2009);
        date.setUTCMonth(5 - 1);
        date.setUTCDate(4);
        date.setUTCHours(12);
        date.setUTCMinutes(34);
        date.setUTCSeconds(23);
        equal(openerp.datetime_to_str(date), "2009-05-04 12:34:23");
    });
    test('Format server date', function () {
        var date = new Date();
        date.setUTCFullYear(2009);
        date.setUTCMonth(5 - 1);
        date.setUTCDate(4);
        date.setUTCHours(0);
        date.setUTCMinutes(0);
        date.setUTCSeconds(0);
        equal(openerp.date_to_str(date), "2009-05-04");
    });
    test('Format server time', function () {
        var date = new Date();
        date.setUTCFullYear(1970);
        date.setUTCMonth(1 - 1);
        date.setUTCDate(1);
        date.setUTCHours(0);
        date.setUTCMinutes(0);
        date.setUTCSeconds(0);
        date.setHours(12);
        date.setMinutes(34);
        date.setSeconds(23);
        equal(openerp.time_to_str(date), "12:34:23");
    });
});

})();

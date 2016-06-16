odoo.define_section('class', ['web.Class'], function (test) {

    test('Basic class creation', function (assert, Class) {
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

    test('Class initialization', function (assert, Class) {
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

    test('Inheritance', function (assert, Class) {
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

    test('In-place extension', function (assert, Class) {
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

    test('In-place extension and inheritance', function (assert, Class) {
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

    test('In-place extensions alter existing instances', function (assert, Class) {
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

    test('In-place extension of subclassed types', function (assert, Class) {
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

odoo.define_section('Widget.proxy', ['web.Widget'], function (test) {
    test('(String)', function (assert, Widget) {
        var W = Widget.extend({
            exec: function () {
                this.executed = true;
            }
        });
        var w = new W();
        var fn = w.proxy('exec');
        fn();
        assert.ok(w.executed, 'should execute the named method in the right context');
    });

    test('(String)(*args)', function (assert, Widget) {
        var W = Widget.extend({
            exec: function (arg) {
                this.executed = arg;
            }
        });
        var w = new W();
        var fn = w.proxy('exec');
        fn(42);
        assert.ok(w.executed, "should execute the named method in the right context");
        assert.equal(w.executed, 42, "should be passed the proxy's arguments");
    });

    test('(String), include', function (assert, Widget) {
        // the proxy function should handle methods being changed on the class
        // and should always proxy "by name", to the most recent one
        var W = Widget.extend({
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
        assert.equal(w.executed, 2, "should be lazily resolved");
    });

    test('(Function)', function (assert, Widget) {
        var w = new (Widget.extend({ }))();

        var fn = w.proxy(function () { this.executed = true; });
        fn();
        assert.ok(w.executed, "should set the function's context (like Function#bind)");
    });

    test('(Function)(*args)', function (assert, Widget) {
        var w = new (Widget.extend({ }))();

        var fn = w.proxy(function (arg) { this.executed = arg; });
        fn(42);
        assert.equal(w.executed, 42, "should be passed the proxy's arguments");
    });

});

odoo.define_section('Widget.renderElement', ['web.Widget'], function (test) {

    test('no template, default', function (assert, Widget) {
        var widget = new (Widget.extend({ }))();

        var $original = widget.$el;
        assert.ok($original, "should initially have a root element");
        
        widget.renderElement();

        assert.ok(widget.$el, "should have generated a root element");
        assert.ok($original !== widget.$el, "should have generated a new root element");
        assert.strictEqual(widget.$el, widget.$el, "should provide $el alias");
        assert.ok(widget.$el.is(widget.el), "should provide raw DOM alias");

        assert.equal(widget.el.nodeName, 'DIV', "should have generated the default element");
        assert.equal(widget.el.attributes.length, 0, "should not have generated any attribute");
        assert.ok(_.isEmpty(widget.$el.html(), "should not have generated any content"));
    });

    test('no template, custom tag', function (assert, Widget) {

        var widget = new (Widget.extend({
            tagName: 'ul'
        }))();
        widget.renderElement();

        assert.equal(widget.el.nodeName, 'UL', "should have generated the custom element tag");
    });

    test('no template, @id', function (assert, Widget) {
        var widget = new (Widget.extend({
            id: 'foo'
        }))();
        widget.renderElement();

        assert.equal(widget.el.attributes.length, 1, "should have one attribute");
        assert.equal(widget.$el.attr('id'), 'foo', "should have generated the id attribute");
        assert.equal(widget.el.id, 'foo', "should also be available via property");
    });

    test('no template, @className', function (assert, Widget) {
        var widget = new (Widget.extend({
            className: 'oe_some_class'
        }))();
        widget.renderElement();

        assert.equal(widget.el.className, 'oe_some_class', "should have the right property");
        assert.equal(widget.$el.attr('class'), 'oe_some_class', "should have the right attribute");
    });

    test('no template, bunch of attributes', function (assert, Widget) {
        var widget = new (Widget.extend({
            attributes: {
                'id': 'some_id',
                'class': 'some_class',
                'data-foo': 'data attribute',
                'clark': 'gable',
                'spoiler': // don't read the next line if you care about Harry Potter...
                      'snape kills dumbledore'
            }
        }))();
        widget.renderElement();

        assert.equal(widget.el.attributes.length, 5, "should have all the specified attributes");

        assert.equal(widget.el.id, 'some_id');
        assert.equal(widget.$el.attr('id'), 'some_id');

        assert.equal(widget.el.className, 'some_class');
        assert.equal(widget.$el.attr('class'), 'some_class');

        assert.equal(widget.$el.attr('data-foo'), 'data attribute');
        assert.equal(widget.$el.data('foo'), 'data attribute');

        assert.equal(widget.$el.attr('clark'), 'gable');
        assert.equal(widget.$el.attr('spoiler'), 'snape kills dumbledore');
    });

    test('template', ['web.core'], function (assert, Widget, core) {
        core.qweb.add_template(
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
            '</no>'
        );

        var widget = new (Widget.extend({
            template: 'test.widget.template'
        }))();
        widget.renderElement();

        assert.equal(widget.el.nodeName, 'OL');
        assert.equal(widget.$el.children().length, 5);
        assert.equal(widget.el.textContent, '01234');
    });

    test('repeated', ['web.core'], function (assert, Widget, core) {
        assert.expect(4);
        var $fix = $( "#qunit-fixture");

        core.qweb.add_template(
            '<no>' +
                '<t t-name="test.widget.template">' +
                    '<p><t t-esc="widget.value"/></p>' +
                '</t>' +
            '</no>'
        );
        var widget = new (Widget.extend({
            template: 'test.widget.template'
        }))();
        widget.value = 42;

        return widget.appendTo($fix)
            .done(function () {
                assert.equal($fix.find('p').text(), '42', "DOM fixture should contain initial value");
                assert.equal(widget.$el.text(), '42', "should set initial value");
                widget.value = 36;
                widget.renderElement();
                assert.equal($fix.find('p').text(), '36', "DOM fixture should use new value");
                assert.equal(widget.$el.text(), '36', "should set new value");
            });
    });

});

odoo.define_section('Widget.$', ['web.Widget', 'web.core'], function (test) {

    test('basic-alias', function (assert, Widget, core) {
        core.qweb.add_template(
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
            '</no>'
        );
        var widget = new (Widget.extend({
            template: 'test.widget.template'
        }))();
        widget.renderElement();

        assert.ok(widget.$('li:eq(3)').is(widget.$el.find('li:eq(3)')),
           "should do the same thing as calling find on the widget root");
    });

});

odoo.define_section('Widget.events', ['web.Widget', 'web.core'], function (test) {
    function setup(qweb) {
       qweb.add_template(
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
            '</no>'
        );
    }

    test('delegate', function (assert, Widget, core) {
        setup(core.qweb);

        var a = [];
        var widget = new (Widget.extend({
            template: 'test.widget.template',
            events: {
                'click': function () {
                    a[0] = true;
                    assert.strictEqual(this, widget, "should trigger events in widget");
                },
                'click li.class-3': 'class3',
                'change input': function () { a[2] = true; }
            },
            class3: function () { a[1] = true; }
        }))();
        widget.renderElement();

        widget.$el.click();
        widget.$('li:eq(3)').click();
        widget.$('input:last').val('foo').change();

        for(var i=0; i<3; ++i) {
            assert.ok(a[i], "should pass test " + i);
        }
    });

    test('undelegate', function (assert, Widget, core) {
        setup(core.qweb);

        var clicked = false,
            newclicked = false;

        var widget = new (Widget.extend({
            template: 'test.widget.template',
            events: { 'click li': function () { clicked = true; } }
        }))();

        widget.renderElement();
        widget.$el.on('click', 'li', function () { newclicked = true; });

        widget.$('li').click();
        assert.ok(clicked, "should trigger bound events");
        assert.ok(newclicked, "should trigger bound events");
        
        clicked = newclicked = false;
        widget.undelegateEvents();
        widget.$('li').click();
        assert.ok(!clicked, "undelegate should unbind events delegated");
        assert.ok(newclicked, "undelegate should only unbind events it created");
    });
});

odoo.define_section('Widget.async', ['web.Widget', 'web.utils'], function (test) {
    test("alive(alive)", function (assert, Widget, utils) {
        assert.expect(1);

        var widget = new (Widget.extend({}));

        return utils.async_when(widget.start())
            .then(function () { return widget.alive(utils.async_when()) })
            .then(function () { assert.ok(true); });
    });

    test("alive(dead)", function (assert, Widget, utils) {
        assert.expect(1);
        var widget = new (Widget.extend({}));

        return $.Deferred(function (d) {
            utils.async_when(widget.start())
            .then(function () {
                // destroy widget
                widget.destroy();
                var promise = utils.async_when();
                // leave time for alive() to do its stuff
                promise.then(function () {
                    return utils.async_when();
                }).then(function () {
                    assert.ok(true);
                    d.resolve();
                });
                // ensure that widget.alive() refuses to resolve or reject
                return widget.alive(promise);
            }).always(function () {
                d.reject();
                assert.ok(false, "alive() should not terminate by default");
            })
        });
    });

    test("alive(alive, true)", function (assert, Widget, utils) {
        assert.expect(1);
        var widget = new (Widget.extend({}));
        return utils.async_when(widget.start())
        .then(function () { return widget.alive(utils.async_when(), true) })
        .then(function () { assert.ok(true); });
    });

    test("alive(dead, true)", function (assert, Widget, utils) {
        assert.expect(1);
        var done = assert.async();

        var widget = new (Widget.extend({}));

        utils.async_when(widget.start())
        .then(function () {
            // destroy widget
            widget.destroy();
            console.log('destroyed');
            return widget.alive(utils.async_when().done(function () { console.log('when'); }), true);
        }).then(function () {
            console.log('unfailed')
            assert.ok(false, "alive(p, true) should fail its promise");
            done();
        }, function () {
            console.log('failed')
            assert.ok(true, "alive(p, true) should fail its promise");
            done();
        });
    });

});


odoo.define_section('server-formats', ['web.time'], function (test) {

    test('Parse server datetime', function (assert, time) {
        var date = time.str_to_datetime("2009-05-04 12:34:23");
        assert.deepEqual(
            [date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate(),
             date.getUTCHours(), date.getUTCMinutes(), date.getUTCSeconds()],
            [2009, 5 - 1, 4, 12, 34, 23]);
        assert.deepEqual(
            [date.getFullYear(), date.getMonth(), date.getDate(),
             date.getHours(), date.getMinutes(), date.getSeconds()],
            [2009, 5 - 1, 4, 12 - (date.getTimezoneOffset() / 60), 34, 23]);

        var date2 = time.str_to_datetime('2011-12-10 00:00:00');
        assert.deepEqual(
            [date2.getUTCFullYear(), date2.getUTCMonth(), date2.getUTCDate(),
             date2.getUTCHours(), date2.getUTCMinutes(), date2.getUTCSeconds()],
            [2011, 12 - 1, 10, 0, 0, 0]);

        var date3 = time.str_to_datetime("2009-05-04 12:34:23.84565");
        assert.deepEqual(
            [date3.getUTCFullYear(), date3.getUTCMonth(), date3.getUTCDate(),
             date3.getUTCHours(), date3.getUTCMinutes(), date3.getUTCSeconds(), date3.getUTCMilliseconds()],
            [2009, 5 - 1, 4, 12, 34, 23, 845]);
    });

    test('Parse server datetime on 31', function (assert, time) {
        var wDate = window.Date;

        try {
            window.Date = function (v) {
                if (_.isUndefined(v)) {
                    v = '2013-10-31 12:34:56';
                }
                return new wDate(v);
            };
            var date = time.str_to_datetime('2013-11-11 02:45:21');

            assert.deepEqual(
                    [date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate(),
                     date.getUTCHours(), date.getUTCMinutes(), date.getUTCSeconds()],
                    [2013, 11 - 1, 11, 2, 45, 21]);
        }
        finally {
            window.Date = wDate;
        }
    });

    test('Parse server date', function (assert, time) {
        var date = time.str_to_date("2009-05-04");
        assert.deepEqual(
            [date.getFullYear(), date.getMonth(), date.getDate()],
            [2009, 5 - 1, 4]);
    });

    test('Parse server date on 31', function (assert, time) {
        var wDate = window.Date;

        try {
            window.Date = function (v) {
                if (_.isUndefined(v)) {
                    v = '2013-10-31 12:34:56';
                }
                return new wDate(v);
            };
            var date = time.str_to_date('2013-11-21');

            assert.deepEqual(
                [date.getFullYear(), date.getMonth(), date.getDate()],
                [2013, 11 - 1, 21]);
        }
        finally {
            window.Date = wDate;
        }

    });

    test('Parse server time', function (assert, time) {
        var date = time.str_to_time("12:34:23");
        assert.deepEqual(
            [date.getHours(), date.getMinutes(), date.getSeconds()],
            [12, 34, 23]);

        date = time.str_to_time("12:34:23.5467");
        assert.deepEqual(
            [date.getHours(), date.getMinutes(), date.getSeconds(), date.getMilliseconds()],
            [12, 34, 23, 546]);
    });

    test('Format server datetime', function (assert, time) {
        var date = new Date();
        date.setUTCFullYear(2009);
        date.setUTCMonth(5 - 1);
        date.setUTCDate(4);
        date.setUTCHours(12);
        date.setUTCMinutes(34);
        date.setUTCSeconds(23);
        assert.equal(time.datetime_to_str(date), "2009-05-04 12:34:23");
    });

    test('Format server date', function (assert, time) {
        var date = new Date();
        date.setUTCFullYear(2009);
        date.setUTCMonth(5 - 1);
        date.setUTCDate(4);
        date.setUTCHours(0);
        date.setUTCMinutes(0);
        date.setUTCSeconds(0);
        assert.equal(time.date_to_str(date), "2009-05-04");
    });

    test('Format server time', function (assert, time) {
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
        assert.equal(time.time_to_str(date), "12:34:23");
    });

});

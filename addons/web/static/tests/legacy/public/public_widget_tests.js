import publicWidget from "@web/legacy/js/public/public_widget";
import testUtils from "@web/../tests/legacy_tests/helpers/test_utils";
import { renderToString } from "@web/core/utils/render";

const Widget = publicWidget.Widget;

QUnit.module('core', {}, function () {

    QUnit.module('Widget');

    QUnit.test('proxy (String)', function (assert) {
        assert.expect(1);

        var W = Widget.extend({
            exec: function () {
                this.executed = true;
            }
        });
        var w = new W();
        var fn = w.proxy('exec');
        fn();
        assert.ok(w.executed, 'should execute the named method in the right context');
        w.destroy();
    });

    QUnit.test('proxy (String)(*args)', function (assert) {
        assert.expect(2);

        var W = Widget.extend({
            exec: function (arg) {
                this.executed = arg;
            }
        });
        var w = new W();
        var fn = w.proxy('exec');
        fn(42);
        assert.ok(w.executed, "should execute the named method in the right context");
        assert.strictEqual(w.executed, 42, "should be passed the proxy's arguments");
        w.destroy();
    });

    QUnit.test('proxy (String), include', function (assert) {
        assert.expect(1);

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
        assert.strictEqual(w.executed, 2, "should be lazily resolved");
        w.destroy();
    });

    QUnit.test('proxy (Function)', function (assert) {
        assert.expect(1);

        var w = new (Widget.extend({ }))();

        var fn = w.proxy(function () { this.executed = true; });
        fn();
        assert.ok(w.executed, "should set the function's context (like Function#bind)");
        w.destroy();
    });

    QUnit.test('proxy (Function)(*args)', function (assert) {
        assert.expect(1);

        var w = new (Widget.extend({ }))();

        var fn = w.proxy(function (arg) { this.executed = arg; });
        fn(42);
        assert.strictEqual(w.executed, 42, "should be passed the proxy's arguments");
        w.destroy();
    });

    QUnit.test('renderElement, no template, default', function (assert) {
        assert.expect(7);

        var widget = new (Widget.extend({ }))();

        assert.strictEqual(widget.$el, undefined, "should not have a root element");

        widget.renderElement();

        assert.ok(widget.$el, "should have generated a root element");
        assert.strictEqual(widget.$el, widget.$el, "should provide $el alias");
        assert.ok(widget.$el.is(widget.el), "should provide raw DOM alias");

        assert.strictEqual(widget.el.nodeName, 'DIV', "should have generated the default element");
        assert.strictEqual(widget.el.attributes.length, 0, "should not have generated any attribute");
        assert.ok(Object.keys(widget.$el.html() || {}).length === 0, "should not have generated any content");
        widget.destroy();
    });

    QUnit.test('no template, custom tag', function (assert) {
        assert.expect(1);


        var widget = new (Widget.extend({
            tagName: 'ul'
        }))();
        widget.renderElement();

        assert.strictEqual(widget.el.nodeName, 'UL', "should have generated the custom element tag");
        widget.destroy();
    });

    QUnit.test('no template, @id', function (assert) {
        assert.expect(3);

        var widget = new (Widget.extend({
            id: 'foo'
        }))();
        widget.renderElement();

        assert.strictEqual(widget.el.attributes.length, 1, "should have one attribute");
        assert.hasAttrValue(widget.$el, 'id', 'foo', "should have generated the id attribute");
        assert.strictEqual(widget.el.id, 'foo', "should also be available via property");
        widget.destroy();
    });

    QUnit.test('no template, @className', function (assert) {
        assert.expect(2);

        var widget = new (Widget.extend({
            className: 'oe_some_class'
        }))();
        widget.renderElement();

        assert.strictEqual(widget.el.className, 'oe_some_class', "should have the right property");
        assert.hasAttrValue(widget.$el, 'class', 'oe_some_class', "should have the right attribute");
        widget.destroy();
    });

    QUnit.test('no template, bunch of attributes', function (assert) {
        assert.expect(9);

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

        assert.strictEqual(widget.el.attributes.length, 5, "should have all the specified attributes");

        assert.strictEqual(widget.el.id, 'some_id');
        assert.hasAttrValue(widget.$el, 'id', 'some_id');

        assert.strictEqual(widget.el.className, 'some_class');
        assert.hasAttrValue(widget.$el, 'class', 'some_class');

        assert.hasAttrValue(widget.$el, 'data-foo', 'data attribute');
        assert.strictEqual(widget.$el.data('foo'), 'data attribute');

        assert.hasAttrValue(widget.$el, 'clark', 'gable');
        assert.hasAttrValue(widget.$el, 'spoiler', 'snape kills dumbledore');
        widget.destroy();
    });

    QUnit.test('template', function (assert) {
        assert.expect(3);

        renderToString.app.addTemplate(
            "test.widget.template.1",
            `<ol>
                <li t-foreach="[0, 1, 2, 3, 4]" t-as="counter" t-key="counter_index" t-attf-class="class-#{counter}">
                    <input/>
                    <t t-esc="counter"/>
                </li>
            </ol>`
        );

        var widget = new (Widget.extend({
            template: 'test.widget.template.1'
        }))();
        widget.renderElement();

        assert.strictEqual(widget.el.nodeName, 'OL');
        assert.strictEqual(widget.$el.children().length, 5);
        assert.strictEqual(widget.el.textContent, '01234');
        widget.destroy();
    });

    QUnit.test('repeated', async function (assert) {
        assert.expect(4);
        var $fix = $( "#qunit-fixture");

        renderToString.app.addTemplate(
            "test.widget.template.2",
            `<p>
                <t t-esc="widget.value"/>
            </p>`
        );
        var widget = new (Widget.extend({
            template: 'test.widget.template.2'
        }))();
        widget.value = 42;

        await widget.appendTo($fix)
            .then(function () {
                assert.strictEqual($fix.find('p').text(), '42', "DOM fixture should contain initial value");
                assert.strictEqual(widget.$el.text(), '42', "should set initial value");
                widget.value = 36;
                widget.renderElement();
                assert.strictEqual($fix.find('p').text(), '36', "DOM fixture should use new value");
                assert.strictEqual(widget.$el.text(), '36', "should set new value");
            });
        widget.destroy();
    });


    QUnit.module('Widgets, with QWeb');

    QUnit.test('basic-alias', function (assert) {
        assert.expect(1);

        renderToString.app.addTemplate(
            "test.widget.template.3",
            `<ol>
                <li t-foreach="[0,1,2,3,4]" t-as="counter" t-key="counter_index" t-attf-class="class-#{counter}">
                    <input/>
                    <t t-esc="counter"/>
                </li>
            </ol>`
        );

        var widget = new (Widget.extend({
            template: 'test.widget.template.3'
        }))();
        widget.renderElement();

        assert.ok(widget.$('li:eq(3)').is(widget.$el.find('li:eq(3)')),
            "should do the same thing as calling find on the widget root");
        widget.destroy();
    });


    QUnit.test('delegate', async function (assert) {
        assert.expect(5);

        renderToString.app.addTemplate(
            "test.widget.template.4",
            `<ol>
                <li t-foreach="[0,1,2,3,4]" t-as="counter" t-key="counter_index" t-attf-class="class-#{counter}">
                    <input/>
                    <t t-esc="counter"/>
                </li>
            </ol>`
        );

        var a = [];
        var widget = new (Widget.extend({
            template: 'test.widget.template.4',
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

        await testUtils.dom.click(widget.$el, {allowInvisible: true});
        await testUtils.dom.click(widget.$('li:eq(3)'), {allowInvisible: true});
        await testUtils.fields.editAndTrigger(widget.$('input:last'), 'foo', 'change');

        for(var i=0; i<3; ++i) {
            assert.ok(a[i], "should pass test " + i);
        }
        widget.destroy();
    });

    QUnit.test('undelegate', async function (assert) {
        assert.expect(4);

        renderToString.app.addTemplate(
            "test.widget.template.5",
            `<ol>
                <li t-foreach="[0,1,2,3,4]" t-as="counter" t-key="counter_index" t-attf-class="class-#{counter}">
                    <input/>
                    <t t-esc="counter"/>
                </li>
            </ol>`
        );

        var clicked = false;
        var newclicked = false;

        var widget = new (Widget.extend({
            template: 'test.widget.template.5',
            events: { 'click li': function () { clicked = true; } }
        }))();

        widget.renderElement();
        widget.$el.on('click', 'li', function () { newclicked = true; });

        await testUtils.dom.clickFirst(widget.$('li'), {allowInvisible: true});
        assert.ok(clicked, "should trigger bound events");
        assert.ok(newclicked, "should trigger bound events");

        clicked = newclicked = false;
        widget._undelegateEvents();
        await testUtils.dom.clickFirst(widget.$('li'), {allowInvisible: true});
        assert.ok(!clicked, "undelegate should unbind events delegated");
        assert.ok(newclicked, "undelegate should only unbind events it created");
        widget.destroy();
    });

    QUnit.module('Widget, and async stuff');

    QUnit.test('start is not called when widget is destroyed', function (assert) {
        assert.expect(0);
        const $fix = $("#qunit-fixture");

        // Note: willStart is always async
        const MyWidget = Widget.extend({
            start: function () {
                assert.ok(false, 'Should not call start method');
            },
        });

        const widget = new MyWidget();
        widget.appendTo($fix);
        widget.destroy();

        const divEl = document.createElement('div');
        $fix[0].appendChild(divEl);
        const widget2 = new MyWidget();
        widget2.attachTo(divEl);
        widget2.destroy();
    });

    QUnit.test("don't destroy twice widget's children", function (assert) {
        assert.expect(2);

        var parent = new Widget();
        new (Widget.extend({
            destroy: function () {
                assert.step('destroy');
            }
        }))(parent);

        parent.destroy();
        assert.verifySteps(['destroy'], "child should have been detroyed only once");
    });
});

/** @odoo-module alias=@web/../tests/legacy_tests/core/widget_tests default=false */

import testUtils from "@web/../tests/legacy_tests/helpers/test_utils";
import { renderToString } from "@web/core/utils/render";
import { PublicRoot } from "@web/legacy/js/public/public_root";
import publicWidget from "@web/legacy/js/public/public_widget";

QUnit.module('public', {}, function () {

    QUnit.module('PublicWidget');

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
        var public_widget = new (publicWidget.Widget.extend({
            template: 'test.widget.template.4',
            events: {
                'click': function () {
                    a[0] = true;
                    assert.strictEqual(this, public_widget, "should trigger events in widget");
                },
                'click li.class-3': 'class3',
                'change input': function () { a[2] = true; }
            },
            class3: function () { a[1] = true; }
        }))();
        public_widget.renderElement();

        await testUtils.dom.click(public_widget.$el, {allowInvisible: true});
        await testUtils.dom.click(public_widget.$('li:eq(3)'), {allowInvisible: true});
        await testUtils.fields.editAndTrigger(public_widget.$('input:last'), 'foo', 'change');

        for(var i=0; i<3; ++i) {
            assert.ok(a[i], "should pass test " + i);
        }
        public_widget.destroy();
    });

    QUnit.test('public widget should bind to selector', async function (assert) {
        assert.expect(1);
        var $fix = $( "#qunit-fixture");

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
        var root_public_widget = new (PublicRoot.extend({
            template: 'test.widget.template.4',
        }))();

        publicWidget.registry.Test = publicWidget.Widget.extend({
            selector: '.class-1',
            events: {
                'click': function () {
                    a[0] = true;
                },
            }
        });

        await root_public_widget.appendTo($fix).then(async function(el) {
            await testUtils.dom.click(document.querySelector('.class-1'), {allowInvisible: true});
        })

        assert.strictEqual(a[0], true, "Public Widget should get bind.");

        root_public_widget.destroy();
        delete publicWidget.registry.Test;
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

        var public_widget = new (publicWidget.Widget.extend({
            template: 'test.widget.template.5',
            events: { 'click li': function () { clicked = true; } }
        }))();

        public_widget.renderElement();
        public_widget.$el.on('click', 'li', function () { newclicked = true; });

        await testUtils.dom.clickFirst(public_widget.$('li'), {allowInvisible: true});
        assert.ok(clicked, "should trigger bound events");
        assert.ok(newclicked, "should trigger bound events");

        clicked = newclicked = false;
        public_widget._undelegateEvents();
        await testUtils.dom.clickFirst(public_widget.$('li'), {allowInvisible: true});
        assert.ok(!clicked, "undelegate should unbind events delegated");
        assert.ok(newclicked, "undelegate should only unbind events it created");
        public_widget.destroy();
    });
});

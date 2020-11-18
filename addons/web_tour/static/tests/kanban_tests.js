odoo.define('web_tour.kanban_tests', function (require) {
"use strict";

var KanbanView = require('web.KanbanView');
var testUtils = require('web.test_utils');
var createView = testUtils.createView;

QUnit.module('Web Tour KanbanView', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    foo: {string: "Foo", type: "char"},
                    bar: {string: "Bar", type: "boolean"},
                },
                records: [
                    {id: 1, bar: true, foo: "yop"},
                ]
            },
        };
    }
}, function () {
    QUnit.test('quick create record: cancel when not dirty / on tooltip', async function (assert) {
        assert.expect(4);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban>' +
                    '<field name="bar"/>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div><field name="foo"/></div>' +
                    '</t></templates></kanban>',
            groupBy: ['bar'],
        });

        // click to add an element
        await testUtils.dom.click(kanban.$('.o_kanban_header .o_kanban_quick_add i').first());
        assert.containsOnce(kanban, '.o_kanban_quick_create',
            "should have open the quick create widget");

        // click outside: should remove the quick create
        await testUtils.dom.click(kanban.$('.o_kanban_group .o_kanban_record:first'));
        assert.containsNone(kanban, '.o_kanban_quick_create',
            "the quick create should have been destroyed");

        // click to reopen the quick create
        await testUtils.dom.click(kanban.$('.o_kanban_header .o_kanban_quick_add i').first());
        assert.containsOnce(kanban, '.o_kanban_quick_create',
            "should have re-opened the quick create widget");

        // create a tip element, add it within the DOM and click on it
        // the element is placed at the "body" level to re-create real tour conditions
        let $tooltipElement = $('<div>', {class: 'o_tooltip o_tooltip_visible'})
            .appendTo(kanban.$el.closest('body'))
            .click();

        // clicking on the tooltip should keep the quick create open
        await testUtils.dom.click($tooltipElement);
        assert.containsOnce(kanban, '.o_kanban_quick_create',
            "the quick create should not have been destroyed when tooltip is clicked");

        $tooltipElement.remove();
        kanban.destroy();
    });
});

});

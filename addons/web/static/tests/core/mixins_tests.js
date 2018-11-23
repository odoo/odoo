odoo.define('web.mixins_tests', function (require) {
"use strict";

var core = require('web.core');
var testUtils = require('web.test_utils');
var Widget = require('web.Widget');

QUnit.module('core', {}, function () {

    QUnit.module('mixins');

    QUnit.test('perform a do_action properly', function (assert) {
        assert.expect(3);

        var widget = new Widget();

        testUtils.mock.intercept(widget, 'do_action', function (event) {
            assert.strictEqual(event.data.action, 'test.some_action_id',
                "should have sent proper action name");
            assert.deepEqual(event.data.options, {clear_breadcrumbs: true},
                "should have sent proper options");
            event.data.on_success();
        });

        widget.do_action('test.some_action_id', {clear_breadcrumbs: true}).then(function () {
            assert.step('deferred should have been resolved');
        });
        widget.destroy();
    });

    QUnit.test('perform a trigger properly', function (assert) {
        assert.expect(6);

        var parentWidget = Widget.extend({
            custom_events: {
                'w_event': function (ev) {
                    assert.step('parent_w_event');
                    return ev;
                }
            }
        });

        var childWidget1 = Widget.extend({
            custom_events: {
                'w_event': function (ev) {
                    assert.step('child1_w_event');
                    return ev;
                }
            },
            call_me: function() {
                this.trigger('w_event', {isWorking: true});
            }
        });

        var childWidget2 = Widget.extend({
            custom_events: {
                'w_event': function (ev) {
                    ev.stopPropagation();
                    assert.step('child2_w_event');
                    return ev;
                }
            },
            call_me: function() {
                this.trigger('w_event', {isWorking: true});
            }
        });

        // parent widget instance
        var parentInstance = new parentWidget();
        // child widget instance
        var childInstance1 = new childWidget1(parentInstance);
        // child widget instance to test stopPropagation
        var childInstance2 = new childWidget2(parentInstance);

        // intercept the w_event in parent instance
        testUtils.intercept(parentInstance, 'w_event', function (ev) {
            assert.strictEqual(ev.data.isWorking, true,
                "should have sent proper data");
        },true);

        childInstance1.call_me();

        assert.verifySteps(['child1_w_event', 'parent_w_event']);

        childInstance2.call_me();
        // child2's w_event will stop propagation so w_event of parent should not be called
        assert.verifySteps(['child1_w_event', 'parent_w_event', 'child2_w_event']);

        parentInstance.destroy();
    });

    QUnit.test('perform a trigger properly bu bus', function (assert) {
        assert.expect(2);

        var widget = Widget.extend({
            bindEvent: function() {
                core.bus.on('call_by_bus', this, this.onCallByBus);
            },
            onCallByBus: function(ev) {
                assert.step('called_by_bus');
                return ev;
            }
        });

        // widget instance
        var widgetInstance = new widget();
        // intercept the call_by_bus in widget instance
        testUtils.intercept(widgetInstance, 'call_by_bus', function (ev) {
            assert.strictEqual(ev.data.isWorking, true,
                "should have sent proper data");
        },true);

        // Listen to call_by_bus on bus.
        widgetInstance.bindEvent();

        core.bus.trigger('call_by_bus', {isWorking: true});
        assert.verifySteps(['called_by_bus']);

        widgetInstance.destroy();
    });


});

});


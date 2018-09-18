odoo.define('web.mixins_tests', function (require) {
"use strict";

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

    QUnit.test('test case to perform trigger properly', function (assert) {
        assert.expect(1);

        var parentWidget = Widget.extend({
            custom_events: {
                'w_event': function (isWorking) {
                    return isWorking;
                }
            }
        });

        var childWidget = Widget.extend({
            custom_events: {
                'w_event': function (isWorking) {
                    return isWorking;
                }
            },
            call_me: function() {
                this.trigger('w_event', {isWorking: true});
            }
        });

        // parent widget instance
        var parentInstance = new parentWidget();
        // child widget instance
        var childInstance = new childWidget(parentInstance);

        // intercept the w_event in parent instance
        testUtils.intercept(parentInstance, 'w_event', function (ev) {
            assert.strictEqual(ev.data.isWorking, true,
                "should have sent proper data");
        },true);

        childInstance.call_me();

        parentInstance.destroy();

    });


});

});


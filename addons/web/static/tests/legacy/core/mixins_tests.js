odoo.define('web.mixins_tests', function (require) {
"use strict";

var testUtils = require('web.test_utils');
var Widget = require('web.Widget');

QUnit.module('core', {}, function () {

    QUnit.module('mixins');

    QUnit.test('perform a do_action properly', function (assert) {
        assert.expect(3);
        var done = assert.async();

        var widget = new Widget();

        testUtils.mock.intercept(widget, 'do_action', function (event) {
            assert.strictEqual(event.data.action, 'test.some_action_id',
                "should have sent proper action name");
            assert.deepEqual(event.data.options, {clear_breadcrumbs: true},
                "should have sent proper options");
            event.data.on_success();
        });

        widget.do_action('test.some_action_id', {clear_breadcrumbs: true}).then(function () {
            assert.ok(true, 'deferred should have been resolved');
            widget.destroy();
            done();
        });
    });


});

});


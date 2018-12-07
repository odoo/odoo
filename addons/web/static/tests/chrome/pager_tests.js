odoo.define('web.pager_tests', function (require) {
"use strict";

var Pager = require('web.Pager');
var concurrency = require('web.concurrency');
var testUtils = require('web.test_utils');

QUnit.module('chrome', {}, function () {

    QUnit.module('Pager');

    QUnit.test('basic stuff', function (assert) {
        assert.expect(2);

        var pager = new Pager(null, 10, 1, 4);
        pager.appendTo($('#qunit-fixture'));

        assert.strictEqual(pager.state.current_min, 1,
            "current_min should be set to 1");

        // click on next
        testUtils.dom.click(pager.$('.o_pager_next'));
        assert.strictEqual(pager.state.current_min, 5,
            "current_min should now be 5");

        pager.destroy();
    });

    QUnit.test('edit the pager', function (assert) {
        assert.expect(5);

        var pager = new Pager(null, 10, 1, 4);
        pager.appendTo($('#qunit-fixture'));

        // enter edition
        testUtils.dom.click(pager.$('.o_pager_value'));
        assert.containsOnce(pager, 'input',
            "the pager should contain an input");
        assert.strictEqual(pager.$('input').val(), '1-4',
            "the input should have correct value");

        // change the limit
        pager.$('input')
            .val('1-6')
            .trigger($.Event('keydown', {which: $.ui.keyCode.ENTER})); // trigger the change
        assert.strictEqual(pager.state.limit, 6,
            "the limit should have been updated");
        assert.strictEqual(pager.state.current_min, 1,
            "the current_min should not have changed");
        assert.strictEqual(pager.$('.o_pager_value').text(), '1-6',
            "the input should have correct value");

        pager.destroy();
    });

    QUnit.test('disabling the pager', function (assert) {
        var done = assert.async();
        assert.expect(4);

        var pager = new Pager(null, 10, 1, 4);
        pager.appendTo($('#qunit-fixture'));

        pager.disable();

        // try to go to the next or previous pages
        testUtils.dom.click(pager.$('.o_pager_next'));
        assert.strictEqual(pager.state.current_min, 1,
            "current_min should still be 1");
        testUtils.dom.click(pager.$('.o_pager_previous'));
        assert.strictEqual(pager.state.current_min, 1,
            "current_min should still be 1");

        // try to change the limit
        testUtils.dom.click(pager.$('.o_pager_value'));
        assert.containsNone(pager, 'input',
            "the pager should not contain an input");

        // a common use is to disable the pager before reloading the data, and
        // re-enable it once they have been loaded
        // the following imulates this situation
        pager.on('pager_changed', null, function () {
            pager.disable();
            concurrency.delay(0).then(function () {
                assert.ok(pager.disabled, "pager should still be disabled");
                pager.destroy();
                done();
            });
        });
        pager.enable();
        testUtils.dom.click(pager.$('.o_pager_next'));

    });
});

});
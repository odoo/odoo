odoo.define('web.dialog_tests', function (require) {
"use strict";

var Dialog = require('web.Dialog');
var testUtils = require('web.test_utils');
var Widget = require('web.Widget');

var ESCAPE_KEY = $.Event("keyup", { which: 27 });

async function createEmptyParent(debug) {
    var widget = new Widget();

    await testUtils.mock.addMockEnvironment(widget, {
        debug: debug || false,
    });
    return widget;
}

QUnit.module('core', {}, function () {

    QUnit.module('Dialog');

    QUnit.test("Closing custom dialog using buttons calls standard callback", async function (assert) {
        assert.expect(3);

        var testPromise = testUtils.makeTestPromiseWithAssert(assert, 'custom callback');
        var parent = await createEmptyParent();
        new Dialog(parent, {
            buttons: [
                {
                    text: "Close",
                    classes: 'btn-primary',
                    close: true,
                    click: testPromise.resolve,
                },
            ],
            $content: $('<main/>'),
            onForceClose: testPromise.reject,
        }).open();

        assert.verifySteps([]);

        await testUtils.nextTick();
        await testUtils.dom.click($('.modal[role="dialog"] .btn-primary'));

        testPromise.then(() => {
            assert.verifySteps(['ok custom callback']);
        });

        parent.destroy();
    });

    QUnit.test("Closing custom dialog without using buttons calls force close callback", async function (assert) {
        assert.expect(3);

        var testPromise = testUtils.makeTestPromiseWithAssert(assert, 'custom callback');
        var parent = await createEmptyParent();
        new Dialog(parent, {
            buttons: [
                {
                    text: "Close",
                    classes: 'btn-primary',
                    close: true,
                    click: testPromise.reject,
                },
            ],
            $content: $('<main/>'),
            onForceClose: testPromise.resolve,
        }).open();

        assert.verifySteps([]);

        await testUtils.nextTick();
        await testUtils.dom.triggerEvents($('.modal[role="dialog"]'), [ESCAPE_KEY]);

        testPromise.then(() => {
            assert.verifySteps(['ok custom callback']);
        });

        parent.destroy();
    });

    QUnit.test("Closing confirm dialog without using buttons calls cancel callback", async function (assert) {
        assert.expect(3);

        var testPromise = testUtils.makeTestPromiseWithAssert(assert, 'confirm callback');
        var parent = await createEmptyParent();
        var options = {
            confirm_callback: testPromise.reject,
            cancel_callback: testPromise.resolve,
        };
        Dialog.confirm(parent, "", options);

        assert.verifySteps([]);

        await testUtils.nextTick();
        await testUtils.dom.triggerEvents($('.modal[role="dialog"]'), [ESCAPE_KEY]);

        testPromise.then(() => {
            assert.verifySteps(['ok confirm callback']);
        });

        parent.destroy();
    });

    QUnit.test("Closing alert dialog without using buttons calls confirm callback", async function (assert) {
        assert.expect(3);

        var testPromise = testUtils.makeTestPromiseWithAssert(assert, 'alert callback');
        var parent = await createEmptyParent();
        var options = {
            confirm_callback: testPromise.resolve,
        };
        Dialog.alert(parent, "", options);

        assert.verifySteps([]);

        await testUtils.nextTick();
        await testUtils.dom.triggerEvents($('.modal[role="dialog"]'), [ESCAPE_KEY]);

        testPromise.then(() => {
            assert.verifySteps(['ok alert callback']);
        });

        parent.destroy();
    });
});

});

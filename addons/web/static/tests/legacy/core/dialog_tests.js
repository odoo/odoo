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

    QUnit.test("click twice on 'Ok' button of a confirm dialog", async function (assert) {
        assert.expect(5);

        var testPromise = testUtils.makeTestPromise();
        var parent = await createEmptyParent();
        var options = {
            confirm_callback: () => {
                assert.step("confirm");
                return testPromise;
            },
        };
        Dialog.confirm(parent, "", options);
        await testUtils.nextTick();

        assert.verifySteps([]);

        await testUtils.dom.click($('.modal[role="dialog"] .btn-primary'));
        await testUtils.dom.click($('.modal[role="dialog"] .btn-primary'));
        await testUtils.nextTick();
        assert.verifySteps(['confirm']);
        assert.ok($('.modal[role="dialog"]').hasClass('show'), "Should still be opened");
        testPromise.resolve();
        await testUtils.nextTick();
        assert.notOk($('.modal[role="dialog"]').hasClass('show'), "Should now be closed");

        parent.destroy();
    });

    QUnit.test("click on 'Cancel' and then 'Ok' in a confirm dialog", async function (assert) {
        assert.expect(3);

        var parent = await createEmptyParent();
        var options = {
            confirm_callback: () => {
                throw new Error("should not be called");
            },
            cancel_callback: () => {
                assert.step("cancel");
            }
        };
        Dialog.confirm(parent, "", options);
        await testUtils.nextTick();

        assert.verifySteps([]);

        testUtils.dom.click($('.modal[role="dialog"] footer button:not(.btn-primary)'));
        testUtils.dom.click($('.modal[role="dialog"] footer .btn-primary'));
        assert.verifySteps(['cancel']);

        parent.destroy();
    });

    QUnit.test("click on 'Cancel' and then 'Ok' in a confirm dialog (no cancel callback)", async function (assert) {
        assert.expect(2);

        var parent = await createEmptyParent();
        var options = {
            confirm_callback: () => {
                throw new Error("should not be called");
            },
            // Cannot add a step in cancel_callback, that's the point of this
            // test, we'll rely on checking the Dialog is opened then closed
            // without a crash.
        };
        Dialog.confirm(parent, "", options);
        await testUtils.nextTick();

        assert.ok($('.modal[role="dialog"]').hasClass('show'));
        testUtils.dom.click($('.modal[role="dialog"] footer button:not(.btn-primary)'));
        testUtils.dom.click($('.modal[role="dialog"] footer .btn-primary'));
        await testUtils.nextTick();
        assert.notOk($('.modal[role="dialog"]').hasClass('show'));

        parent.destroy();
    });

    QUnit.test("Confirm dialog callbacks properly handle rejections", async function (assert) {
        assert.expect(5);

        var parent = await createEmptyParent();
        var options = {
            confirm_callback: () => {
                assert.step("confirm");
                return Promise.reject();
            },
            cancel_callback: () => {
                assert.step("cancel");
                return $.Deferred().reject(); // Test jquery deferred too
            }
        };
        Dialog.confirm(parent, "", options);
        await testUtils.nextTick();

        assert.verifySteps([]);
        testUtils.dom.click($('.modal[role="dialog"] footer button:not(.btn-primary)'));
        await testUtils.nextTick();
        testUtils.dom.click($('.modal[role="dialog"] footer .btn-primary'));
        await testUtils.nextTick();
        testUtils.dom.click($('.modal[role="dialog"] footer button:not(.btn-primary)'));
        assert.verifySteps(['cancel', 'confirm', 'cancel']);

        parent.destroy();
    });

    QUnit.test("Properly can rely on the this in confirm and cancel callbacks of confirm dialog", async function (assert) {
        assert.expect(2);

        let dialogInstance = null;
        var parent = await createEmptyParent();
        var options = {
            confirm_callback: function () {
                assert.equal(this, dialogInstance, "'this' is properly a reference to the dialog instance");
                return Promise.reject();
            },
            cancel_callback: function () {
                assert.equal(this, dialogInstance, "'this' is properly a reference to the dialog instance");
                return Promise.reject();
            }
        };
        dialogInstance = Dialog.confirm(parent, "", options);
        await testUtils.nextTick();

        testUtils.dom.click($('.modal[role="dialog"] footer button:not(.btn-primary)'));
        await testUtils.nextTick();
        testUtils.dom.click($('.modal[role="dialog"] footer .btn-primary'));

        parent.destroy();
    });

    QUnit.test("Confirm dialog callbacks can return anything without crash", async function (assert) {
        assert.expect(3);
        // Note that this test could be removed in master if the related code
        // is reworked. This only prevents a stable fix to break this again by
        // relying on the fact what is returned by those callbacks are undefined
        // or promises.

        var parent = await createEmptyParent();
        var options = {
            confirm_callback: () => {
                assert.step("confirm");
                return 5;
            },
        };
        Dialog.confirm(parent, "", options);
        await testUtils.nextTick();

        assert.verifySteps([]);
        testUtils.dom.click($('.modal[role="dialog"] footer .btn-primary'));
        assert.verifySteps(['confirm']);

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

    QUnit.test("Ensure on_attach_callback and on_detach_callback are properly called", async function (assert) {
        assert.expect(4);

        const TestDialog = Dialog.extend({
            on_attach_callback() {
                assert.step('on_attach_callback');
            },
            on_detach_callback() {
                assert.step('on_detach_callback');
            },
        });

        const parent = await createEmptyParent();
        const dialog = new TestDialog(parent, {
            buttons: [
                {
                    text: "Close",
                    classes: 'btn-primary',
                    close: true,
                },
            ],
            $content: $('<main/>'),
        }).open();

        await dialog.opened();

        assert.verifySteps(['on_attach_callback']);

        await testUtils.dom.click($('.modal[role="dialog"] .btn-primary'));
        assert.verifySteps(['on_detach_callback']);

        parent.destroy();
    });

    QUnit.test("Should not be displayed if parent is destroyed while dialog is being opened", async function (assert) {
        assert.expect(1);
        const parent = await createEmptyParent();
        const dialog = new Dialog(parent);
        dialog.open();
        parent.destroy();
        await testUtils.nextTick();
        assert.containsNone(document.body, ".modal[role='dialog']");
    });
});

});

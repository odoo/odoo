odoo.define('web.notification_tests', function (require) {
"use strict";

var AbstractView = require('web.AbstractView');
var Notification = require('web.Notification');
var NotificationService = require('web.NotificationService');

var testUtils = require('web.test_utils');
var createView = testUtils.createView;

var waitCloseNotification = function () {
    return new Promise(function (resolve) {
        setTimeout(resolve, 1);
    });
}

QUnit.module('Services', {
    beforeEach: function () {
        // We need to use a delay above 0 ms because otherwise the notification will close right after it opens
        // before we can perform any test.
        testUtils.mock.patch(Notification, {
            _autoCloseDelay: 1,
            _animation: false,
        });
        this.viewParams = {
            View: AbstractView,
            arch: '<fake/>',
            data: {
            fake_model: {
                    fields: {},
                    record: [],
                },
            },
            model: 'fake_model',
            services: {
                notification: NotificationService,
            },
        };
    },
    afterEach: function () {
        // The Notification Service has a side effect: it adds a div inside
        // document.body.  We could implement a cleanup mechanism for services,
        // but this seems a little overkill since services are not supposed to
        // be destroyed anyway.
        $('.o_notification_manager').remove();
        testUtils.mock.unpatch(Notification);
    }
}, function () {
    QUnit.module('Notification');

    QUnit.test('Display a warning notification', async function (assert) {
        assert.expect(4);

        var view = await createView(this.viewParams);
        view.call('notification', 'notify', {
            title: 'a',
            message: 'b',
        });
        await testUtils.nextMicrotaskTick();
        var $notification = $('body .o_notification_manager .o_notification');
        assert.strictEqual($notification.html().trim().replace(/\s+/g, ' '),
            "<div class=\"toast-header\"> <span class=\"fa fa-2x mr-3 fa-lightbulb-o o_notification_icon\" role=\"img\" aria-label=\"Notification undefined\" title=\"Notification undefined\"></span> <div class=\"d-flex align-items-center mr-auto font-weight-bold o_notification_title\">a</div> <button type=\"button\" class=\"close o_notification_close\" data-dismiss=\"toast\" aria-label=\"Close\"> <span class=\"d-inline\" aria-hidden=\"true\">×</span> </button> </div> <div class=\"toast-body\"> <div class=\"mr-auto o_notification_content\">b</div> </div>",
            "should display notification");
        assert.containsOnce($notification, '.o_notification_close');
        await waitCloseNotification();
        assert.strictEqual($notification.is(':hidden'), true, "should hide the notification");
        assert.strictEqual($('body .o_notification_manager .o_notification').length, 0, "should destroy the notification");
        view.destroy();
    });

    QUnit.test('Display a danger notification', async function (assert) {
        assert.expect(1);

        var view = await createView(this.viewParams);
        view.call('notification', 'notify', {
            title: 'a',
            message: 'b',
            type: 'danger'
        });
        await testUtils.nextMicrotaskTick();
        var $notification = $('body .o_notification_manager .o_notification');
        assert.strictEqual($notification.html().trim().replace(/\s+/g, ' '),
            "<div class=\"toast-header\"> <span class=\"fa fa-2x mr-3 fa-exclamation o_notification_icon\" role=\"img\" aria-label=\"Notification undefined\" title=\"Notification undefined\"></span> <div class=\"d-flex align-items-center mr-auto font-weight-bold o_notification_title\">a</div> <button type=\"button\" class=\"close o_notification_close\" data-dismiss=\"toast\" aria-label=\"Close\"> <span class=\"d-inline\" aria-hidden=\"true\">×</span> </button> </div> <div class=\"toast-body\"> <div class=\"mr-auto o_notification_content\">b</div> </div>",
            "should display notification");
        view.destroy();
    });

    QUnit.test('Display a sticky notification', async function (assert) {
        assert.expect(3);

        var view = await createView(this.viewParams);
        view.call('notification', 'notify', {
            title: 'a',
            message: 'b',
            sticky: true,
        });
        await testUtils.nextTick();
        var $notification = $('body .o_notification_manager .o_notification');
        assert.containsOnce($notification, '.o_notification_close', "should display the close button in notification");

        assert.strictEqual($notification.is(':hidden'), false, "should not hide the notification automatically");
        await testUtils.dom.click($notification.find('.o_notification_close'));
        assert.strictEqual($('body .o_notification_manager .o_notification').length,
            0, "should destroy the notification");
        view.destroy();
    });

    QUnit.test('Display a notification without title', async function (assert) {
        assert.expect(3);

        const view = await createView(this.viewParams);
        view.call('notification', 'notify', {
            title: false,
            message: 'b',
            sticky: true,
        });
        await testUtils.nextTick();
        const $notification = $('body .o_notification_manager .o_notification');
        assert.containsNone($notification, '.toast-header .o_notification_title');
        assert.containsNone($notification, '.o_notification_icon');
        assert.containsOnce($notification, '.toast-body .o_notification_close');

        view.destroy();
    });

    // FIXME skip because the feature is unused and do not understand why the test even worked before
    QUnit.skip('Display a simple notification with onClose callback when automatically close', async function (assert) {
        assert.expect(2);

        var close = 0;
        var view = await createView(this.viewParams);
        view.call('notification', 'notify', {
            title: 'a',
            message: 'b',
            onClose: function () {
                close++;
            }
        });
        await testUtils.nextMicrotaskTick();
        view.destroy();
        assert.strictEqual(close, 0, "should wait to call onClose method once");
        await testUtils.nextTick();
        assert.strictEqual(close, 1, "should call onClose method once");
    });

    QUnit.test('Display a sticky notification with onClose callback', async function (assert) {
        assert.expect(2);

        testUtils.mock.unpatch(Notification);
        testUtils.mock.patch(Notification, {
            _autoCloseDelay: 2500,
            _animation: false,
        });
        var view = await createView(this.viewParams);

        var close = 0;
        view.call('notification', 'notify', {
            title: 'a',
            message: 'b',
            sticky: true,
            onClose: function () {
                close++;
            }
        });
        await testUtils.nextMicrotaskTick();
        assert.strictEqual(close, 0, "should wait to call onClose method once");
        testUtils.dom.click($('body .o_notification_manager .o_notification .o_notification_close'));
        assert.strictEqual(close, 1, "should call onClose method once");
        view.destroy();
    });

    QUnit.test('Display a question', async function (assert) {
        assert.expect(8);

        var view = await createView(this.viewParams);
        function notification (inc) {
            return {
                title: 'a' + inc,
                message: 'b' + inc,
                buttons: [
                    {
                        text: 'accept' + inc,
                        primary: true,
                        click: function () {
                            assert.step('accept' + inc);
                        },
                    },
                    {
                        text: 'refuse' + inc,
                        click: function () {
                            assert.step('refuse' + inc);
                        },
                    }
                ],
                onClose: function () {
                    assert.step('close' + inc);
                }
            };
        };
        view.call('notification', 'notify', notification(0));
        view.call('notification', 'notify', notification(1));
        view.call('notification', 'notify', notification(2));
        await testUtils.nextTick();

        var $notification = $('body .o_notification_manager .o_notification');
        assert.containsOnce($notification.eq(0), '.o_notification_close',
            "should display the close button in notification");
        assert.strictEqual($notification.html().trim().replace(/\s+/g, ' '),
            "<div class=\"toast-header\"> <span class=\"fa fa-2x mr-3 fa-question-circle-o o_notification_icon\" role=\"img\" aria-label=\"Notification undefined\" title=\"Notification undefined\"></span> <div class=\"d-flex align-items-center mr-auto font-weight-bold o_notification_title\">a0</div> <button type=\"button\" class=\"close o_notification_close\" data-dismiss=\"toast\" aria-label=\"Close\"> <span class=\"d-inline\" aria-hidden=\"true\">×</span> </button> </div> <div class=\"toast-body\"> <div class=\"mr-auto o_notification_content\">b0</div> <div class=\"mt-2 o_notification_buttons\"> <button type=\"button\" class=\"btn btn-sm btn-primary\"> <span>accept0</span> </button><button type=\"button\" class=\"btn btn-sm btn-secondary\"> <span>refuse0</span> </button> </div> </div>",
            "should display notification");

        testUtils.dom.click($notification.find('.o_notification_buttons button:contains(accept0)'));
        testUtils.dom.click($notification.find('.o_notification_buttons button:contains(refuse1)'));
        testUtils.dom.click($notification.eq(2).find('.o_notification_close'));

        assert.strictEqual($notification.is(':hidden'), true, "should hide the notification");
        assert.strictEqual($('body .o_notification_manager .o_notification').length,
            0, "should destroy the notification");
        assert.verifySteps(['accept0', 'refuse1', 'close2']);
        view.destroy();
    });

    QUnit.test('call close notification service', async function (assert) {
        assert.expect(2);

        testUtils.mock.unpatch(Notification);
        testUtils.mock.patch(Notification, {
            _autoCloseDelay: 2500,
            _animation: false,
        });
        var view = await createView(this.viewParams);

        var close = 0;
        var notificationId0 = view.call('notification', 'notify', {
            title: 'a',
            message: 'b',
            onClose: function () {
                close++;
            }
        });
        var notificationId1 = view.call('notification', 'notify', {
            title: 'a',
            message: 'b',
            sticky: true,
            onClose: function () {
                close++;
            }
        });
        await testUtils.nextTick();

        view.call('notification', 'close', notificationId0);
        view.call('notification', 'close', notificationId1);
        await testUtils.nextTick();

        assert.strictEqual($('body .o_notification_manager .o_notification').length, 0, "should destroy the notifications");
        assert.strictEqual(close, 2, "should call onClose method twice");
        view.destroy();
    });

    QUnit.test('Display a custom notification', async function (assert) {
        assert.expect(3);

        var Custom = Notification.extend({
            init: function (parent, params) {
                this._super.apply(this, arguments);
                assert.ok(params.customParams, 'instantiate custom notification');
            },
            start: function () {
                var self = this;
                return this._super().then(function () {
                    self.$el.html('Custom');
                });
            },
        });

        var view = await createView(this.viewParams);
        view.call('notification', 'notify', {
            Notification: Custom,
            customParams: true,
        });
        await testUtils.nextMicrotaskTick();
        assert.containsOnce($('body'), '.o_notification_manager .o_notification:contains(Custom)',
            "should display the notification");
        view.destroy();
        assert.containsNone($('body'), '.o_notification_manager .o_notification',
            "should destroy the notification");
    });

});});

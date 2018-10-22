odoo.define('web.notification_tests', function (require) {
"use strict";

var AbstractView = require('web.AbstractView');
var Notification = require('web.Notification');
var NotificationService = require('web.NotificationService');

var testUtils = require('web.test_utils');
var createView = testUtils.createView;


QUnit.module('Services', {
    beforeEach: function () {
        testUtils.patch(Notification, {
            _autoCloseDelay: 0,
            _animationDelay: 0,
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
        testUtils.unpatch(Notification);
    }
}, function () {
    QUnit.module('Notification');

    QUnit.test('Display a simple notification', function (assert) {
        var done = assert.async();
        assert.expect(4);

        var view = createView(this.viewParams);
        view.call('notification', 'notify', {
            title: 'a',
            message: 'b',
        });
        var $notification = $('body .o_notification_manager .o_notification');
        assert.strictEqual(_.str.trim($notification.html().replace(/\s+/g, ' ')),
            "<div class=\"o_notification_title\"> <span role=\"img\" aria-label=\"Notification undefined\" class=\"o_icon fa fa-3x fa-lightbulb-o\" title=\"Notification undefined\"></span> a </div> <div class=\"o_notification_content\">b</div>",
            "should display notification");
        assert.strictEqual($notification.find('.o_close').length, 0, "should not display the close button in ");
        setTimeout(function () {
            assert.strictEqual($notification.is(':hidden'), true, "should hide the notification");
            assert.strictEqual($('body .o_notification_manager .o_notification').length, 0, "should destroy the notification");
            view.destroy();
            done();
        });
    });

    QUnit.test('Display a warning', function (assert) {
        var done = assert.async();
        assert.expect(1);

        var view = createView(this.viewParams);
        view.call('notification', 'notify', {
            title: 'a',
            message: 'b',
            type: 'warning'
        });
        var $notification = $('body .o_notification_manager .o_notification');
        assert.strictEqual(_.str.trim($notification.html().replace(/\s+/g, ' ')),
            "<div class=\"o_notification_title\"> <span role=\"img\" aria-label=\"Notification undefined\" class=\"o_icon fa fa-3x fa-exclamation\" title=\"Notification undefined\"></span> a </div> <div class=\"o_notification_content\">b</div>",
            "should display notification");
        view.destroy();
        setTimeout(done);
    });

    QUnit.test('Display a sticky notification', function (assert) {
        var done = assert.async();
        assert.expect(3);

        var view = createView(this.viewParams);
        view.call('notification', 'notify', {
            title: 'a',
            message: 'b',
            sticky: true,
        });
        var $notification = $('body .o_notification_manager .o_notification');
        assert.strictEqual($notification.find('.o_close').length, 1, "should display the close button in notification");

        setTimeout(function () {
            assert.strictEqual($notification.is(':hidden'), false, "should not hide the notification automatically");
            $notification.find('.o_close').click();
            setTimeout(function () {
                assert.strictEqual($('body .o_notification_manager .o_notification').length, 0, "should destroy the notification");
                view.destroy();
                done();
            });
        });
    });

    QUnit.test('Display a simple notification with onClose callback when automatically close', function (assert) {
        var done = assert.async();
        assert.expect(2);

        var close = 0;
        var view = createView(this.viewParams);
        view.call('notification', 'notify', {
            title: 'a',
            message: 'b',
            onClose: function () {
                close++;
            }
        });
        view.destroy();
        assert.strictEqual(close, 0, "should wait to call onClose method once");
        setTimeout(function () {
            assert.strictEqual(close, 1, "should call onClose method once");
            done();
        });
    });

    QUnit.test('Display a sticky notification with onClose callback', function (assert) {
        var done = assert.async();
        assert.expect(2);

        testUtils.unpatch(Notification);
        testUtils.patch(Notification, {
            _autoCloseDelay: 2500,
            _animationDelay: 0,
        });
        var view = createView(this.viewParams);

        var close = 0;
        view.call('notification', 'notify', {
            title: 'a',
            message: 'b',
            sticky: true,
            onClose: function () {
                close++;
            }
        });
        assert.strictEqual(close, 0, "should wait to call onClose method once");
        $('body .o_notification_manager .o_notification .o_close').click();
        setTimeout(function () {
            assert.strictEqual(close, 1, "should call onClose method once");
            view.destroy();
            done();
        });
    });

    QUnit.test('Display a question', function (assert) {
        var done = assert.async();
        assert.expect(8);

        var view = createView(this.viewParams);
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

        var $notification = $('body .o_notification_manager .o_notification');
        assert.strictEqual($notification.eq(0).find('.o_close').length, 1, "should display the close button in notification");
        assert.strictEqual(_.str.trim($notification.eq(0).html().replace(/\s+/g, ' ')),
            "<a aria-label=\"Close\" class=\"fa fa-times o_close\" href=\"#\" title=\"Close\"></a> <div class=\"o_notification_title\"> <span role=\"img\" aria-label=\"Notification undefined\" class=\"o_icon fa fa-3x fa-question-circle-o\" title=\"Notification undefined\"></span> a0 </div> <div class=\"o_notification_content\">b0</div> <div class=\"o_buttons\"> <button class=\"btn btn-primary\" type=\"button\"> <span>accept0</span> </button><button class=\"btn btn-secondary\" type=\"button\"> <span>refuse0</span> </button> </div>",
            "should display notification");

        $notification.find('.o_buttons button:contains(accept0)').click();
        $notification.find('.o_buttons button:contains(accept0)').click();
        $notification.find('.o_buttons button:contains(refuse0)').click();
        $notification.eq(0).find('.o_close').click();

        $notification.find('.o_buttons button:contains(refuse1)').click();

        $notification.eq(2).find('.o_close').click();

        setTimeout(function () {
            assert.strictEqual($notification.is(':hidden'), true, "should hide the notification");
            assert.strictEqual($('body .o_notification_manager .o_notification').length, 0, "should destroy the notification");
            assert.verifySteps(['accept0', 'refuse1', 'close2']);
            view.destroy();
            done();
        });
    });

    QUnit.test('call close notification service', function (assert) {
        var done = assert.async();
        assert.expect(2);

        testUtils.unpatch(Notification);
        testUtils.patch(Notification, {
            _autoCloseDelay: 2500,
            _animationDelay: 0,
        });
        var view = createView(this.viewParams);

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

        view.call('notification', 'close', notificationId0);
        view.call('notification', 'close', notificationId1);

        setTimeout(function () {
            assert.strictEqual($('body .o_notification_manager .o_notification').length, 0, "should destroy the notifications");
            assert.strictEqual(close, 2, "should call onClose method twice");
            view.destroy();
            done();
        });
    });

    QUnit.test('Display a custom notification', function (assert) {
        var done = assert.async();
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

        var view = createView(this.viewParams);
        view.call('notification', 'notify', {
            Notification: Custom,
            customParams: true,
        });
        assert.strictEqual(
            $('body .o_notification_manager .o_notification:contains(Custom)').length, 1,
            "should display the notification");
        view.destroy();
        setTimeout(function () {
            assert.strictEqual(
                $('body .o_notification_manager .o_notification').length, 0,
                "should destroy the notification");
            done();
        });
    });

});});

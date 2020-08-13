odoo.define('mail_bot/static/src/components/messaging_menu/messaging_menu_tests.js', function (require) {
"use strict";

const {
    afterEach,
    afterNextRender,
    beforeEach,
    start,
} = require('mail/static/src/utils/test_utils.js');

QUnit.module('mail_bot', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('messaging_menu', {}, function () {
QUnit.module('messaging_menu_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.start = async params => {
            let { widget } = await start(Object.assign({}, params, {
                data: this.data,
                hasMessagingMenu: true,
            }));
            this.widget = widget;
        };
    },
    afterEach() {
        afterEach(this);
    },
});

QUnit.test('rendering with OdooBot has a request (default)', async function (assert) {
    assert.expect(4);

    await this.start({
        env: {
            browser: {
                Notification: {
                    permission: 'default',
                },
            },
        },
    });

    assert.ok(
        document.querySelector('.o_MessagingMenu_counter'),
        "should display a notification counter next to the messaging menu for OdooBot request"
    );
    assert.strictEqual(
        document.querySelector('.o_MessagingMenu_counter').textContent,
        "1",
        "should display a counter of '1' next to the messaging menu"
    );

    await afterNextRender(() =>
        document.querySelector('.o_MessagingMenu_toggler').click()
    );
    assert.containsOnce(
        document.body,
        '.o_NotificationRequest',
        "should display a notification in the messaging menu"
    );
    assert.strictEqual(
        document.querySelector('.o_NotificationRequest_name').textContent.trim(),
        'OdooBot has a request',
        "notification should display that OdooBot has a request"
    );
});

QUnit.test('rendering without OdooBot has a request (denied)', async function (assert) {
    assert.expect(2);

    await this.start({
        env: {
            browser: {
                Notification: {
                    permission: 'denied',
                },
            },
        },
    });

    assert.containsNone(
        document.body,
        '.o_MessagingMenu_counter',
        "should not display a notification counter next to the messaging menu"
    );

    await afterNextRender(() =>
        document.querySelector('.o_MessagingMenu_toggler').click()
    );
    assert.containsNone(
        document.body,
        '.o_NotificationRequest',
        "should display no notification in the messaging menu"
    );
});

QUnit.test('rendering without OdooBot has a request (accepted)', async function (assert) {
    assert.expect(2);

    await this.start({
        env: {
            browser: {
                Notification: {
                    permission: 'granted',
                },
            },
        },
    });

    assert.containsNone(
        document.body,
        '.o_MessagingMenu_counter',
        "should not display a notification counter next to the messaging menu"
    );

    await afterNextRender(() =>
        document.querySelector('.o_MessagingMenu_toggler').click()
    );
    assert.containsNone(
        document.body,
        '.o_NotificationRequest',
        "should display no notification in the messaging menu"
    );
});

QUnit.test('respond to notification prompt (denied)', async function (assert) {
    assert.expect(3);

    await this.start({
        env: {
            browser: {
                Notification: {
                    permission: 'default',
                    async requestPermission() {
                        this.permission = 'denied';
                        return this.permission;
                    },
                },
            },
        },
    });

    await afterNextRender(() =>
        document.querySelector('.o_MessagingMenu_toggler').click()
    );
    await afterNextRender(() =>
        document.querySelector('.o_NotificationRequest').click()
    );
    assert.containsOnce(
        document.body,
        '.toast .o_notification_content',
        "should display a toast notification with the deny confirmation"
    );
    assert.containsNone(
        document.body,
        '.o_MessagingMenu_counter',
        "should not display a notification counter next to the messaging menu"
    );

    await afterNextRender(() =>
        document.querySelector('.o_MessagingMenu_toggler').click()
    );
    assert.containsNone(
        document.body,
        '.o_NotificationRequest',
        "should display no notification in the messaging menu"
    );
});

});
});
});

});

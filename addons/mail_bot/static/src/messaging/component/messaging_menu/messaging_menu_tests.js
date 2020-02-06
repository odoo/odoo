odoo.define('mail_bot.messaging.component.MessagingMenuTests', function (require) {
"use strict";

const {
    afterEach: utilsAfterEach,
    afterNextRender,
    beforeEach: utilsBeforeEach,
    pause,
    start: utilsStart,
} = require('mail.messaging.testUtils');

QUnit.module('mail_bot', {}, function () {
QUnit.module('messaging', {}, function () {
QUnit.module('component', {}, function () {
QUnit.module('MessagingMenu', {
    beforeEach: function () {
        utilsBeforeEach(this);
        this.start = async params => {
            let { widget } = await utilsStart(Object.assign({}, params, {
                data: this.data,
                hasMessagingMenu: true,
            }));
            this.widget = widget;
        };
    },
    afterEach: function () {
        utilsAfterEach(this);
        if (this.widget) {
            this.widget.destroy();
        }
    },
});

QUnit.test('rendering with OdooBot has a request (default)', async function (assert) {
    assert.expect(4);

    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'channel_fetch_preview') {
                return [];
            }
            return this._super(...arguments);
        },
        'window.Notification': {
            permission: 'default',
        },
    });

    assert.ok(
        document.querySelector('.o_MessagingMenu_counter'),
        "should display a notification counter next to the messaging menu"
    );
    assert.strictEqual(
        document.querySelector('.o_MessagingMenu_counter').textContent,
        "1",
        "should display a counter of '1' next to the messaging menu"
    );

    document.querySelector('.o_MessagingMenu_toggler').click();
    await afterNextRender();
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
        async mockRPC(route, args) {
            if (args.method === 'channel_fetch_preview') {
                return [];
            }
            return this._super(...arguments);
        },
        'window.Notification': {
            permission: 'denied',
        },
    });

    assert.containsNone(
        document.body,
        '.o_MessagingMenu_counter',
        "should not display a notification counter next to the messaging menu"
    );

    document.querySelector('.o_MessagingMenu_toggler').click();
    await afterNextRender();
    assert.containsNone(
        document.body,
        '.o_NotificationRequest',
        "should display no notification in the messaging menu"
    );
});

QUnit.test('rendering without OdooBot has a request (accepted)', async function (assert) {
    assert.expect(2);

    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'channel_fetch_preview') {
                return [];
            }
            return this._super(...arguments);
        },
        'window.Notification': {
            permission: 'granted',
        },
    });

    assert.containsNone(
        document.body,
        '.o_MessagingMenu_counter',
        "should not display a notification counter next to the messaging menu"
    );

    document.querySelector('.o_MessagingMenu_toggler').click();
    await afterNextRender();
    assert.containsNone(
        document.body,
        '.o_NotificationRequest',
        "should display no notification in the messaging menu"
    );
});

QUnit.test('respond to notification prompt (denied)', async function (assert) {
    assert.expect(3);

    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'channel_fetch_preview') {
                return [];
            }
            return this._super(...arguments);
        },
        'window.Notification': {
            permission: 'default',
            async requestPermission() {
                this.permission = 'denied';
                return this.permission;
            },
        },
    });

    document.querySelector('.o_MessagingMenu_toggler').click();
    await afterNextRender();
    document.querySelector('.o_NotificationRequest').click();
    await afterNextRender();
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

    document.querySelector('.o_MessagingMenu_toggler').click();
    await afterNextRender();
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

odoo.define('mail_bot.messaging.widget.NotificationAlertTests', function (require) {
'use strict';

const {
    afterEach: utilsAfterEach,
    afterNextRender,
    beforeEach: utilsBeforeEach,
    pause,
    start,
} = require('mail.messaging.testUtils');

const FormView = require('web.FormView');

QUnit.module('mail_bot', {}, function () {
QUnit.module('messaging', {}, function () {
QUnit.module('widget', {}, function () {
QUnit.module('NotificationAlert', {
    beforeEach() {
        utilsBeforeEach(this);
        this.start = async params => {
            let { widget } = await start(Object.assign({
                data: this.data,
                hasView: true,
                // View params
                View: FormView,
                model: 'mail.message',
                arch: `
                    <form>
                        <widget name="notification_alert"/>
                    </form>
                `,
            }, params));
            this.widget = widget;
        };
    },
    afterEach() {
        utilsAfterEach(this);
        if (this.widget) {
            this.widget.destroy();
            this.widget = undefined;
        }
    },
});

QUnit.test('notification_alert widget: display blocked notification alert', async function (assert) {
    assert.expect(1);

    await afterNextRender(async () => {
        await this.start({
            env: {
                window: {
                    Notification: {
                        permission: 'denied',
                    },
                },
            },
        });
    });

    assert.containsOnce(
        document.body,
        '.o_notification_alert',
        "Blocked notification alert should be displayed"
    );
});

QUnit.test('notification_alert widget: no notification alert when granted', async function (assert) {
    assert.expect(1);

    await afterNextRender(async () => {
        await this.start({
            env: {
                window: {
                    Notification: {
                        permission: 'granted',
                    },
                },
            },
        });
    });

    assert.containsNone(
        document.body,
        '.o_notification_alert',
        "Blocked notification alert should not be displayed"
    );
});

QUnit.test('notification_alert widget: no notification alert when default', async function (assert) {
    assert.expect(1);

    await afterNextRender(async () => {
        await this.start({
            env: {
                window: {
                    Notification: {
                        permission: 'default',
                    },
                },
            },
        });
    });

    assert.containsNone(
        document.body,
        '.o_notification_alert',
        "Blocked notification alert should not be displayed"
    );
});

});
});
});

});

/** @odoo-module **/

import { beforeEach, start } from '@mail/utils/test_utils';

import FormView from 'web.FormView';

QUnit.module('mail', {}, function () {
QUnit.module('widgets', {}, function () {
QUnit.module('notification_alert_tests.js', {
    async beforeEach() {
        await beforeEach(this);
    },
});

QUnit.skip('notification_alert widget: display blocked notification alert', async function (assert) {
    // FIXME: Test should work, but for some reasons OWL always flags the
    // component as not mounted, even though it is in the DOM and it's state
    // is good for rendering... task-227947
    assert.expect(1);

    await start({
        arch: `
            <form>
                <widget name="notification_alert"/>
            </form>
        `,
        data: this.data,
        env: {
            browser: {
                Notification: {
                    permission: 'denied',
                },
            },
        },
        hasView: true,
        model: 'mail.message',
        // View params
        View: FormView,
    });

    assert.containsOnce(
        document.body,
        '.o_notification_alert',
        "Blocked notification alert should be displayed"
    );
});

QUnit.test('notification_alert widget: no notification alert when granted', async function (assert) {
    assert.expect(1);

    await start({
        arch: `
            <form>
                <widget name="notification_alert"/>
            </form>
        `,
        data: this.data,
        env: {
            browser: {
                Notification: {
                    permission: 'granted',
                },
            },
        },
        hasView: true,
        model: 'mail.message',
        // View params
        View: FormView,
    });

    assert.containsNone(
        document.body,
        '.o_notification_alert',
        "Blocked notification alert should not be displayed"
    );
});

QUnit.test('notification_alert widget: no notification alert when default', async function (assert) {
    assert.expect(1);

    await start({
        arch: `
            <form>
                <widget name="notification_alert"/>
            </form>
        `,
        data: this.data,
        env: {
            browser: {
                Notification: {
                    permission: 'default',
                },
            },
        },
        hasView: true,
        model: 'mail.message',
        // View params
        View: FormView,
    });

    assert.containsNone(
        document.body,
        '.o_notification_alert',
        "Blocked notification alert should not be displayed"
    );
});

});
});

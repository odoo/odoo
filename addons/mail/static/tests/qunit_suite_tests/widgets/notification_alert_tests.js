/** @odoo-module **/

import { start } from '@mail/../tests/helpers/test_utils';

import { browser } from '@web/core/browser/browser';
import { patchWithCleanup } from "@web/../tests/helpers/utils";

QUnit.module('mail', {}, function () {
QUnit.module('widgets', {}, function () {
QUnit.module('notification_alert_tests.js');

QUnit.test('notification_alert widget: display blocked notification alert', async function (assert) {
    assert.expect(1);

    const views = {
        'mail.message,false,form': `<form><widget name="notification_alert"/></form>`,
    };
    patchWithCleanup(browser, {
        Notification: {
            ...browser.Notification,
            permission: 'denied',
        },
    });
    const { openView } = await start({
        serverData: { views },
    });
    await openView({
        res_model: 'mail.message',
        views: [[false, 'form']],
    });

    assert.containsOnce(
        document.body,
        '.o_NotificationAlert',
        "Blocked notification alert should be displayed"
    );
});

QUnit.test('notification_alert widget: no notification alert when granted', async function (assert) {
    assert.expect(1);

    const views = {
        'mail.message,false,form': `<form><widget name="notification_alert"/></form>`,
    };
    patchWithCleanup(browser, {
        Notification: {
            permission: 'granted',
        },
    });
    const { openView } = await start({
        serverData: { views },
    });
    await openView({
        res_model: 'mail.message',
        views: [[false, 'form']],
    });

    assert.containsNone(
        document.body,
        '.o_NotificationAlert',
        "Blocked notification alert should not be displayed"
    );
});

QUnit.test('notification_alert widget: no notification alert when default', async function (assert) {
    assert.expect(1);

    const views = {
        'mail.message,false,form': `<form><widget name="notification_alert"/></form>`,
    };
    patchWithCleanup(browser, {
        Notification: {
            permission: 'default',
        },
    });
    const { openView } = await start({
        serverData: { views },
    });
    await openView({
        res_model: 'mail.message',
        views: [[false, 'form']],
    });

    assert.containsNone(
        document.body,
        '.o_NotificationAlert',
        "Blocked notification alert should not be displayed"
    );
});

});
});

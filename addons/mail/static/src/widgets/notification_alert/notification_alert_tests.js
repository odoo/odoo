odoo.define('mail/static/src/widgets/notification_alert/notification_alert_tests.js', function (require) {
'use strict';

const { afterEach, beforeEach, start } = require('mail/static/src/utils/test_utils.js');

const FormView = require('web.FormView');

QUnit.module('mail', {}, function () {
QUnit.module('widgets', {}, function () {
QUnit.module('notification_alert', {}, function () {
QUnit.module('notification_alert_tests.js', {
    beforeEach() {
        beforeEach(this);

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
        afterEach(this);
    },
});

QUnit.skip('notification_alert widget: display blocked notification alert', async function (assert) {
    // FIXME: Test should work, but for some reasons OWL always flags the
    // component as not mounted, even though it is in the DOM and it's state
    // is good for rendering... task-227947
    assert.expect(1);

    await this.start({
        env: {
            browser: {
                Notification: {
                    permission: 'denied',
                },
            },
        },
    });

    assert.containsOnce(
        document.body,
        '.o_notification_alert',
        "Blocked notification alert should be displayed"
    );
});

QUnit.test('notification_alert widget: no notification alert when granted', async function (assert) {
    assert.expect(1);

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
        '.o_notification_alert',
        "Blocked notification alert should not be displayed"
    );
});

QUnit.test('notification_alert widget: no notification alert when default', async function (assert) {
    assert.expect(1);

    await this.start({
        env: {
            browser: {
                Notification: {
                    permission: 'default',
                },
            },
        },
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

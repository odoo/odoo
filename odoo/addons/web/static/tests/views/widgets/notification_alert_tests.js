/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

const viewData = {
    type: "form",
    resModel: "partner",
    serverData: {
        models: {
            partner: {
                records: [
                    {
                        id: 1,
                    },
                ],
            },
        },
    },
    resId: 1,
    arch: `<form><widget name="notification_alert"/></form>`,
};

QUnit.module("Widgets", (hooks) => {
    hooks.beforeEach(setupViewRegistries);

    QUnit.module("NotificationAlert");

    QUnit.test(
        "notification alert should be displayed when notification denied",
        async function (assert) {
            assert.expect(1);

            patchWithCleanup(browser, { Notification: { permission: "denied" } });
            await makeView(viewData);
            assert.containsOnce(
                document.body,
                ".o_widget_notification_alert .alert",
                "notification alert should be displayed when notification denied"
            );
        }
    );

    QUnit.test(
        "notification alert should not be displayed when notification granted",
        async function (assert) {
            assert.expect(1);

            patchWithCleanup(browser, { Notification: { permission: "granted" } });
            await makeView(viewData);
            assert.containsNone(
                document.body,
                ".o_widget_notification_alert .alert",
                "notification alert should not be displayed when notification granted"
            );
        }
    );

    QUnit.test(
        "notification alert should not be displayed when notification default",
        async function (assert) {
            assert.expect(1);

            patchWithCleanup(browser, { Notification: { permission: "default" } });
            await makeView(viewData);
            assert.containsNone(
                document.body,
                ".o_widget_notification_alert .alert",
                "notification alert should not be displayed when notification default"
            );
        }
    );
});

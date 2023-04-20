/* @odoo-module */

import { busService } from "@bus/services/bus_service";
import { busParametersService } from "@bus/bus_parameters_service";
import { multiTabService } from "@bus/multi_tab_service";
import { simpleNotificationService } from "@bus/simple_notification_service";
import { getPyEnv } from "@bus/../tests/helpers/mock_python_environment";

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { createWebClient } from "@web/../tests/webclient/helpers";

const serviceRegistry = registry.category("services");

QUnit.module("simple_notification", {
    beforeEach() {
        serviceRegistry.add("bus_service", busService);
        serviceRegistry.add("bus.parameters", busParametersService);
        serviceRegistry.add("multi_tab", multiTabService);
        serviceRegistry.add("simple_notification", simpleNotificationService);
    },
});

QUnit.test("receive and display simple notification with message", async (assert) => {
    await createWebClient({});
    const pyEnv = await getPyEnv();
    const { afterNextRender } = owl.App;
    await afterNextRender(() => {
        pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "simple_notification", {
            message: "simple notification",
        });
    });
    assert.strictEqual($(".o_notification_content").text(), "simple notification");
});

QUnit.test("receive and display simple notification with title", async (assert) => {
    await createWebClient({});
    const pyEnv = await getPyEnv();
    const { afterNextRender } = owl.App;
    await afterNextRender(() => {
        pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "simple_notification", {
            message: "simple notification",
            title: "simple title",
        });
    });
    assert.strictEqual($(".o_notification_title").text(), "simple title");
});

QUnit.test("receive and display simple notification with specific type", async (assert) => {
    await createWebClient({});
    const pyEnv = await getPyEnv();
    const { afterNextRender } = owl.App;
    await afterNextRender(() => {
        pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "simple_notification", {
            message: "simple notification",
            type: "info",
        });
    });
    assert.containsOnce($, ".o_notification.border-info");
});

QUnit.test("receive and display simple notification as sticky", async (assert) => {
    await createWebClient({});
    const pyEnv = await getPyEnv();
    const { afterNextRender } = owl.App;
    patchWithCleanup(browser, {
        setTimeout(fn) {
            /**
             * Sticky notifications are removed after a delay. If the notification is still
             * present when this delay is set to 0 it means it is a sticky one.
             */
            return this._super(fn, 0);
        },
    });
    await afterNextRender(() => {
        pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "simple_notification", {
            message: "simple notification",
            sticky: true,
        });
    });
    assert.containsOnce($, ".o_notification");
});

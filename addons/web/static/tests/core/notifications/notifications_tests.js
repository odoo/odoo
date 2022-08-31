/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { notificationService } from "@web/core/notifications/notification_service";
import { registry } from "@web/core/registry";
import { makeTestEnv } from "../../helpers/mock_env";
import { click, getFixture, mount, nextTick, patchWithCleanup } from "../../helpers/utils";

const { markup } = owl;

let target;
const serviceRegistry = registry.category("services");

QUnit.module("Notifications", {
    async beforeEach() {
        target = getFixture();
        serviceRegistry.add("notification", notificationService);
        patchWithCleanup(browser, { setTimeout: () => 1 });
    },
});

QUnit.test("can display a basic notification", async (assert) => {
    const env = await makeTestEnv({ serviceRegistry });
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    const notifService = env.services.notification;
    await mount(NotificationContainer, target, { env, props });

    notifService.add("I'm a basic notification");
    await nextTick();
    assert.containsOnce(target, ".o_notification");
    const notif = target.querySelector(".o_notification");
    assert.strictEqual(
        notif.querySelector(".o_notification_content").textContent,
        "I'm a basic notification"
    );
    assert.hasClass(notif, "border-warning");
});

QUnit.test("can display a notification with a className", async (assert) => {
    const env = await makeTestEnv({ serviceRegistry });
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    const notifService = env.services.notification;
    await mount(NotificationContainer, target, { env, props });

    notifService.add("I'm a basic notification", { className: "abc" });
    await nextTick();
    assert.containsOnce(target, ".o_notification.abc");
});

QUnit.test("title and message are escaped by default", async (assert) => {
    const env = await makeTestEnv({ serviceRegistry });
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    const notifService = env.services.notification;
    await mount(NotificationContainer, target, { env, props });

    notifService.add("<i>Some message</i>", { title: "<b>Some title</b>" });
    await nextTick();
    assert.containsOnce(target, ".o_notification");
    const notif = target.querySelector(".o_notification");
    assert.strictEqual(
        notif.querySelector(".o_notification_title").textContent,
        "<b>Some title</b>"
    );
    assert.strictEqual(
        notif.querySelector(".o_notification_content").textContent,
        "<i>Some message</i>"
    );
});

QUnit.test("can display a notification with markup content", async (assert) => {
    const env = await makeTestEnv({ serviceRegistry });
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    const notifService = env.services.notification;
    await mount(NotificationContainer, target, { env, props });

    notifService.add(markup("<b>I'm a <i>markup</i> notification</b>"));
    await nextTick();
    assert.containsOnce(target, ".o_notification");
    const notif = target.querySelector(".o_notification");
    assert.strictEqual(
        notif.querySelector(".o_notification_content").innerHTML,
        "<b>I'm a <i>markup</i> notification</b>"
    );
});

QUnit.test("can display a notification of type danger", async (assert) => {
    const env = await makeTestEnv({ serviceRegistry });
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    const notifService = env.services.notification;
    await mount(NotificationContainer, target, { env, props });

    notifService.add("I'm a danger notification", { type: "danger" });
    await nextTick();
    assert.containsOnce(target, ".o_notification");
    const notif = target.querySelector(".o_notification");
    assert.strictEqual(
        notif.querySelector(".o_notification_content").textContent,
        "I'm a danger notification"
    );
    assert.hasClass(notif, "border-danger");
});

QUnit.test("can display a danger notification with a title", async (assert) => {
    const env = await makeTestEnv({ serviceRegistry });
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    const notifService = env.services.notification;
    await mount(NotificationContainer, target, { env, props });

    notifService.add("I'm a danger notification", { title: "Some title", type: "danger" });
    await nextTick();
    assert.containsOnce(target, ".o_notification");
    const notif = target.querySelector(".o_notification");
    assert.strictEqual(notif.querySelector(".o_notification_title").textContent, "Some title");
    assert.strictEqual(
        notif.querySelector(".o_notification_content").textContent,
        "I'm a danger notification"
    );
    assert.hasClass(notif, "border-danger");
});

QUnit.test("can display a notification with a button", async (assert) => {
    const env = await makeTestEnv({ serviceRegistry });
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    const notifService = env.services.notification;
    await mount(NotificationContainer, target, { env, props });

    notifService.add("I'm a notification with button", {
        buttons: [
            {
                name: "I'm a button",
                primary: true,
                onClick: () => {
                    assert.step("Button clicked");
                },
            },
        ],
    });
    await nextTick();
    assert.containsOnce(target, ".o_notification");
    const notif = target.querySelector(".o_notification");
    assert.strictEqual(notif.querySelector(".o_notification_buttons").textContent, "I'm a button");
    await click(notif, ".btn-primary");
    assert.verifySteps(["Button clicked"]);
    assert.containsOnce(
        target,
        ".o_notification",
        "Clicking on a button shouldn't close automatically the notification"
    );
});

QUnit.test("can display a notification with a callback when closed", async (assert) => {
    const env = await makeTestEnv({ serviceRegistry });
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    const notifService = env.services.notification;
    await mount(NotificationContainer, target, { env, props });

    notifService.add("I'm a sticky notification", {
        sticky: true,
        onClose: () => {
            assert.step("Notification closed");
        },
    });
    await nextTick();
    assert.containsOnce(target, ".o_notification");

    // close by clicking on the close icon
    await click(target, ".o_notification .o_notification_close");
    assert.verifySteps(["Notification closed"]);
    assert.containsNone(target, ".o_notification");
});

QUnit.test("notifications aren't sticky by default", async (assert) => {
    let timeoutCB;
    patchWithCleanup(browser, {
        setTimeout: (cb) => {
            timeoutCB = cb;
            return 1;
        },
    });

    const env = await makeTestEnv({ serviceRegistry });
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    const notifService = env.services.notification;
    await mount(NotificationContainer, target, { env, props });

    notifService.add("I'm a notification");
    await nextTick();
    assert.containsOnce(target, ".o_notification");
    timeoutCB(); // should close the notification
    await nextTick();
    assert.containsNone(target, ".o_notification");
});

QUnit.test("can display a sticky notification", async (assert) => {
    patchWithCleanup(browser, {
        setTimeout: () => {
            throw new Error("Should not register a callback for sticky notifications");
        },
    });
    const env = await makeTestEnv({ browser, serviceRegistry });
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    const notifService = env.services.notification;
    await mount(NotificationContainer, target, { env, props });

    notifService.add("I'm a sticky notification", { sticky: true });
    await nextTick();
    assert.containsOnce(target, ".o_notification");
});

QUnit.test("can close sticky notification", async (assert) => {
    const env = await makeTestEnv({ serviceRegistry });
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    const notifService = env.services.notification;
    await mount(NotificationContainer, target, { env, props });

    const closeNotif = notifService.add("I'm a sticky notification", { sticky: true });
    await nextTick();
    assert.containsOnce(target, ".o_notification");

    // close programmatically
    closeNotif();
    await nextTick();
    assert.containsNone(target, ".o_notification");

    notifService.add("I'm a sticky notification", { sticky: true });
    await nextTick();
    assert.containsOnce(target, ".o_notification");

    // close by clicking on the close icon
    await click(target, ".o_notification .o_notification_close");
    assert.containsNone(target, ".o_notification");
});

// The timeout have to be done by the one that uses the notification service
QUnit.skip("can close sticky notification with wait", async (assert) => {
    let timeoutCB;
    patchWithCleanup(browser, {
        setTimeout: (cb, t) => {
            timeoutCB = cb;
            assert.step("time: " + t);
            return 1;
        },
    });
    const env = await makeTestEnv({ serviceRegistry });
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    const notifService = env.services.notification;
    await mount(NotificationContainer, target, { env, props });

    const id = notifService.create("I'm a sticky notification", { sticky: true });
    await nextTick();
    assert.containsOnce(target, ".o_notification");

    // close programmatically
    notifService.close(id, 3000);
    await nextTick();
    assert.containsOnce(target, ".o_notification");
    // simulate end of timeout
    timeoutCB();
    await nextTick();
    assert.containsNone(target, ".o_notification");
    assert.verifySteps(["time: 3000"]);
});

QUnit.test("can close a non-sticky notification", async (assert) => {
    let timeoutCB;
    patchWithCleanup(browser, {
        setTimeout: (cb) => {
            timeoutCB = cb;
            return 1;
        },
    });
    const env = await makeTestEnv({ serviceRegistry });
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    const notifService = env.services.notification;
    await mount(NotificationContainer, target, { env, props });

    const closeNotif = notifService.add("I'm a sticky notification");
    await nextTick();
    assert.containsOnce(target, ".o_notification");

    // close the notification
    closeNotif();
    await nextTick();
    assert.containsNone(target, ".o_notification");

    // simulate end of timeout, which should try to close the notification as well
    timeoutCB();
    await nextTick();
    assert.containsNone(target, ".o_notification");
});

QUnit.test("close a non-sticky notification while another one remains", async (assert) => {
    let timeoutCB;
    patchWithCleanup(browser, {
        setTimeout: (cb) => {
            timeoutCB = cb;
            return 1;
        },
    });
    const env = await makeTestEnv({ serviceRegistry });
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    const notifService = env.services.notification;
    await mount(NotificationContainer, target, { env, props });

    const closeNotif1 = notifService.add("I'm a non-sticky notification");
    const closeNotif2 = notifService.add("I'm a sticky notification", { sticky: true });
    await nextTick();
    assert.containsN(target, ".o_notification", 2);

    // close the non sticky notification
    closeNotif1();
    await nextTick();
    assert.containsOnce(target, ".o_notification");

    // simulate end of timeout, which should try to close notification 1 as well
    timeoutCB();
    await nextTick();
    assert.containsOnce(target, ".o_notification");

    // close the non sticky notification
    closeNotif2();
    await nextTick();
    assert.containsNone(target, ".o_notification");
});

QUnit.test("notification coming when NotificationManager not mounted yet", async (assert) => {
    const env = await makeTestEnv({ serviceRegistry });
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    const notifService = env.services.notification;
    mount(NotificationContainer, target, { env, props });

    notifService.add("I'm a non-sticky notification");
    await nextTick();
    assert.containsOnce(target, ".o_notification");
});

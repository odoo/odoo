import { expect, queryRect, test } from "@odoo/hoot";
import { click, hover, leave, waitFor } from "@odoo/hoot-dom";
import { advanceTime, animationFrame, runAllTimers } from "@odoo/hoot-mock";
import { markup } from "@odoo/owl";
import { getService, makeMockEnv, mountWithCleanup } from "@web/../tests/web_test_helpers";

import { registry } from "@web/core/registry";

test("can display a basic notification", async () => {
    await makeMockEnv();
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    await mountWithCleanup(NotificationContainer, { props, noMainContainer: true });
    getService("notification").add("I'm a basic notification");
    await animationFrame();
    expect(".o_notification").toHaveCount(1);
    expect(".o_notification_content").toHaveText("I'm a basic notification");
    expect(".o_notification_bar").toHaveClass("bg-warning");
});

test("can display a notification with a className", async () => {
    await makeMockEnv();
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    await mountWithCleanup(NotificationContainer, { props, noMainContainer: true });
    getService("notification").add("I'm a basic notification", { className: "abc" });
    await animationFrame();
    expect(".o_notification.abc").toHaveCount(1);
});

test("message are escaped by default", async () => {
    await makeMockEnv();
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    await mountWithCleanup(NotificationContainer, { props, noMainContainer: true });
    getService("notification").add("<i>Some message</i>");
    await animationFrame();
    expect(".o_notification").toHaveCount(1);
    expect(".o_notification_content").toHaveText("<i>Some message</i>");
});

test("can display a notification with markup content", async () => {
    await makeMockEnv();
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    await mountWithCleanup(NotificationContainer, { props, noMainContainer: true });
    getService("notification").add(markup`<b>I'm a <i>markup</i> notification</b>`);
    await animationFrame();
    expect(".o_notification").toHaveCount(1);
    expect(".o_notification_content").toHaveInnerHTML("<b>I'm a <i>markup</i> notification</b>");
});

test("can display a notification with title and markup content", async () => {
    await makeMockEnv();
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    await mountWithCleanup(NotificationContainer, { props, noMainContainer: true });
    getService("notification").add(markup`<b>I'm a <i>markup</i> notification</b>`, {
        title: "I'm a title",
    });
    await animationFrame();
    expect(".o_notification").toHaveCount(1);
    expect(".o_notification_content").toHaveInnerHTML(
        "I'm a title. <b>I'm a <i>markup</i> notification</b>"
    );
    expect(".o_notification_content").toHaveText("I'm a title. I'm a markup notification");
});

test("can display a notification of type danger", async () => {
    await makeMockEnv();
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    await mountWithCleanup(NotificationContainer, { props, noMainContainer: true });
    getService("notification").add("I'm a danger notification", { type: "danger" });
    await animationFrame();
    expect(".o_notification").toHaveCount(1);
    expect(".o_notification_content").toHaveText("I'm a danger notification");
    expect(".o_notification_bar").toHaveClass("bg-danger");
});

test("can display a notification with a button", async () => {
    await makeMockEnv();
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    await mountWithCleanup(NotificationContainer, { props, noMainContainer: true });
    getService("notification").add("I'm a notification with button", {
        buttons: [
            {
                name: "I'm a button",
                onClick: () => {
                    expect.step("Button clicked");
                },
            },
        ],
    });
    await animationFrame();
    expect(".o_notification").toHaveCount(1);
    expect(".o_notification_buttons").toHaveText("I'm a button");
    await click(".o_notification .btn-link");
    await animationFrame();
    expect.verifySteps(["Button clicked"]);
    expect(".o_notification").toHaveCount(1);
});

test("can display a notification with a callback when closed", async () => {
    await makeMockEnv();
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    await mountWithCleanup(NotificationContainer, { props, noMainContainer: true });
    getService("notification").add("I'm a sticky notification", {
        sticky: true,
        onClose: () => {
            expect.step("Notification closed");
        },
    });
    await animationFrame();
    expect(".o_notification").toHaveCount(1);
    await click(".o_notification .o_notification_close");
    await animationFrame();
    expect.verifySteps(["Notification closed"]);
    expect(".o_notification").toHaveCount(0);
});

test("notifications aren't sticky by default", async () => {
    await makeMockEnv();
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    await mountWithCleanup(NotificationContainer, { props, noMainContainer: true });
    getService("notification").add("I'm a notification");
    await animationFrame();
    expect(".o_notification").toHaveCount(1);
    // Wait for the notification to close
    await advanceTime(4000);
    await animationFrame();
    expect(".o_notification").toHaveCount(0);
});

test("can display a sticky notification", async () => {
    await makeMockEnv();
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    await mountWithCleanup(NotificationContainer, { props, noMainContainer: true });
    getService("notification").add("I'm a sticky notification", { sticky: true });
    await animationFrame();
    expect(".o_notification").toHaveCount(1);
    await advanceTime(5000);
    await animationFrame();
    expect(".o_notification").toHaveCount(1);
});

test("can close sticky notification", async () => {
    await makeMockEnv();
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    await mountWithCleanup(NotificationContainer, { props, noMainContainer: true });
    const closeNotif = getService("notification").add("I'm a sticky notification", {
        sticky: true,
    });
    await animationFrame();
    expect(".o_notification").toHaveCount(1);

    // close programmatically
    closeNotif();
    await animationFrame();
    expect(".o_notification").toHaveCount(0);

    getService("notification").add("I'm a sticky notification", { sticky: true });
    await animationFrame();
    expect(".o_notification").toHaveCount(1);

    // close by clicking on the close icon
    await click(".o_notification .o_notification_close");
    await animationFrame();
    expect(".o_notification").toHaveCount(0);
});

// The timeout have to be done by the one that uses the notification service
test.skip("can close sticky notification with wait", async () => {
    await makeMockEnv();
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    await mountWithCleanup(NotificationContainer, { props, noMainContainer: true });
    const closeNotif = getService("notification").add("I'm a sticky notification", {
        sticky: true,
    });
    await animationFrame();
    expect(".o_notification").toHaveCount(1);

    // close programmatically
    getService("notification").close(closeNotif, 3000);
    await animationFrame();
    expect(".o_notification").toHaveCount(1);

    // simulate end of timeout
    await advanceTime(3000);
    await animationFrame();
    expect(".o_notification").toHaveCount(0);
});

test("can close a non-sticky notification", async () => {
    await makeMockEnv();
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    await mountWithCleanup(NotificationContainer, { props, noMainContainer: true });
    const closeNotif = getService("notification").add("I'm a sticky notification");
    await animationFrame();
    expect(".o_notification").toHaveCount(1);

    // close the notification
    closeNotif();
    await animationFrame();
    expect(".o_notification").toHaveCount(0);

    // simulate end of timeout, which should try to close the notification as well
    await runAllTimers();
    expect(".o_notification").toHaveCount(0);
});

test.tags("desktop");
test("can refresh the duration of a non-sticky notification", async () => {
    await makeMockEnv();
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    await mountWithCleanup(NotificationContainer, { props, noMainContainer: true });
    getService("notification").add("I'm a first non-sticky notification");
    getService("notification").add("I'm a second non-sticky notification");
    await animationFrame();
    expect(".o_notification").toHaveCount(2);

    await advanceTime(3000);
    await hover(".o_notification:first-child");
    await advanceTime(5000);
    // hovered notification should be visible as long as mouse is over
    expect(".o_notification").toHaveCount(1);
    await leave();
    await advanceTime(3000);
    // notification should be refreshed in duration (4000 ms)
    expect(".o_notification").toHaveCount(1);
    await advanceTime(2000);
    expect(".o_notification").toHaveCount(0);
});

test("close a non-sticky notification while another one remains", async () => {
    await makeMockEnv();
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    await mountWithCleanup(NotificationContainer, { props, noMainContainer: true });
    const closeNotif1 = getService("notification").add("I'm a non-sticky notification");
    const closeNotif2 = getService("notification").add("I'm a sticky notification", {
        sticky: true,
    });
    await animationFrame();
    expect(".o_notification").toHaveCount(2);

    // close the non sticky notification
    closeNotif1();
    await animationFrame();
    expect(".o_notification").toHaveCount(1);

    // simulate end of timeout, which should try to close notification 1 as well
    await runAllTimers();
    expect(".o_notification").toHaveCount(1);

    // close the non sticky notification
    closeNotif2();
    await animationFrame();
    expect(".o_notification").toHaveCount(0);
});

test("notification coming when NotificationManager not mounted yet", async () => {
    await makeMockEnv();
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    mountWithCleanup(NotificationContainer, { props, noMainContainer: true });
    getService("notification").add("I'm a non-sticky notification");
    await animationFrame();
    expect(".o_notification").toHaveCount(1);
});

test("notification autocloses after a specified delay", async () => {
    await makeMockEnv();
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");

    await mountWithCleanup(NotificationContainer, { props, noMainContainer: true });
    getService("notification").add("custom autoclose delay notification", {
        autocloseDelay: 1000,
    });

    await waitFor(".o_notification");
    await advanceTime(500);
    await animationFrame();
    expect(".o_notification").toHaveCount(1);

    await advanceTime(500);
    await animationFrame();
    expect(".o_notification").toHaveCount(0);
});

test("no spam notifications", async () => {
    await makeMockEnv();
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");

    await mountWithCleanup(NotificationContainer, { props, noMainContainer: true });
    getService("notification").add("my notification");
    getService("notification").add("my notification");
    getService("notification").add("my notification");
    getService("notification").add("my notification");
    getService("notification").add("my notification");
    await waitFor(".o_notification");

    expect(".o_notification").toHaveCount(1);
});

test("no spam markup'd notifications", async () => {
    await makeMockEnv();
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");

    await mountWithCleanup(NotificationContainer, { props, noMainContainer: true });
    getService("notification").add(markup("<i>my notification</i>"));
    getService("notification").add(markup("<i>my notification</i>"));
    getService("notification").add(markup("<i>my notification</i>"));
    getService("notification").add(markup("<i>my notification</i>"));
    getService("notification").add(markup("<i>my notification</i>"));
    await waitFor(".o_notification");

    expect(".o_notification").toHaveCount(1);
});

test.tags("mobile");
test("notification must be on the bottom of the screen in mobile", async () => {
    await makeMockEnv();
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    await mountWithCleanup(NotificationContainer, { props, noMainContainer: true });
    getService("notification").add("I'm a basic notification");
    await animationFrame();

    const notificationManagerRect = queryRect(".o_notification_manager");
    const viewportHeight = Math.max(
        document.documentElement.clientHeight || 0,
        window.innerHeight || 0
    );

    // $o-navbar-height (46px) x 0.25 = 11.5
    // we use 15 to have a buffer in case of inconsistent browser computation
    expect(viewportHeight - notificationManagerRect.bottom).toBeLessThan(15);
});

test.tags("mobile");
test("notification with multilines must be limited to 2 lines in mobile", async () => {
    await makeMockEnv();
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    await mountWithCleanup(NotificationContainer, { props, noMainContainer: true });

    getService("notification").add("I'm a basic notification");
    await animationFrame();
    const contentOneLineHeight = queryRect(".o_notification_content").height;
    await click(".o_notification .o_notification_close");
    await animationFrame();

    getService("notification").add("I'm a basic notification".repeat(3));
    await animationFrame();
    const contentTwoLineHeight = queryRect(".o_notification_content").height;
    await click(".o_notification .o_notification_close");
    await animationFrame();

    expect(contentTwoLineHeight).toBeGreaterThan(contentOneLineHeight);
    expect(contentTwoLineHeight).toBeLessThan(contentOneLineHeight * 3);

    getService("notification").add("I'm a basic notification".repeat(10));
    await animationFrame();
    const contentOverflowHeight = queryRect(".o_notification_content").height;
    expect(Math.abs(contentOverflowHeight - contentTwoLineHeight)).toBeWithin(0, 1);
});

test.tags("mobile");
test("notification with button on mobile", async () => {
    await makeMockEnv();
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    await mountWithCleanup(NotificationContainer, { props, noMainContainer: true });

    getService("notification").add("I'm a basic notification", {
        buttons: [{ name: "I'm a button", onClick: () => {} }],
    });
    await animationFrame();
    // Check if both the text and the button are on the same line
    expect(
        Math.abs(queryRect(".o_notification_content").bottom - queryRect(".o_notification_buttons").bottom)
    ).toBeWithin(0, 1);
    await click(".o_notification .o_notification_close");
    await animationFrame();

    getService("notification").add("I'm a basic notification", {
        buttons: [{ name: "I'm a button with a longer text", onClick: () => {} }],
    });
    await animationFrame();
    const notificationBodyRect = queryRect(".o_notification_body");
    const contentRect = queryRect(".o_notification_content");
    const buttonsRect = queryRect(".o_notification_buttons");
    // Check if the button is below the text and aligned on the right
    expect(buttonsRect.top - contentRect.bottom).toBeWithin(0, 1);
    expect(Math.abs(notificationBodyRect.right - buttonsRect.right)).toBeLessThan(1);
});

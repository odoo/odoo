import { test, expect } from "@odoo/hoot";
import { animationFrame, advanceTime, runAllTimers } from "@odoo/hoot-mock";
import { click, queryOne } from "@odoo/hoot-dom";
import { markup } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { mountWithCleanup, makeMockEnv, getService } from "@web/../tests/web_test_helpers";

test("can display a basic notification", async () => {
    await makeMockEnv();
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    await mountWithCleanup(NotificationContainer, { props, noMainContainer: true });
    await getService("notification").add("I'm a basic notification");
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
    await getService("notification").add("I'm a basic notification", { className: "abc" });
    await animationFrame();
    expect(".o_notification.abc").toHaveCount(1);
});

test("title and message are escaped by default", async () => {
    await makeMockEnv();
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    await mountWithCleanup(NotificationContainer, { props, noMainContainer: true });
    await getService("notification").add("<i>Some message</i>", { title: "<b>Some title</b>" });
    await animationFrame();
    expect(".o_notification").toHaveCount(1);
    expect(".o_notification_title").toHaveText("<b>Some title</b>");
    expect(".o_notification_content").toHaveText("<i>Some message</i>");
});

test("can display a notification with markup content", async () => {
    await makeMockEnv();
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    await mountWithCleanup(NotificationContainer, { props, noMainContainer: true });
    await getService("notification").add(markup("<b>I'm a <i>markup</i> notification</b>"));
    await animationFrame();
    expect(".o_notification").toHaveCount(1);
    expect(queryOne(".o_notification_content").innerHTML).toBe(
        "<b>I'm a <i>markup</i> notification</b>"
    );
});

test("can display a notification of type danger", async () => {
    await makeMockEnv();
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    await mountWithCleanup(NotificationContainer, { props, noMainContainer: true });
    await getService("notification").add("I'm a danger notification", { type: "danger" });
    await animationFrame();
    expect(".o_notification").toHaveCount(1);
    expect(".o_notification_content").toHaveText("I'm a danger notification");
    expect(".o_notification_bar").toHaveClass("bg-danger");
});

test("can display a danger notification with a title", async () => {
    await makeMockEnv();
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    await mountWithCleanup(NotificationContainer, { props, noMainContainer: true });
    await getService("notification").add("I'm a danger notification", {
        title: "Some title",
        type: "danger",
    });
    await animationFrame();
    expect(".o_notification").toHaveCount(1);
    expect(".o_notification_title").toHaveText("Some title");
    expect(".o_notification_content").toHaveText("I'm a danger notification");
    expect(".o_notification_bar").toHaveClass("bg-danger");
});

test("can display a notification with a button", async () => {
    await makeMockEnv();
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    await mountWithCleanup(NotificationContainer, { props, noMainContainer: true });
    await getService("notification").add("I'm a notification with button", {
        buttons: [
            {
                name: "I'm a button",
                primary: true,
                onClick: () => {
                    expect.step("Button clicked");
                },
            },
        ],
    });
    await animationFrame();
    expect(".o_notification").toHaveCount(1);
    expect(".o_notification_buttons").toHaveText("I'm a button");
    click(".o_notification .btn-primary");
    await animationFrame();
    expect(["Button clicked"]).toVerifySteps();
    expect(".o_notification").toHaveCount(1);
});

test("can display a notification with a callback when closed", async () => {
    await makeMockEnv();
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    await mountWithCleanup(NotificationContainer, { props, noMainContainer: true });
    await getService("notification").add("I'm a sticky notification", {
        sticky: true,
        onClose: () => {
            expect.step("Notification closed");
        },
    });
    await animationFrame();
    expect(".o_notification").toHaveCount(1);
    click(".o_notification .o_notification_close");
    await animationFrame();
    expect(["Notification closed"]).toVerifySteps();
    expect(".o_notification").toHaveCount(0);
});

test("notifications aren't sticky by default", async () => {
    await makeMockEnv();
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    await mountWithCleanup(NotificationContainer, { props, noMainContainer: true });
    await getService("notification").add("I'm a notification");
    await animationFrame();
    expect(".o_notification").toHaveCount(1);
    // Wait for the notification to close
    await runAllTimers();
    await animationFrame();
    expect(".o_notification").toHaveCount(0);
});

test("can display a sticky notification", async () => {
    await makeMockEnv();
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    await mountWithCleanup(NotificationContainer, { props, noMainContainer: true });
    await getService("notification").add("I'm a sticky notification", { sticky: true });
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
    const closeNotif = await getService("notification").add("I'm a sticky notification", {
        sticky: true,
    });
    await animationFrame();
    expect(".o_notification").toHaveCount(1);

    // close programmatically
    closeNotif();
    await animationFrame();
    expect(".o_notification").toHaveCount(0);

    await getService("notification").add("I'm a sticky notification", { sticky: true });
    await animationFrame();
    expect(".o_notification").toHaveCount(1);

    // close by clicking on the close icon
    click(".o_notification .o_notification_close");
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
    const id = await getService("notification").add("I'm a sticky notification", { sticky: true });
    await animationFrame();
    expect(".o_notification").toHaveCount(1);

    // close programmatically
    await getService("notification").close(id, 3000);
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
    const closeNotif = await getService("notification").add("I'm a sticky notification");
    await animationFrame();
    expect(".o_notification").toHaveCount(1);

    // close the notification
    closeNotif();
    await animationFrame();
    expect(".o_notification").toHaveCount(0);

    // simulate end of timeout, which should try to close the notification as well
    await runAllTimers();
    await animationFrame();
    expect(".o_notification").toHaveCount(0);
});

test("can refresh the duration of a non-sticky notification", async () => {
    await makeMockEnv();
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    await mountWithCleanup(NotificationContainer, { props, noMainContainer: true });
    await getService("notification").add("I'm a first non-sticky notification");
    await getService("notification").add("I'm a second non-sticky notification");
    await animationFrame();
    expect(".o_notification").toHaveCount(2);

    await advanceTime(3000);
    queryOne(".o_notification:first-child").dispatchEvent(new Event("mouseenter"));
    await advanceTime(5000);
    await animationFrame();
    // Both notifications should be visible as long as mouse is over one of them
    expect(".o_notification").toHaveCount(2);
    queryOne(".o_notification:first-child").dispatchEvent(new Event("mouseleave"));
    await advanceTime(3000);
    await animationFrame();
    // Both notifications should be refreshed in duration (4000 ms)
    expect(".o_notification").toHaveCount(2);
    await advanceTime(2000);
    await animationFrame();
    expect(".o_notification").toHaveCount(0);
});

test("close a non-sticky notification while another one remains", async () => {
    await makeMockEnv();
    const { Component: NotificationContainer, props } = registry
        .category("main_components")
        .get("NotificationContainer");
    await mountWithCleanup(NotificationContainer, { props, noMainContainer: true });
    const closeNotif1 = await getService("notification").add("I'm a non-sticky notification");
    const closeNotif2 = await getService("notification").add("I'm a sticky notification", {
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
    await animationFrame();
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
    await getService("notification").add("I'm a non-sticky notification");
    await animationFrame();
    expect(".o_notification").toHaveCount(1);
});

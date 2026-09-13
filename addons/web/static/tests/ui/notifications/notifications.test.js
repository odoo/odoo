// @ts-check

import { expect, onError, test } from "@odoo/hoot";
import { click, hover, leave, queryOne, waitFor } from "@odoo/hoot-dom";
import { advanceTime, animationFrame, runAllTimers } from "@odoo/hoot-mock";
import { Component, markup, xml } from "@odoo/owl";
import {
    getService,
    makeMockEnv,
    mountWithCleanup,
} from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";
import { MainComponentsContainer } from "@web/ui/main_components_container";
import { NotificationContainer } from "@web/ui/notification/notification_container";
import { notificationService } from "@web/ui/notification/notification_service";
import { OverlayContainer } from "@web/ui/overlay/overlay_container";
import { serviceBackedItems } from "@web/ui/service_backed_items";

test("onClose can destroy the service and create a replacement without closing twice", async () => {
    const {
        services: { notification },
    } = await makeMockEnv();
    let calls = 0;
    const close = notification.add("first", {
        onClose: () => {
            if (++calls === 1) {
                notification.destroy();
                notification.add("replacement", { sticky: true });
            }
        },
    });
    close();
    expect(calls).toBe(1);
    expect(
        Object.values(notification.notifications).map((entry) => entry.props.message),
    ).toEqual(["replacement"]);
});

test("closing a notification is reentrant and invokes onClose once", async () => {
    const env = await makeMockEnv();
    let calls = 0;
    const close = env.services.notification.add("reentrant", {
        onClose: () => {
            calls++;
            if (calls === 1) {
                close();
            }
        },
    });
    close();
    close();
    expect(calls).toBe(1);
    expect(Object.keys(env.services.notification.notifications)).toHaveLength(0);
});

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
    expect(".o_notification_content").toHaveInnerHTML(
        "<b>I'm a <i>markup</i> notification</b>",
    );
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
        "I'm a title. <b>I'm a <i>markup</i> notification</b>",
    );
    expect(".o_notification_content").toHaveText(
        "I'm a title. I'm a markup notification",
    );
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

    closeNotif();
    await animationFrame();
    expect(".o_notification").toHaveCount(0);

    getService("notification").add("I'm a sticky notification", { sticky: true });
    await animationFrame();
    expect(".o_notification").toHaveCount(1);

    await click(".o_notification .o_notification_close");
    await animationFrame();
    expect(".o_notification").toHaveCount(0);
});

test("the notification service exposes no close entry point", async () => {
    await makeMockEnv();

    const service = getService("notification");
    expect(Reflect.get(service, "close")).toBe(undefined);
    for (const name of ["add", "notifications", "destroy"]) {
        expect(service[name]).not.toBe(undefined);
    }
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

    closeNotif();
    await animationFrame();
    expect(".o_notification").toHaveCount(0);

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
    expect(".o_notification").toHaveCount(1);
    await leave();
    await advanceTime(3000);
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

    closeNotif1();
    await animationFrame();
    expect(".o_notification").toHaveCount(1);

    await runAllTimers();
    expect(".o_notification").toHaveCount(1);

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

test("a notification that fails to render does not kill later notifications", async () => {
    expect.errors(1);
    onError((error) =>
        expect.step(/** @type {PromiseRejectionEvent} */ (error).reason.message),
    );

    await makeMockEnv();
    await mountWithCleanup(MainComponentsContainer);

    // @ts-expect-error
    getService("notification").add("faulty", { buttons: "not-a-list" });
    await animationFrame();
    await animationFrame();
    expect.verifySteps([
        "Invalid props for component 'Notification': 'buttons' is not a list of objects",
    ]);
    expect.verifyErrors([
        "Invalid props for component 'Notification': 'buttons' is not a list of objects",
    ]);

    getService("notification").add("I still work");
    await animationFrame();
    expect(".o_notification").toHaveCount(1);
    expect(".o_notification_content").toHaveText("I still work");
});

test("a throwing onClose is reported instead of propagating to the closer", async () => {
    expect.errors(1);
    onError((error) =>
        expect.step(/** @type {PromiseRejectionEvent} */ (error).reason.message),
    );

    await makeMockEnv();
    await mountWithCleanup(MainComponentsContainer);

    const close = getService("notification").add("fragile", {
        onClose: () => {
            throw new Error("onClose boom");
        },
    });
    await animationFrame();
    expect(".o_notification").toHaveCount(1);

    close();
    expect.step("close returned");
    await animationFrame();
    expect(".o_notification").toHaveCount(0, {
        message: "the notification is gone despite its throwing onClose",
    });
    expect.verifySteps(["close returned", "onClose boom"]);
    expect.verifyErrors(["onClose boom"]);
});

test("an unrecognised option does not cost the caller their notification", async () => {
    await mountWithCleanup(MainComponentsContainer);

    getService("notification").add("first");
    await animationFrame();
    expect(".o_notification").toHaveCount(1);

    // @ts-expect-error
    getService("notification").add("second", { notAnOption: true });
    await animationFrame();
    await animationFrame();
    expect(".o_notification").toHaveCount(2);
});

test("known options still reach the notification", async () => {
    await mountWithCleanup(MainComponentsContainer);
    getService("notification").add("styled", {
        type: "success",
        className: "o_custom_notif",
        sticky: true,
        title: "Heads up",
    });
    await animationFrame();
    expect(".o_notification.o_custom_notif").toHaveCount(1);
    expect(".o_notification_bar.bg-success").toHaveCount(1);
    expect(".o_notification").toHaveText(/Heads up/);
});

test("a subclassed container still receives its own extra props", async () => {
    class CustomNotification extends Component {
        static template = xml`<div class="o_custom_notif" t-esc="props.flavour"/>`;
        static props = {
            message: { type: String },
            flavour: { type: String },
            className: { type: String, optional: true },
            close: { type: Function },
        };
    }
    class CustomContainer extends NotificationContainer {
        static serviceName = "custom_notification";
        static notificationComponent = CustomNotification;
        static components = {
            ...NotificationContainer.components,
            Notification: CustomNotification,
        };
    }
    const customService = {
        ...notificationService,
        notificationContainer: CustomContainer,
        notificationContainerKey: "CustomNotificationContainer",
    };
    registry.category("services").add("custom_notification", customService);

    const env = await makeMockEnv();
    await mountWithCleanup(MainComponentsContainer, { env });

    env.services.custom_notification.add("hello", { flavour: "mango" });
    await animationFrame();
    expect(".o_custom_notif").toHaveCount(1);
    expect(".o_custom_notif").toHaveText("mango");
});

test("a second env's notifications reach that env's own container", async () => {
    const firstEnv = await makeMockEnv();
    const secondEnv = await makeMockEnv();
    expect(firstEnv.services.notification.notifications).not.toBe(
        secondEnv.services.notification.notifications,
    );

    await mountWithCleanup(MainComponentsContainer, { env: secondEnv });
    secondEnv.services.notification.add("from the second env");
    await animationFrame();
    expect(".o_notification").toHaveCount(1);
    expect(".o_notification_content").toHaveText("from the second env");
});

test("the main_components entry is the same object across env starts", async () => {
    await makeMockEnv();
    const entry = registry.category("main_components").get("NotificationContainer");
    await makeMockEnv();
    expect(registry.category("main_components").get("NotificationContainer")).toBe(
        entry,
    );
    expect(entry.props).toBe(undefined);
});

test("a container whose service is not started says so", async () => {
    class OrphanContainer extends NotificationContainer {
        static serviceName = "not_a_service";
    }
    const container = Object.create(OrphanContainer.prototype);
    container.env = await makeMockEnv();
    let message = "";
    try {
        serviceBackedItems(container, undefined);
    } catch (error) {
        message = error.message;
    }
    expect(message).toInclude("OrphanContainer");
    expect(message).toInclude("not_a_service");
});

test("the same lookup answers for the overlay container, and for a prop", async () => {
    const container = Object.create(OverlayContainer.prototype);
    container.env = await makeMockEnv();
    expect(() => serviceBackedItems(container, undefined)).not.toThrow();

    const handed = {};
    expect(serviceBackedItems(container, handed)).toBe(handed);
});

test("destroy() runs the onClose of every still-open notification", async () => {
    const env = await makeMockEnv();
    env.services.notification.add("sticky one", {
        sticky: true,
        onClose: () => expect.step("closed:1"),
    });
    env.services.notification.add("sticky two", {
        sticky: true,
        onClose: () => expect.step("closed:2"),
    });
    expect(Object.keys(env.services.notification.notifications)).toHaveLength(2);

    env.services.notification.destroy();

    expect.verifySteps(["closed:1", "closed:2"]);
    expect(Object.keys(env.services.notification.notifications)).toHaveLength(0);
});

test("focusing a notification pauses its auto-close", async () => {
    await makeMockEnv();
    await mountWithCleanup(MainComponentsContainer);
    getService("notification").add("hello");
    await animationFrame();
    expect(".o_notification").toHaveCount(1);

    queryOne(".o_notification .o_notification_close").focus();
    await advanceTime(6000);
    await animationFrame();
    expect(".o_notification").toHaveCount(1);

    queryOne(".o_notification .o_notification_close").blur();
    await advanceTime(6000);
    await animationFrame();
    expect(".o_notification").toHaveCount(0);
});

test("releasing the pointer does not resume a notification still focused", async () => {
    await makeMockEnv();
    await mountWithCleanup(MainComponentsContainer);
    getService("notification").add("hello");
    await animationFrame();

    await hover(".o_notification");
    queryOne(".o_notification .o_notification_close").focus();
    await leave();
    await advanceTime(6000);
    await animationFrame();
    expect(".o_notification").toHaveCount(1);
});

test("moving focus inside a notification keeps it paused", async () => {
    await makeMockEnv();
    await mountWithCleanup(MainComponentsContainer);
    getService("notification").add("hello", {
        buttons: [{ name: "Undo", onClick: () => {} }],
    });
    await animationFrame();

    queryOne(".o_notification .o_notification_close").focus();
    queryOne(".o_notification_buttons button").focus();
    await advanceTime(6000);
    await animationFrame();
    expect(".o_notification").toHaveCount(1);
});

test("a container must declare the component it renders notifications with", async () => {
    class Orphan extends NotificationContainer {
        static serviceName = "orphan_notification";
        static notificationComponent = undefined;
    }
    let message = "";
    try {
        notificationService.start.call({
            ...notificationService,
            notificationContainer: Orphan,
            notificationContainerKey: "OrphanNotificationContainer",
        });
    } catch (error) {
        message = error.message;
    }
    expect(message).toInclude("notificationComponent");
});

test("a mouseleave with no matching mouseenter does not extend the countdown", async () => {
    await makeMockEnv();
    await mountWithCleanup(MainComponentsContainer);
    getService("notification").add("hello", { autocloseDelay: 4000 });
    await animationFrame();
    expect(".o_notification").toHaveCount(1);

    await advanceTime(2000);
    await animationFrame();
    expect(".o_notification").toHaveCount(1);

    queryOne(".o_notification").dispatchEvent(
        new MouseEvent("mouseleave", { relatedTarget: document.body }),
    );
    await animationFrame();

    await advanceTime(2100);
    await animationFrame();
    expect(".o_notification").toHaveCount(0);
});

test("a lone mouseleave does not release a hold taken by focus", async () => {
    await makeMockEnv();
    await mountWithCleanup(MainComponentsContainer);
    getService("notification").add("hello", { autocloseDelay: 4000 });
    await animationFrame();

    queryOne(".o_notification .o_notification_close").focus();
    queryOne(".o_notification").dispatchEvent(
        new MouseEvent("mouseleave", { relatedTarget: document.body }),
    );
    await animationFrame();

    await advanceTime(6000);
    await animationFrame();
    expect(".o_notification").toHaveCount(1);
});

test.tags("desktop");
test("a real hover still pauses and resumes the countdown", async () => {
    await makeMockEnv();
    await mountWithCleanup(MainComponentsContainer);
    getService("notification").add("hello", { autocloseDelay: 4000 });
    await animationFrame();

    await hover(".o_notification");
    await advanceTime(6000);
    await animationFrame();
    expect(".o_notification").toHaveCount(1);

    await leave();
    await advanceTime(4100);
    await animationFrame();
    expect(".o_notification").toHaveCount(0);
});

test("a caller cannot take over the service-owned props", async () => {
    await makeMockEnv();
    await mountWithCleanup(MainComponentsContainer);
    getService("notification").add("real message", {
        // @ts-ignore hostile on purpose
        close: () => expect.step("hijacked close"),
        // @ts-ignore hostile on purpose
        message: "hijacked message",
    });
    await animationFrame();
    expect(".o_notification_content").toHaveText("real message");

    await click(".o_notification_close");
    await animationFrame();
    expect(".o_notification").toHaveCount(0);
    expect.verifySteps([]);
});

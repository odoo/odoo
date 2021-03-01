/** @odoo-module **/
import { notificationService } from "../../src/notifications/notification_service";
import { Registry } from "../../src/core/registry";
import { click, getFixture, makeTestEnv, mount, nextTick } from "../helpers/index";
import { NotificationContainer } from "../../src/notifications/notification_container";
let target;
let browser;
let serviceRegistry;

QUnit.module("Notifications", {
  async beforeEach() {
    target = getFixture();
    serviceRegistry = new Registry();
    serviceRegistry.add(notificationService.name, notificationService);
    browser = { setTimeout: () => 1 };
  },
});

QUnit.test("can display a basic notification", async (assert) => {
  const env = await makeTestEnv({ browser, serviceRegistry });
  const notifService = env.services.notifications;
  await mount(NotificationContainer, { env, target });

  notifService.create("I'm a basic notification");
  await nextTick();
  assert.containsOnce(target, ".o_notification");
  const notif = target.querySelector(".o_notification");
  assert.strictEqual(notif.innerText, "I'm a basic notification");
  assert.hasClass(notif, "bg-warning");
});

QUnit.test("can display a notification of type danger", async (assert) => {
  const env = await makeTestEnv({ browser, serviceRegistry });
  const notifService = env.services.notifications;
  await mount(NotificationContainer, { env, target });

  notifService.create("I'm a danger notification", { type: "danger" });
  await nextTick();
  assert.containsOnce(target, ".o_notification");
  const notif = target.querySelector(".o_notification");
  assert.strictEqual(notif.innerText, "I'm a danger notification");
  assert.hasClass(notif, "bg-danger");
});

QUnit.test("can display a danger notification with a title", async (assert) => {
  const env = await makeTestEnv({ browser, serviceRegistry });
  const notifService = env.services.notifications;
  await mount(NotificationContainer, { env, target });
  
  notifService.create("I'm a danger notification", { title: "Some title", type: "danger" });
  await nextTick();
  assert.containsOnce(target, ".o_notification");
  const notif = target.querySelector(".o_notification");
  assert.strictEqual(notif.querySelector(".o_notification_header").innerText, "Some title");
  assert.strictEqual(
    notif.querySelector(".o_notification_body").innerText,
    "I'm a danger notification"
  );
  assert.hasClass(notif, "bg-danger");
  assert.hasClass(notif.querySelector(".o_notification_icon"), "fa-exclamation");
});

QUnit.test("notifications aren't sticky by default", async (assert) => {
  let timeoutCB;
  browser.setTimeout = (cb) => {
    timeoutCB = cb;
    return 1;
  };
  const env = await makeTestEnv({ browser, serviceRegistry });
  const notifService = env.services.notifications;
  await mount(NotificationContainer, { env, target });

  notifService.create("I'm a notification");
  await nextTick();
  assert.containsOnce(target, ".o_notification");
  timeoutCB(); // should close the notification
  await nextTick();
  assert.containsNone(target, ".o_notification");
});

QUnit.test("can display a sticky notification", async (assert) => {
  browser.setTimeout = () => {
    throw new Error("Should not register a callback for sticky notifications");
    return 1;
  };
  const env = await makeTestEnv({ browser, serviceRegistry });
  const notifService = env.services.notifications;
  await mount(NotificationContainer, { env, target });

  notifService.create("I'm a sticky notification", { sticky: true });
  await nextTick();
  assert.containsOnce(target, ".o_notification");
});

QUnit.test("can close sticky notification", async (assert) => {
  const env = await makeTestEnv({ browser, serviceRegistry });
  const notifService = env.services.notifications;
  await mount(NotificationContainer, { env, target });

  let id = notifService.create("I'm a sticky notification", { sticky: true });
  await nextTick();
  assert.containsOnce(target, ".o_notification");

  // close programmatically
  notifService.close(id);
  await nextTick();
  assert.containsNone(target, ".o_notification");
  
  id = notifService.create("I'm a sticky notification", { sticky: true });
  await nextTick();
  assert.containsOnce(target, ".o_notification");
  
  // close by clicking on the close icon
  await click(target, ".o_notification .o_notification_close");
  assert.containsNone(target, ".o_notification");
});

QUnit.test("can close a non-sticky notification", async (assert) => {
  let timeoutCB;
  browser.setTimeout = (cb) => {
    timeoutCB = cb;
    return 1;
  };
  const env = await makeTestEnv({ browser, serviceRegistry });
  const notifService = env.services.notifications;
  await mount(NotificationContainer, { env, target });

  const id = notifService.create("I'm a sticky notification");
  await nextTick();
  assert.containsOnce(target, ".o_notification");

  // close the notification
  notifService.close(id);
  await nextTick();
  assert.containsNone(target, ".o_notification");

  // simulate end of timeout, which should try to close the notification as well
  timeoutCB();
  await nextTick();
  assert.containsNone(target, ".o_notification");
});

QUnit.test("close a non-sticky notification while another one remains", async (assert) => {
  let timeoutCB;
  browser.setTimeout = (cb) => {
    timeoutCB = cb;
    return 1;
  };
  const env = await makeTestEnv({ browser, serviceRegistry });
  const notifService = env.services.notifications;
  await mount(NotificationContainer, { env, target });

  const id1 = notifService.create("I'm a non-sticky notification");
  const id2 = notifService.create("I'm a sticky notification", { sticky: true });
  await nextTick();
  assert.containsN(target, ".o_notification", 2);
  
  // close the non sticky notification
  notifService.close(id1);
  await nextTick();
  assert.containsOnce(target, ".o_notification");
  
  // simulate end of timeout, which should try to close notification 1 as well
  timeoutCB();
  await nextTick();
  assert.containsOnce(target, ".o_notification");
  
  // close the non sticky notification
  notifService.close(id2);
  await nextTick();
  assert.containsNone(target, ".o_notification");
});

QUnit.test("notification coming when NotificationManager not mounted yet", async (assert) => {
  const env = await makeTestEnv({ browser, serviceRegistry });
  const notifService = env.services.notifications;
  mount(NotificationContainer, { env, target });
  
  notifService.create("I'm a non-sticky notification");
  await nextTick();
  assert.containsOnce(target, ".o_notification");
});

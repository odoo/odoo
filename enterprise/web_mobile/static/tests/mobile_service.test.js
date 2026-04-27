import { expect, test } from "@odoo/hoot";
import { getService, mockService, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { WebClient } from "@web/webclient/webclient";

test("test Reader Loop", async () => {
    mockService("mobile", {
        enableReader: () => expect.step("enableReader"),
        stopReader: () => expect.step("stopReader"),
    });

    const eventName = "test_event";
    const listener1 = () => expect.step("listener1");
    const listener2 = () => expect.step("listener2");

    await mountWithCleanup(WebClient);
    const eventBus = await getService("mobile").bus;

    // No callback should be call at the initialization
    expect.verifySteps([]);

    eventBus.trigger(eventName, {});
    // No callback should be call if no listener
    expect.verifySteps([]);

    eventBus.addEventListener(eventName, listener1);
    // enableReader should be call at first listener
    expect.verifySteps(["enableReader"]);

    eventBus.trigger(eventName, {});
    // No callback should be call when an event is trigger
    expect.verifySteps(["listener1"]);

    eventBus.addEventListener(eventName, listener2);
    eventBus.trigger(eventName, {});
    // No callback should be call if one listener is already present and another one is added
    expect.verifySteps(["listener1", "listener2"]);

    eventBus.removeEventListener(eventName, listener1);
    eventBus.trigger(eventName, {});
    // No callback should be call if there is at least one listener and another one is removed
    expect.verifySteps(["listener2"]);

    eventBus.removeEventListener(eventName, listener2);
    // stopReader should be call if there is no listeners anymore
    expect.verifySteps(["stopReader"]);

    eventBus.trigger(eventName, {});
    // No callback should be call if no listener
    expect.verifySteps([]);
});

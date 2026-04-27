import { expect, test } from "@odoo/hoot";

import { HookEventBus } from "@web_mobile/js/hook_event_bus";

test("HookEventBus: Test callback", async () => {
    const eventBus = new HookEventBus({
        onAddListener: () => expect.step("onAddListenerCallback"),
        onRemoveListener: () => expect.step("onRemoveListenerCallback"),
    });

    const eventName = "test_event";
    const listener1 = () => expect.step("listener1");
    const listener2 = () => expect.step("listener2");

    // No callback should be call at the initialization
    expect.verifySteps([]);

    eventBus.trigger(eventName, {});
    // No callback should be call on event
    expect.verifySteps([]);

    eventBus.addEventListener(eventName, listener1);
    // enableReader should be call when a listener is added
    expect.verifySteps(["onAddListenerCallback"]);

    eventBus.trigger(eventName, {});
    // No callback should be call when an event is trigger
    expect.verifySteps(["listener1"]);

    eventBus.addEventListener(eventName, listener2);
    // enableReader should be call when a listener is added
    expect.verifySteps(["onAddListenerCallback"]);

    eventBus.trigger(eventName, {});
    // No callback should be call when an event is trigger
    expect.verifySteps(["listener1", "listener2"]);

    eventBus.removeEventListener(eventName, listener1);
    // stopReader should be call when a listeners is removed
    expect.verifySteps(["onRemoveListenerCallback"]);

    eventBus.trigger(eventName, {});
    // No callback should be call when an event is trigger
    expect.verifySteps(["listener2"]);

    eventBus.removeEventListener(eventName, listener2);
    // stopReader should be call when a listeners is removed
    expect.verifySteps(["onRemoveListenerCallback"]);

    eventBus.trigger(eventName, {});
    // No callback should be call when an event is trigger
    expect.verifySteps([]);
});

import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { getService, makeTestApp } from "@web/../tests/web_test_helpers";

import { ServiceWorkerChannelPlugin } from "@web/core/browser/service_worker_channel_plugin";

describe.current.tags("headless");

let plugin;

beforeEach(async () => {
    await makeTestApp();
    plugin = getService(ServiceWorkerChannelPlugin);
    const registration = await navigator.serviceWorker.register("/web/service-worker.js", {
        scope: "/odoo",
    });
    registration.active.postMessage = ({ type, channel, id }) => {
        expect.step(type === "service_worker_channel:ready" ? `ready:${channel}` : `ack:${id}`);
    };
});

function deliver(id, channel, message) {
    return { type: "service_worker_channel:deliver", id, channel, message };
}

test("listening announces the channel to the worker once", async () => {
    plugin.listen("voip", () => {});
    plugin.listen("voip", () => {});
    plugin.listen("discuss", () => {});
    await expect.waitForSteps(["ready:voip", "ready:discuss"]);
});

test("a message broadcast to every page reaches the channel's handlers", async () => {
    plugin.listen("voip", (message) => expect.step(`voip:${message.action}`));
    await expect.waitForSteps(["ready:voip"]);
    new BroadcastChannel("service_worker_channel").postMessage(
        deliver("id-1", "voip", { action: "answer" })
    );
    await expect.waitForSteps(["voip:answer", "ack:id-1"]);
});

test("a message posted to this page by the worker reaches the channel's handlers", async () => {
    plugin.listen("voip", (message) => expect.step(`voip:${message.action}`));
    await expect.waitForSteps(["ready:voip"]);
    navigator.serviceWorker.dispatchEvent(
        new MessageEvent("message", { data: deliver("id-1", "voip", { action: "call_back" }) })
    );
    await expect.waitForSteps(["voip:call_back", "ack:id-1"]);
});

test("a message for a channel nobody listens to is left to the worker", async () => {
    plugin.listen("voip", (message) => expect.step(`voip:${message.action}`));
    await expect.waitForSteps(["ready:voip"]);
    navigator.serviceWorker.dispatchEvent(
        new MessageEvent("message", { data: deliver("id-1", "discuss", { action: "open" }) })
    );
    navigator.serviceWorker.dispatchEvent(
        new MessageEvent("message", { data: deliver("id-2", "voip", { action: "answer" }) })
    );
    // Not acknowledged: the worker keeps it for a page listening to it.
    await expect.waitForSteps(["voip:answer", "ack:id-2"]);
});

test("a message received again is handled once", async () => {
    plugin.listen("voip", (message) => expect.step(`voip:${message.action}`));
    await expect.waitForSteps(["ready:voip"]);
    // Broadcast while the page was loading, then handed again once it
    // announced it listens.
    const message = deliver("id-1", "voip", { action: "answer" });
    navigator.serviceWorker.dispatchEvent(new MessageEvent("message", { data: message }));
    navigator.serviceWorker.dispatchEvent(new MessageEvent("message", { data: message }));
    await expect.waitForSteps(["voip:answer", "ack:id-1"]);
});

test("a handler stops receiving messages once it stops listening", async () => {
    const stop = plugin.listen("voip", (message) => expect.step(`first:${message.action}`));
    plugin.listen("voip", (message) => expect.step(`second:${message.action}`));
    await expect.waitForSteps(["ready:voip"]);
    stop();
    navigator.serviceWorker.dispatchEvent(
        new MessageEvent("message", { data: deliver("id-1", "voip", { action: "answer" }) })
    );
    await expect.waitForSteps(["second:answer", "ack:id-1"]);
});

import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { EventBus } from "@odoo/owl";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { makeSpreadsheetMockEnv } from "@spreadsheet/../tests/helpers/model";
import { SpreadsheetCollaborativeChannel } from "@spreadsheet_edition/bundle/o_spreadsheet/collaborative/spreadsheet_collaborative_channel";
import { mockService } from "@web/../tests/web_test_helpers";

describe.current.tags("headless");
defineSpreadsheetModels();

async function setupEnvWithMockBus({ mockRPC } = {}) {
    const channels = [];
    const _bus = new EventBus();

    const busService = {
        addChannel: (name) => {
            channels.push(name);
        },
        subscribe: (eventName, handler) => {
            _bus.addEventListener("notif", ({ detail }) => {
                if (detail.type === eventName) {
                    handler(detail.payload, { id: detail.id });
                }
            });
        },
        notify: (message) => {
            _bus.trigger("notif", message);
        },
    };
    const rpc = mockRPC || function (route, params) {
        // Mock the server behavior: new revisions are pushed in the bus
        if (params.method === "dispatch_spreadsheet_message") {
            const [documentId, message] = params.args;
            busService.notify({ type: "spreadsheet", payload: { id: documentId, ...message } });
            return true;
        }
    };
    mockService("bus_service", busService);
    return makeSpreadsheetMockEnv({
        mockRPC: rpc,
    });
}


test("sending a message forward it to the registered listener", async function () {
    const env = await setupEnvWithMockBus();
    const channel = new SpreadsheetCollaborativeChannel(env, "my.model", 5);
    let i = 5;
    channel.onNewMessage("anId", (message) => {
        expect.step("message");
        expect(message.greeting).toBe("hello", {
            message: "It should have the correct message content",
        });
        i = 8;
    });
    await channel.sendMessage({ greeting: "hello" });
    expect(i).toBe(8);
    // It should have received the message
    expect.verifySteps(["message", "message"]);
});

test("previous messages are forwarded when registering a listener", async function () {
    const env = await setupEnvWithMockBus();
    const channel = new SpreadsheetCollaborativeChannel(env, "my.model", 5);
    await channel.sendMessage({ greeting: "hello" });
    channel.onNewMessage("anId", (message) => {
        expect.step("message");
        expect(message.greeting).toBe("hello", {
            message: "It should have the correct message content",
        });
    });
    // It should have received the pending message
    expect.verifySteps(["message", "message"]);
});

test("the channel does not care about other bus messages", async function () {
    const env = await setupEnvWithMockBus();
    const channel = new SpreadsheetCollaborativeChannel(env, "my.model", 5);
    channel.onNewMessage("anId", () => expect.step("message"));
    env.services.bus_service.notify("a-random-channel", "a-random-message");
    await animationFrame();
    // The message should not have been received
    expect.verifySteps([]);
});

test("Message accepted by the server is immediately handled", async function () {
    const env = await setupEnvWithMockBus({
        mockRPC: async function (route, params) {
            // Mock the server to accept the revision
            if (params.method === "dispatch_spreadsheet_message") {
                return true;
            }
        }
    });
    const channel = new SpreadsheetCollaborativeChannel(env, "my.model", 5);
    channel.onNewMessage("anId", (message) => {
        expect.step("message");
        expect(message.greeting).toBe("hello");
    });
    channel.sendMessage({ greeting: "hello" });
    await animationFrame();
    expect.verifySteps(["message"]);
});

test("Message refused by the server is not immediately handled", async function () {
    const env = await setupEnvWithMockBus({
        mockRPC: async function (route, params) {
            // Mock the server to refuse the revision
            if (params.method === "dispatch_spreadsheet_message") {
                return false;
            }
        }
    });
    const channel = new SpreadsheetCollaborativeChannel(env, "my.model", 5);
    channel.onNewMessage("anId", () => {
        expect.step("message");
    });
    channel.sendMessage({ greeting: "hello" });
    await animationFrame();
    expect.verifySteps([]);
});

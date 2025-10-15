import { describe, expect, test, mockFetch, beforeEach, waitUntil } from "@odoo/hoot";
import { IoTLongpolling } from "@iot_base/network_utils/longpolling";

const notificationsReceived = [];
beforeEach(() => notificationsReceived.splice(0));

const mockServices = {
    notification: { add: (title) => notificationsReceived.push(title) },
};
const mockIp = "1.2.3.4";

const mockActionResponse = (options = {}) => {
    mockFetch((path, { body }) => {
        const url = new URL(path);
        const expectedRoute = options.route ?? "/iot_drivers/action";
        if (url.pathname === expectedRoute && url.hostname === mockIp) {
            if (options.shouldThrowError) {
                throw new Error();
            }
            return JSON.parse(body).params;
        }
    });
};

const mockEventResponse = (events) => {
    const eventsRemaining = [...events];
    mockFetch((path, { body }) => {
        const url = new URL(path);
        if (url.pathname === "/iot_drivers/event" && url.hostname === mockIp) {
            if (eventsRemaining.length === 0) {
                return new Promise(() => {});
            }
            const [event] = eventsRemaining.splice(0, 1);
            const listener = JSON.parse(body).params.listener;
            return { result: { session_id: listener.session_id, device_identifier: event } };
        }
    });
};

describe("action", () => {
    test("returns action result", async () => {
        const longpolling = new IoTLongpolling(mockServices);
        mockActionResponse();

        const result = await longpolling.action(mockIp, "mockDevice", "testData");

        expect(result.data).toBe("testData");
        expect(result.device_identifier).toBe("mockDevice");
    });

    test("provides session ID to action", async () => {
        const longpolling = new IoTLongpolling(mockServices);
        mockActionResponse();

        const result = await longpolling.action(mockIp, "mockDevice", "testData");

        expect(result.session_id).toBeOfType("string");
        expect(result.session_id).toBe(longpolling._session_id);
    });

    test("throws if network error occurs", async () => {
        const longpolling = new IoTLongpolling(mockServices);
        mockActionResponse({ shouldThrowError: true });

        const resultPromise = longpolling.action(mockIp, "mockDevice", "testData");

        await expect(resultPromise).rejects.toBeInstanceOf(Error);
    });

    test("shows failure notification", async () => {
        const longpolling = new IoTLongpolling(mockServices);
        mockActionResponse({ shouldThrowError: true });

        const resultPromise = longpolling.action(mockIp, "mockDevice", "testData");

        await expect(resultPromise).rejects.toBeInstanceOf(Error);
        expect(notificationsReceived).toHaveLength(1);
        expect(notificationsReceived[0].values).toInclude(mockIp);
    });

    test("does not show failure notification when fallback=true", async () => {
        const longpolling = new IoTLongpolling(mockServices);
        mockActionResponse({ shouldThrowError: true });

        const resultPromise = longpolling.action(mockIp, "mockDevice", "testData", true);

        await expect(resultPromise).rejects.toBeInstanceOf(Error);
        expect(notificationsReceived).toHaveLength(0);
    });

    test("uses the provided route", async () => {
        const longpolling = new IoTLongpolling(mockServices);
        mockActionResponse({ route: "/my-custom-route" });

        const result = await longpolling.action(
            mockIp,
            "mockDevice",
            "testData",
            true,
            "/my-custom-route"
        );

        expect(result.data).toBe("testData");
    });
});

describe("addListener", () => {
    test("receives an event", async () => {
        const longpolling = new IoTLongpolling(mockServices);
        const eventsReceived = [];
        mockEventResponse(["mockDevice"]);

        longpolling.addListener(mockIp, ["mockDevice"], "testListenerId", (event) =>
            eventsReceived.push(event)
        );

        await waitUntil(() => eventsReceived.length === 1);
        expect(eventsReceived[0].device_identifier).toBe("mockDevice");
    });

    test("receives multiple events", async () => {
        const longpolling = new IoTLongpolling(mockServices);
        const eventsReceived = [];
        mockEventResponse(["mockDevice", "mockDevice"]);

        longpolling.addListener(mockIp, ["mockDevice"], "testListenerId", (event) =>
            eventsReceived.push(event)
        );

        await waitUntil(() => eventsReceived.length === 2);
        expect(eventsReceived[0].device_identifier).toBe("mockDevice");
        expect(eventsReceived[1].device_identifier).toBe("mockDevice");
    });

    test("ignores other device events", async () => {
        const longpolling = new IoTLongpolling(mockServices);
        const eventsReceived = [];
        mockEventResponse(["otherDevice", "mockDevice"]);

        longpolling.addListener(mockIp, ["mockDevice"], "testListenerId", (event) =>
            eventsReceived.push(event)
        );

        await waitUntil(() => eventsReceived.length === 1);
        expect(eventsReceived[0].device_identifier).toBe("mockDevice");
    });

    test("receives events for multiple devices", async () => {
        const longpolling = new IoTLongpolling(mockServices);
        const eventsReceived = [];
        mockEventResponse(["mockDevice2", "mockDevice"]);

        longpolling.addListener(mockIp, ["mockDevice", "mockDevice2"], "testListenerId", (event) =>
            eventsReceived.push(event)
        );

        await waitUntil(() => eventsReceived.length === 2);
        expect(eventsReceived[0].device_identifier).toBe("mockDevice2");
        expect(eventsReceived[1].device_identifier).toBe("mockDevice");
    });
});

describe("removeListener", () => {
    test("stops listening for events", async () => {
        const longpolling = new IoTLongpolling(mockServices);
        const eventsReceived = [];
        mockEventResponse(["mockDevice", "mockDevice"]);

        longpolling.addListener(mockIp, ["mockDevice"], "testListenerId", (event) => {
            longpolling.removeListener(mockIp, "mockDevice", "testListenerId");
            eventsReceived.push(event);
        });

        await waitUntil(() => eventsReceived.length === 1);
        expect(longpolling._listeners[mockIp].devices).toBeEmpty();
    });
});

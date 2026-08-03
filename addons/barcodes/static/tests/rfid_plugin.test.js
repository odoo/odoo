import { advanceTime, describe, expect, mockWebSocket, test } from "@odoo/hoot";
import { Component, usePlugin, xml } from "@odoo/owl";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { session } from "@web/session";
import { RfidPlugin } from "@barcodes/rfid_plugin";

async function startRfidPlugin(sessionValues = {}) {
    patchWithCleanup(session, sessionValues);
    let plugin;
    class Root extends Component {
        static template = xml`<div/>`;
        setup() {
            plugin = usePlugin(RfidPlugin);
        }
    }
    await mountWithCleanup(Root);
    return plugin;
}

describe("isSupported", () => {
    test("needs an URL to reach the scanner", async () => {
        const plugin = await startRfidPlugin({ rfid_ws_url: "" });
        expect(plugin.isSupported()).toBe(false);
    });

    test("is supported once an URL is configured", async () => {
        const plugin = await startRfidPlugin({ rfid_ws_url: "ws://localhost:1234" });
        expect(plugin.isSupported()).toBe(true);
    });
});

describe("trigger keys", () => {
    test("are split, trimmed and emptied out", async () => {
        const plugin = await startRfidPlugin({ rfid_trigger_keys: " F15 ,F16,, " });
        expect([...plugin.triggerKeys]).toEqual(["F15", "F16"]);
    });

    test("an empty setting binds nothing", async () => {
        const plugin = await startRfidPlugin({ rfid_trigger_keys: "" });
        expect(plugin.triggerKeys.size).toBe(0);
    });
});

describe("extractTags", () => {
    test("returns nothing without a configured regex", async () => {
        const plugin = await startRfidPlugin({ rfid_tag_extraction_regex: "" });
        expect(plugin.extractTags("3074257BF7194E4000001A85")).toEqual([]);
    });

    test("an invalid regex is ignored rather than thrown", async () => {
        const plugin = await startRfidPlugin({ rfid_tag_extraction_regex: "([" });
        expect(plugin.extractionRegex).toBe(null);
        expect(plugin.extractTags("anything")).toEqual([]);
    });

    test("takes the first capturing group when there is one", async () => {
        const plugin = await startRfidPlugin({
            rfid_tag_extraction_regex: "EPC:([0-9A-F]+);",
        });
        expect(plugin.extractTags("ANT:1;EPC:3074257BF7194E4000001A85;RSSI:-42")).toEqual([
            "3074257BF7194E4000001A85",
        ]);
    });

    test("falls back on the whole match without a capturing group", async () => {
        const plugin = await startRfidPlugin({ rfid_tag_extraction_regex: "[0-9A-F]{24}" });
        expect(plugin.extractTags("<3074257BF7194E4000001A85>")).toEqual([
            "3074257BF7194E4000001A85",
        ]);
    });

    test("collects every tag of a multi-tag payload", async () => {
        const plugin = await startRfidPlugin({
            rfid_tag_extraction_regex: "EPC:([0-9A-F]+);",
        });
        expect(
            plugin.extractTags("EPC:3074257BF7194E4000001A85;EPC:3074257BF7194E4000001A86;")
        ).toEqual(["3074257BF7194E4000001A85", "3074257BF7194E4000001A86"]);
    });

    test("does not carry its regex state over to the next message", async () => {
        const plugin = await startRfidPlugin({
            rfid_tag_extraction_regex: "EPC:([0-9A-F]+);",
        });
        const message = "EPC:3074257BF7194E4000001A85;";
        expect(plugin.extractTags(message)).toEqual(["3074257BF7194E4000001A85"]);
        expect(plugin.extractTags(message)).toEqual(["3074257BF7194E4000001A85"]);
    });

    test("a regex matching the empty string terminates", async () => {
        const plugin = await startRfidPlugin({ rfid_tag_extraction_regex: "[0-9]*" });
        expect(plugin.extractTags("42abc7")).toEqual(["42", "7"]);
    });

    test("returns nothing for an empty message", async () => {
        const plugin = await startRfidPlugin({ rfid_tag_extraction_regex: "[0-9A-F]+" });
        expect(plugin.extractTags("")).toEqual([]);
    });
});

describe("reconnect", () => {
    async function startWithMockedScanner() {
        const plugin = await startRfidPlugin({
            rfid_ws_url: "ws://localhost:1234",
            rfid_start_command: "START",
            rfid_stop_command: "STOP",
        });
        // Registered only once the app is up: `mockWebSocket` holds a single
        // callback, and mounting installs its own for the bus service.
        const sockets = [];
        mockWebSocket((socket) => sockets.push(socket));
        return { plugin, sockets };
    }

    test("a scan interrupted by a drop is resumed", async () => {
        const { plugin, sockets } = await startWithMockedScanner();
        plugin.startScan();
        await advanceTime(0);
        expect(sockets).toHaveLength(1);
        expect(plugin.isConnected()).toBe(true);

        sockets[0].close(1006);
        await advanceTime(0);
        expect(plugin.isConnected()).toBe(false);

        await advanceTime(1000);
        expect(sockets).toHaveLength(2);
        expect(plugin.isConnected()).toBe(true);
    });

    test("a drop while idle is left alone", async () => {
        const { plugin, sockets } = await startWithMockedScanner();
        plugin.connect();
        await advanceTime(0);
        expect(sockets).toHaveLength(1);

        sockets[0].close(1006);
        await advanceTime(10000);
        expect(sockets).toHaveLength(1);
        expect(plugin.isConnected()).toBe(false);
    });

    test("retries are given up on after the last delay", async () => {
        const { plugin, sockets } = await startWithMockedScanner();
        const events = [];
        plugin.bus.addEventListener("rfid_connection_changed", (ev) => events.push(ev.detail));

        plugin.startScan();
        await advanceTime(0);
        for (const delay of [0, 1000, 2000, 4000]) {
            await advanceTime(delay);
            sockets.at(-1).close(1006);
            await advanceTime(0);
        }
        expect(sockets).toHaveLength(RfidPlugin.RECONNECT_DELAYS_IN_MS.length + 1);

        await advanceTime(10000);
        expect(sockets).toHaveLength(RfidPlugin.RECONNECT_DELAYS_IN_MS.length + 1);
        expect(events.at(-1)).toEqual({ connected: false, retrying: false });
        expect(plugin.wantsScan).toBe(false);
    });

    test("a connection that held for a while earns a fresh budget", async () => {
        const { plugin, sockets } = await startWithMockedScanner();
        plugin.startScan();
        await advanceTime(0);

        for (const delay of [0, 1000, 2000]) {
            await advanceTime(delay);
            sockets.at(-1).close(1006);
            await advanceTime(0);
        }
        expect(sockets).toHaveLength(RfidPlugin.RECONNECT_DELAYS_IN_MS.length);

        await advanceTime(4000);
        expect(sockets).toHaveLength(RfidPlugin.RECONNECT_DELAYS_IN_MS.length + 1);
        await advanceTime(RfidPlugin.HEALTHY_CONNECTION_IN_MS);
        sockets.at(-1).close(1006);
        await advanceTime(1000);

        expect(sockets).toHaveLength(RfidPlugin.RECONNECT_DELAYS_IN_MS.length + 2);
        expect(plugin.isConnected()).toBe(true);
    });

    test("stopping the scan cancels a pending retry", async () => {
        const { plugin, sockets } = await startWithMockedScanner();
        plugin.startScan();
        await advanceTime(0);

        sockets[0].close(1006);
        await advanceTime(0);
        plugin.stopScan();

        await advanceTime(10000);
        expect(sockets).toHaveLength(1);
    });

    test("leaving the app cancels a pending retry", async () => {
        const { plugin, sockets } = await startWithMockedScanner();
        plugin.startScan();
        await advanceTime(0);

        sockets[0].close(1006);
        await advanceTime(0);
        plugin.disconnect();

        await advanceTime(10000);
        expect(sockets).toHaveLength(1);
    });
});

import { describe, expect, test } from "@odoo/hoot";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { makeCustomerDisplayService } from "../webrtc/utils/webrtc_service";

describe("update_customer_display", () => {
    test("updates data when device uuid matches", async () => {
        const { webrtc, data } = await makeCustomerDisplayService();
        const trigger = webrtc._registry.get("update_customer_display");

        trigger(
            { id: "peer-1", group: "terminal", deviceUuid: "my-uuid" },
            { finalized: true, amount: "$10" }
        );

        expect(data).toEqual({ finalized: true, amount: "$10" });
    });

    test("ignores message from a different device", async () => {
        const { webrtc, data } = await makeCustomerDisplayService();
        const trigger = webrtc._registry.get("update_customer_display");

        trigger({ id: "peer-1", group: "terminal", deviceUuid: "other-uuid" }, { finalized: true });

        expect(data).toEqual({});
    });

    test("ignores message from not a terminal", async () => {
        const { webrtc, data } = await makeCustomerDisplayService();
        const trigger = webrtc._registry.get("update_customer_display");

        trigger(
            { id: "peer-1", group: "customer_display", deviceUuid: "my-uuid" },
            { finalized: true }
        );

        expect(data).toEqual({});
    });

    test("reloads page with new theme when theme changes", async () => {
        const { webrtc, data } = await makeCustomerDisplayService();
        const trigger = webrtc._registry.get("update_customer_display");
        const mockLocation = { search: "" };
        patchWithCleanup(browser, { location: mockLocation });

        trigger(
            { id: "peer-1", group: "terminal", deviceUuid: "my-uuid" },
            { displayTheme: "dark", finalized: true }
        );

        expect(mockLocation.search).toBe("theme=dark");
        expect(data).toEqual({});
    });
});

describe("update_customer_display snapshot", () => {
    test("build null", async () => {
        const { webrtc } = await makeCustomerDisplayService();
        const { build } = webrtc._snapshotRegistry.get("update_customer_display");

        expect(build({ id: "peer-1", group: "terminal", deviceUuid: "my-uuid" })).toBe(null);
    });

    test("applies snapshot when device uuid matches", async () => {
        const { webrtc, data } = await makeCustomerDisplayService();
        const { apply } = webrtc._snapshotRegistry.get("update_customer_display");

        apply(
            { id: "peer-1", group: "terminal", deviceUuid: "my-uuid" },
            { finalized: true, amount: "$10" }
        );

        expect(data).toEqual({ finalized: true, amount: "$10" });
    });

    test("ignores snapshot from a different device", async () => {
        const { webrtc, data } = await makeCustomerDisplayService();
        const { apply } = webrtc._snapshotRegistry.get("update_customer_display");

        apply({ id: "peer-1", group: "terminal", deviceUuid: "other-uuid" }, { finalized: true });

        expect(data).toEqual({});
    });

    test("ignores snapshot from not a terminal", async () => {
        const { webrtc, data } = await makeCustomerDisplayService();
        const { apply } = webrtc._snapshotRegistry.get("update_customer_display");

        apply(
            { id: "peer-1", group: "customer_display", deviceUuid: "my-uuid" },
            { finalized: true }
        );

        expect(data).toEqual({});
    });

    test("reloads page with new theme when snapshot contains a theme change", async () => {
        const { webrtc, data } = await makeCustomerDisplayService();
        const { apply } = webrtc._snapshotRegistry.get("update_customer_display");
        const mockLocation = { search: "" };
        patchWithCleanup(browser, { location: mockLocation });

        apply(
            { id: "peer-1", group: "terminal", deviceUuid: "my-uuid" },
            { displayTheme: "dark", finalized: true }
        );

        expect(mockLocation.search).toBe("theme=dark");
        expect(data).toEqual({});
    });
});

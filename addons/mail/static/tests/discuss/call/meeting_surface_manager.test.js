import {
    MeetingSurface,
    MeetingSurfaceManager,
} from "@mail/discuss/call/common/meeting_surface_manager";

import { describe, expect, test } from "@odoo/hoot";

describe.current.tags("desktop");

describe("meeting surface manager", () => {
    test("reconcile creates surfaces for the desired descriptors", () => {
        const manager = new MeetingSurfaceManager();
        const surfaces = manager.reconcile([
            { key: "session_main_1", type: "camera" },
            { key: "session_main_2", type: "camera" },
        ]);
        expect(surfaces.map((surface) => surface.key)).toEqual([
            "session_main_1",
            "session_main_2",
        ]);
        expect(manager.size).toBe(2);
        expect(surfaces[0]).toBeInstanceOf(MeetingSurface);
        expect(surfaces[0].data.type).toBe("camera");
    });

    test("reconcile keeps the same surface instance while the key stays desired", () => {
        const manager = new MeetingSurfaceManager();
        const first = manager.reconcile([{ key: "session_main_1" }, { key: "session_main_2" }]);
        const second = manager.reconcile([{ key: "session_main_1" }, { key: "session_main_2" }]);
        expect(second[0]).toBe(first[0]);
        expect(second[1]).toBe(first[1]);
        // The manager is the single owner: it never re-creates a still-desired surface.
        expect(manager.size).toBe(2);
    });

    test("reconcile drops surfaces that are no longer desired", () => {
        const manager = new MeetingSurfaceManager();
        const first = manager.reconcile([{ key: "a" }, { key: "b" }, { key: "c" }]);
        const second = manager.reconcile([{ key: "a" }, { key: "c" }]);
        expect(second).toEqual([first[0], first[2]]);
        expect(manager.get("b")).toBe(undefined);
        expect(manager.size).toBe(2);
    });

    test("reconcile replaces the data snapshot of a reused surface instead of mutating it", () => {
        const manager = new MeetingSurfaceManager();
        const first = manager.reconcile([
            {
                key: "session_main_1",
                session: { id: 1 },
                videoStream: "stream-1",
                placement: "main",
            },
        ]);
        const second = manager.reconcile([
            {
                key: "session_main_1",
                session: { id: 1 },
                videoStream: "stream-2",
                placement: "sidebar",
            },
        ]);
        expect(second[0]).toBe(first[0]);
        expect(second[0].data.videoStream).toBe("stream-2");
        expect(second[0].data.placement).toBe("sidebar");
    });

    test("a reused surface exposes a new data object, so cardData changes identity", () => {
        // The card component receives `surface.data` as its `cardData` prop. Merging the
        // descriptor into the surface would keep the same reference and the card would keep
        // rendering its previous media (a camera turning on would never show up).
        const manager = new MeetingSurfaceManager();
        const [first] = manager.reconcile([{ key: "session_main_1", videoStream: undefined }]);
        const firstData = first.data;
        const [second] = manager.reconcile([{ key: "session_main_1", videoStream: "stream-1" }]);
        expect(second).toBe(first);
        expect(second.data).not.toBe(firstData);
        expect(firstData.videoStream).toBe(undefined);
        expect(second.data.videoStream).toBe("stream-1");
    });

    test("reconcile result order follows the desired order, not the previous one", () => {
        const manager = new MeetingSurfaceManager();
        manager.reconcile([{ key: "a" }, { key: "b" }, { key: "c" }]);
        const reversed = manager.reconcile([{ key: "c" }, { key: "b" }, { key: "a" }]);
        expect(reversed.map((surface) => surface.key)).toEqual(["c", "b", "a"]);
        // Reordering is a geometry concern, not an identity concern: instances are reused.
        expect(reversed[0]).toBe(manager.get("c"));
    });

    test("reconcile handles empty desired lists", () => {
        const manager = new MeetingSurfaceManager();
        manager.reconcile([{ key: "a" }]);
        expect(manager.reconcile([])).toEqual([]);
        expect(manager.size).toBe(0);
        // A dropped surface can come back as a fresh instance.
        const again = manager.reconcile([{ key: "a" }]);
        expect(again[0].key).toBe("a");
    });

    test("reconcile ignores duplicate keys (a surface is only rendered once)", () => {
        const manager = new MeetingSurfaceManager();
        const surfaces = manager.reconcile([{ key: "a" }, { key: "a" }, { key: "b" }]);
        expect(surfaces.map((surface) => surface.key)).toEqual(["a", "b"]);
        expect(manager.size).toBe(2);
    });
});

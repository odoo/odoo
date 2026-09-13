// @ts-check

import { destroy, expect, test } from "@odoo/hoot";
import { keyDown, keyUp } from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import {
    useLongTouchSelection,
    useRecordSelection,
} from "@web/views/multi_record_selection";

/**
 * @param {string} id
 * @returns {{ id: string, selected: boolean, toggleSelection: (selected?: boolean) => void }}
 */
function makeRecord(id) {
    return {
        id,
        selected: false,
        toggleSelection(selected) {
            this.selected = selected === undefined ? !this.selected : selected;
        },
    };
}

/** @param {object} [ctxOverrides] */
async function mountSelectionHost(ctxOverrides = {}) {
    class Host extends Component {
        static template = xml`<div/>`;
        static props = {};
        /** @type {any[]} */
        records = [];
        /** @type {ReturnType<typeof useRecordSelection>} */
        sel;

        setup() {
            this.records = ["r1", "r2", "r3", "r4"].map(makeRecord);
            this.sel = useRecordSelection({
                getRecords: () => this.records,
                ...ctxOverrides,
            });
        }
    }
    return mountWithCleanup(Host);
}

test("range selection selects the whole span from the anchor", async () => {
    const host = await mountSelectionHost();

    host.sel.toggleSelection(host.records[0]);
    host.sel.toggleSelection(host.records[2], true);

    expect(host.records.map((r) => r.selected)).toEqual([true, true, true, false]);
});

test("range selection survives a reload that replaces the record objects", async () => {
    const host = await mountSelectionHost();

    host.sel.toggleSelection(host.records[0]);
    expect(host.records[0].selected).toBe(true);

    const reloaded = ["r1", "r2", "r3", "r4"].map(makeRecord);
    reloaded[0].selected = true;
    host.records = reloaded;

    expect(host.sel.isAnchorPresent()).toBe(true);
    host.sel.toggleSelection(host.records[3], true);

    expect(host.records.map((r) => r.selected)).toEqual([true, true, true, true]);
});

test("a range request without a resolvable anchor falls back to a single toggle", async () => {
    const host = await mountSelectionHost();

    host.sel.toggleSelection(host.records[1]);
    host.records = [makeRecord("r5"), makeRecord("r6")];

    expect(host.sel.isAnchorPresent()).toBe(false);
    host.sel.toggleSelection(host.records[1], true);

    expect(host.records.map((r) => r.selected)).toEqual([false, true]);
    expect(host.sel.lastCheckedRecord).toBe(host.records[1]);
});

test("the range toggle can be routed through the caller's own implementation", async () => {
    /** @type {string[]} */
    const ranged = [];
    const host = await mountSelectionHost({
        rangeToggle: (/** @type {any} */ record) => ranged.push(record.id),
    });

    host.sel.toggleSelection(host.records[0]);
    host.sel.toggleSelection(host.records[2], true);

    expect(ranged).toEqual(["r3"]);
    expect(host.records[2].selected).toBe(false, {
        message: "the default range application must not also run",
    });
});

test("expandCheckboxes grows and shrinks by id, not object identity", async () => {
    const host = await mountSelectionHost();

    expect(host.sel.expandCheckboxes(null, "down")).toBe(true);
    expect(host.records[0].selected).toBe(true);
    expect(host.sel.shiftKeyedRecord).toBe(host.records[0]);

    const reloaded = ["r1", "r2", "r3", "r4"].map(makeRecord);
    reloaded[0].selected = true;
    host.records = reloaded;

    expect(host.sel.expandCheckboxes(host.records[0], "down")).toBe(true);
    expect(host.records.map((r) => r.selected)).toEqual([true, true, false, false]);

    expect(host.sel.expandCheckboxes(host.records[1], "up")).toBe(true);
    expect(host.records[1].selected).toBe(false, {
        message: "moving back towards the shift-keyed record shrinks the span",
    });
});

test("the selection modifier callback tracks Alt across keydown/keyup/blur", async () => {
    /** @type {boolean[]} */
    const calls = [];
    await mountSelectionHost({
        onSelectionModifier: (/** @type {boolean} */ available) =>
            calls.push(available),
    });

    await keyDown("alt");
    expect(calls).toEqual([true]);
    await keyUp("alt");
    expect(calls).toEqual([true, false]);
    window.dispatchEvent(new Event("blur"));
    expect(calls).toEqual([true, false, false]);
});

test("shiftKeyMode mirrors the physical shift key", async () => {
    const host = await mountSelectionHost();

    expect(host.sel.shiftKeyMode).toBe(false);
    await keyDown("shift");
    expect(host.sel.shiftKeyMode).toBe(true);
    window.dispatchEvent(new KeyboardEvent("keyup", { key: "Shift", shiftKey: false }));
    expect(host.sel.shiftKeyMode).toBe(false);
});

test("losing focus clears the shift selection anchor", async () => {
    const host = await mountSelectionHost();
    await keyDown("shift");
    host.sel.expandCheckboxes(null, "down");

    window.dispatchEvent(new Event("blur"));

    expect(host.sel.shiftKeyMode).toBe(false);
    expect(host.sel.shiftKeyedRecord).toBe(undefined);
});

const LONG_TOUCH_THRESHOLD = 400;

/** @param {(record: any) => void} onLongTouch */
async function mountLongTouchHost(onLongTouch) {
    class Host extends Component {
        static template = xml`<div/>`;
        static props = {};
        /** @type {ReturnType<typeof useLongTouchSelection>} */
        longTouch;

        setup() {
            this.longTouch = useLongTouchSelection({
                getLongTouchThreshold: () => LONG_TOUCH_THRESHOLD,
                onLongTouch,
            });
        }
    }
    return mountWithCleanup(Host);
}

test("a touch held past the threshold fires the long-touch callback once", async () => {
    /** @type {any[]} */
    const touched = [];
    const host = await mountLongTouchHost((record) => touched.push(record));

    host.longTouch.onTouchStart("rec1");
    await advanceTime(LONG_TOUCH_THRESHOLD * 2);

    expect(touched).toEqual(["rec1"]);
});

test("an early release or a move disarms the long-touch timer", async () => {
    let touched = 0;
    const host = await mountLongTouchHost(() => touched++);

    host.longTouch.onTouchStart();
    host.longTouch.onTouchEnd();
    await advanceTime(LONG_TOUCH_THRESHOLD * 2);
    expect(touched).toBe(0);

    host.longTouch.onTouchStart();
    host.longTouch.onTouchMove();
    await advanceTime(LONG_TOUCH_THRESHOLD * 2);
    expect(touched).toBe(0);
});

test("release cancels an overdue long-touch callback that has not run", async () => {
    let touched = 0;
    const host = await mountLongTouchHost(() => touched++);
    const start = Date.now();
    host.longTouch.onTouchStart();
    // A busy event loop can deliver touchend before an already due timer.
    patchWithCleanup(Date, { now: () => start + LONG_TOUCH_THRESHOLD + 1 });
    host.longTouch.onTouchEnd();
    await advanceTime(LONG_TOUCH_THRESHOLD * 2);

    expect(touched).toBe(0);
});

test("a pending long touch dies with its component", async () => {
    let touched = 0;
    const host = await mountLongTouchHost(() => touched++);

    host.longTouch.onTouchStart();
    destroy(host);
    await advanceTime(LONG_TOUCH_THRESHOLD * 2);

    expect(touched).toBe(0);
});

test("a completed touch releases its timer before the callback starts another touch", async () => {
    const touched = [];
    const host = await mountLongTouchHost((record) => {
        touched.push(record);
        if (record === "first") {
            host.longTouch.onTouchStart("second");
        }
    });

    host.longTouch.onTouchStart("first");
    await advanceTime(LONG_TOUCH_THRESHOLD + 1);
    expect(touched).toEqual(["first"]);
    await advanceTime(LONG_TOUCH_THRESHOLD + 1);
    expect(touched).toEqual(["first", "second"]);
});

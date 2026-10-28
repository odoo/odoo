/** @odoo-module */

import { describe, expect, getCurrent, test, trackObject } from "@odoo/hoot";
import { getUncollectedObjects } from "../../core/gc";
import { parseUrl } from "../local_helpers";

function getUncollectedLabels() {
    return getUncollectedObjects().get(getCurrent().test.fullName) ?? [];
}

describe(parseUrl(import.meta.url), () => {
    test("uncollected objects are reported once", async () => {
        const retained = {};
        trackObject("retained", retained);
        trackObject("released", {});

        // Recently tracked objects are only checked on the next call
        expect(getUncollectedLabels()).toEqual([]);

        await window.gc?.({ type: "major", execution: "async" });

        // Objects are only tracked when garbage collection can be forced
        const expected = typeof window.gc === "function" ? ["retained"] : [];
        expect(getUncollectedLabels()).toEqual(expected);
        expect(getUncollectedLabels()).toEqual([]);
        expect(retained).toEqual({});
    });
});

/** @odoo-module */

import { describe, expect, test } from "@odoo/hoot";
import { parseUrl } from "../local_helpers";

import { Suite } from "../../core/suite";

describe(parseUrl(import.meta.url), () => {
    test("should have a hashed id", () => {
        expect(new Suite(null, "a suite", []).id).toMatch(/^\w{8}$/);
    });

    test("should describe its path in its name", () => {
        const a = new Suite(null, "a", []);
        const b = new Suite(a, "b", []);
        const c = new Suite(a, "c", []);
        const d = new Suite(b, "d", []);

        expect(a.parent).toBe(null);
        expect(b.parent).toBe(a);
        expect(c.parent).toBe(a);
        expect(d.parent.parent).toBe(a);

        expect(a.fullName).toBe("a");
        expect(b.fullName).toBe("a/b");
        expect(c.fullName).toBe("a/c");
        expect(d.fullName).toBe("a/b/d");
    });
});

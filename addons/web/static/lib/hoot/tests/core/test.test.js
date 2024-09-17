/** @odoo-module */

import { describe, expect, test } from "@odoo/hoot";
import { parseUrl } from "../local_helpers";

import { Suite } from "../../core/suite";
import { Test } from "../../core/test";

describe(parseUrl(import.meta.url), () => {
    test("should have a hashed id", () => {
        expect(new Test(null, "a test", {}, () => {}).id).toMatch(/^\w{8}$/);
    });

    test("should describe its path in its name", () => {
        const a = new Suite(null, "a", {});
        const b = new Suite(a, "b", {});
        const t1 = new Test(null, "t1", {}, () => {});
        const t2 = new Test(a, "t2", {}, () => {});
        const t3 = new Test(b, "t3", {}, () => {});

        expect(t1.fullName).toBe("t1");
        expect(t2.fullName).toBe("a/t2");
        expect(t3.fullName).toBe("a/b/t3");
    });
});

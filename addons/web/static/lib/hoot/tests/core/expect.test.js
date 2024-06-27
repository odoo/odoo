import { describe, expect, test } from "@odoo/hoot";
import { Suite } from "../../core/suite";
import { parseUrl } from "../local_helpers";

describe(parseUrl(import.meta.url), () => {
    test("toBeUndefined", () => {
        expect(undefined).toBeUndefined();
        expect(null).not.toBeUndefined();
        expect(0).not.toBeUndefined();
        expect("").not.toBeUndefined();
        expect(false).not.toBeUndefined();
        expect({ a: 1 }).not.toBeUndefined();
        expect(new Suite(null, "a suite", []).id).toMatch(/^\w{8}$/);
    });

    test("toBeNull", () => {
        expect(null).toBeNull();
        expect(undefined).not.toBeNull();
        expect(0).not.toBeNull();
        expect("").not.toBeNull();
        expect(false).not.toBeNull();
        expect({ a: 1 }).not.toBeNull();
    });
});

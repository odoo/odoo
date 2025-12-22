/** @odoo-module */

import { describe, expect, test } from "@odoo/hoot";
import { parseUrl } from "../local_helpers";

import { Suite } from "../../core/suite";
import { Test } from "../../core/test";

function disableHighlighting() {
    if (!window.Prism) {
        return () => {};
    }
    const { highlight } = window.Prism;
    window.Prism.highlight = (text) => text;

    return function restoreHighlighting() {
        window.Prism.highlight = highlight;
    };
}

describe(parseUrl(import.meta.url), () => {
    test("should have a hashed id", () => {
        expect(new Test(null, "a test", {}).id).toMatch(/^\w{8}$/);
    });

    test("should describe its path in its name", () => {
        const a = new Suite(null, "a", {});
        const b = new Suite(a, "b", {});
        const t1 = new Test(null, "t1", {});
        const t2 = new Test(a, "t2", {});
        const t3 = new Test(b, "t3", {});

        expect(t1.fullName).toBe("t1");
        expect(t2.fullName).toBe("a/t2");
        expect(t3.fullName).toBe("a/b/t3");
    });

    test("run is async and lazily formatted", () => {
        const restoreHighlighting = disableHighlighting();

        const testName = "some test";
        const t = new Test(null, testName, {});
        const runFn = () => {
            // Synchronous
            expect(1).toBe(1);
        };

        expect(t.run).toBe(null);
        expect(t.runFnString).toBe("");
        expect(t.formatted).toBe(false);

        t.setRunFn(runFn);

        expect(t.run()).toBeInstanceOf(Promise);
        expect(t.runFnString).toBe(runFn.toString());
        expect(t.formatted).toBe(false);

        expect(String(t.code)).toBe(
            `
test("${testName}", () => {
    // Synchronous
    expect(1).toBe(1);
});
`.trim()
        );
        expect(t.formatted).toBe(true);

        restoreHighlighting();
    });
});

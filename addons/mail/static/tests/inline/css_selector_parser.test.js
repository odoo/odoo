import { parseSelector } from "@mail/convert_inline/css_selector_parser";
import { describe, expect, test } from "@odoo/hoot";

describe("CSS selector to AST and specificity computation (parseSelector)", () => {
    test("Baseline sanity", async () => {
        let selectorList = parseSelector("div");
        expect(selectorList.selector).toBe("div");
        expect(selectorList.specificity).toMatchObject([0, 0, 1]);

        selectorList = parseSelector(".a");
        expect(selectorList.selector).toBe(".a");
        expect(selectorList.specificity).toMatchObject([0, 1, 0]);

        selectorList = parseSelector("#id");
        expect(selectorList.selector).toBe("#id");
        expect(selectorList.specificity).toMatchObject([1, 0, 0]);

        selectorList = parseSelector("*");
        expect(selectorList.selector).toBe("*");
        expect(selectorList.specificity).toMatchObject([0, 0, 0]);
    });

    test("Selector lists (comma groups) + `max group wins`", async () => {
        const selectorList = parseSelector("div, #id, .class");
        expect(selectorList.selector).toBe("div,#id,.class");
        expect(selectorList.specificity).toMatchObject([1, 0, 0]);
    });

    test("Combinators + whitespace normalization", async () => {
        let selectorList = parseSelector("ul#nav li.active > a:hover");
        expect(selectorList.selector).toBe("ul#nav li.active>a:hover");
        expect(selectorList.specificity).toMatchObject([1, 2, 3]);

        selectorList = parseSelector(".row > *");
        expect(selectorList.selector).toBe(".row>*");
        expect(selectorList.specificity).toMatchObject([0, 1, 0]);

        selectorList = parseSelector("div>span");
        expect(selectorList.selector).toBe("div>span");
        expect(selectorList.specificity).toMatchObject([0, 0, 2]);

        selectorList = parseSelector("div     span");
        expect(selectorList.selector).toBe("div span");
        expect(selectorList.specificity).toMatchObject([0, 0, 2]);

        selectorList = parseSelector("div   >   span");
        expect(selectorList.selector).toBe("div>span");
        expect(selectorList.specificity).toMatchObject([0, 0, 2]);
    });

    test("Attribute selectors (quotes, escapes, operators)", async () => {
        let selectorList = parseSelector("[data-x]");
        expect(selectorList.selector).toBe("[data-x]");
        expect(selectorList.specificity).toMatchObject([0, 1, 0]);

        selectorList = parseSelector(`div[class~="x"][id="y"]`);
        expect(selectorList.selector).toBe(`div[class~="x"][id="y"]`);
        expect(selectorList.specificity).toMatchObject([0, 2, 1]);

        selectorList = parseSelector(`a[href^="https"]:not([download])`);
        expect(selectorList.selector).toBe(`a[href^="https"]:not([download])`);
        expect(selectorList.specificity).toMatchObject([0, 2, 1]);

        selectorList = parseSelector("[data-x='a\\]b']");
        expect(selectorList.selector).toBe("[data-x='a\\]b']");
        expect(selectorList.specificity).toMatchObject([0, 1, 0]);
    });

    test("Pseudo-elements + legacy pseudo-elements", async () => {
        let selectorList = parseSelector("a::before");
        expect(selectorList.selector).toBe("a::before");
        expect(selectorList.specificity).toMatchObject([0, 0, 2]);

        selectorList = parseSelector("a:before");
        expect(selectorList.selector).toBe("a::before");
        expect(selectorList.specificity).toMatchObject([0, 0, 2]);
    });

    test("Escapes in identifiers", async () => {
        let selectorList = parseSelector(".md\\:block");
        expect(selectorList.selector).toBe(".md\\:block");
        expect(selectorList.specificity).toMatchObject([0, 1, 0]);

        selectorList = parseSelector("#\\31 23");
        expect(selectorList.selector).toBe("#\\31 23");
        expect(selectorList.specificity).toMatchObject([1, 0, 0]);

        selectorList = parseSelector(".a\\+b");
        expect(selectorList.selector).toBe(".a\\+b");
        expect(selectorList.specificity).toMatchObject([0, 1, 0]);
    });

    describe("Pseudo-classes", () => {
        test(":where zeroes-out", async () => {
            let selectorList = parseSelector("*:where(#x.foo)");
            expect(selectorList.selector).toBe("*:where(#x.foo)");
            expect(selectorList.specificity).toMatchObject([0, 0, 0]);

            selectorList = parseSelector("div:where(.a, #b).c");
            expect(selectorList.selector).toBe("div:where(.a, #b).c");
            expect(selectorList.specificity).toMatchObject([0, 1, 1]);

            selectorList = parseSelector("a:not(:where(#x), .y)");
            expect(selectorList.selector).toBe("a:not(:where(#x), .y)");
            expect(selectorList.specificity).toMatchObject([0, 1, 1]);
        });

        test(":is()/:not() max-of-argument-list behavior", async () => {
            let selectorList = parseSelector(":is(.a, #b, div.c)");
            expect(selectorList.selector).toBe(":is(.a, #b, div.c)");
            expect(selectorList.specificity).toMatchObject([1, 0, 0]);

            selectorList = parseSelector("section:is(.a, #b)");
            expect(selectorList.selector).toBe("section:is(.a, #b)");
            expect(selectorList.specificity).toMatchObject([1, 0, 1]);

            selectorList = parseSelector(":not(.a, #b)");
            expect(selectorList.selector).toBe(":not(.a, #b)");
            expect(selectorList.specificity).toMatchObject([1, 0, 0]);

            selectorList = parseSelector(":is(:where(.a), :not(.b, #c))");
            expect(selectorList.selector).toBe(":is(:where(.a), :not(.b, #c))");
            expect(selectorList.specificity).toMatchObject([1, 0, 0]);

            selectorList = parseSelector(":not(:is(.a, .b), :where(#id))");
            expect(selectorList.selector).toBe(":not(:is(.a, .b), :where(#id))");
            expect(selectorList.specificity).toMatchObject([0, 1, 0]);
        });

        test(":has() (relative selectors, leading combinators)", async () => {
            let selectorList = parseSelector("div:has(> .item)");
            expect(selectorList.selector).toBe("div:has(> .item)");
            expect(selectorList.specificity).toMatchObject([0, 1, 1]);

            selectorList = parseSelector("div:has(> #x, .y)");
            expect(selectorList.selector).toBe("div:has(> #x, .y)");
            expect(selectorList.specificity).toMatchObject([1, 0, 1]);

            selectorList = parseSelector("div:has(> :not(.a, #b))");
            expect(selectorList.selector).toBe("div:has(> :not(.a, #b))");
            expect(selectorList.specificity).toMatchObject([1, 0, 1]);
        });

        test(":nth-child() and of <selector-list>", async () => {
            let selectorList = parseSelector("li:nth-child(2n+1)");
            expect(selectorList.selector).toBe("li:nth-child(2n+1)");
            expect(selectorList.specificity).toMatchObject([0, 1, 1]);

            selectorList = parseSelector("li:nth-child(2n+1 of .a, #b, div.c)");
            expect(selectorList.selector).toBe("li:nth-child(2n+1 of .a, #b, div.c)");
            expect(selectorList.specificity).toMatchObject([1, 1, 1]);

            selectorList = parseSelector("li:nth-child(n-1 of.a, #b, div.c)");
            expect(selectorList.selector).toBe("li:nth-child(n-1 of.a, #b, div.c)");
            expect(selectorList.specificity).toMatchObject([1, 1, 1]);

            selectorList = parseSelector(":nth-child(odd of .a, #b)");
            expect(selectorList.selector).toBe(":nth-child(odd of .a, #b)");
            expect(selectorList.specificity).toMatchObject([1, 1, 0]);

            selectorList = parseSelector(":nth-child(2n+1 of :not(.a, #b))");
            expect(selectorList.selector).toBe(":nth-child(2n+1 of :not(.a, #b))");
            expect(selectorList.specificity).toMatchObject([1, 1, 0]);

            selectorList = parseSelector(`:nth-child(2n+1 of [data-x="a of b"])`);
            expect(selectorList.selector).toBe(`:nth-child(2n+1 of [data-x="a of b"])`);
            expect(selectorList.specificity).toMatchObject([0, 2, 0]);

            selectorList = parseSelector(":nth-child(2n+1 of .a\\, .b)");
            expect(selectorList.selector).toBe(":nth-child(2n+1 of .a\\, .b)");
            expect(selectorList.specificity).toMatchObject([0, 3, 0]);
        });
    });
});

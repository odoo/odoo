import {
    advanceTime,
    afterEach,
    animationFrame,
    describe,
    expect,
    getFixture,
    test,
} from "@odoo/hoot";
import {
    DEBOUNCE,
    makeAsyncHandler,
    makeButtonHandler,
    PairSet,
    patchDynamicContent,
} from "@web/public/utils";

describe.current.tags("headless");

describe("PairSet", () => {
    test("can add and delete pairs", () => {
        const pairSet = new PairSet();

        const a = {};
        const b = {};
        expect(pairSet.has(a, b)).toBe(false);
        pairSet.add(a, b);
        expect(pairSet.has(a, b)).toBe(true);
        pairSet.delete(a, b);
        expect(pairSet.has(a, b)).toBe(false);
    });

    test("can add and delete pairs with the same first element", () => {
        const pairSet = new PairSet();

        const a = {};
        const b = {};
        const c = {};
        expect(pairSet.has(a, b)).toBe(false);
        expect(pairSet.has(a, c)).toBe(false);
        pairSet.add(a, b);
        expect(pairSet.has(a, b)).toBe(true);
        expect(pairSet.has(a, c)).toBe(false);
        pairSet.add(a, c);
        expect(pairSet.has(a, b)).toBe(true);
        expect(pairSet.has(a, c)).toBe(true);
        pairSet.delete(a, c);
        expect(pairSet.has(a, b)).toBe(true);
        expect(pairSet.has(a, c)).toBe(false);
        pairSet.delete(a, b);
        expect(pairSet.has(a, b)).toBe(false);
        expect(pairSet.has(a, c)).toBe(false);
    });

    test("do not duplicated pairs", () => {
        const pairSet = new PairSet();

        const a = {};
        const b = {};
        expect(pairSet.map.size).toBe(0);
        pairSet.add(a, b);
        expect(pairSet.map.size).toBe(1);
        pairSet.add(a, b);
        expect(pairSet.map.size).toBe(1);
    });
});

describe("make handlers", () => {
    let rejectPromise;
    afterEach(async () => {
        rejectPromise(new Error("reject"));
        await animationFrame();
        expect.verifyErrors(["reject"], {
            message: "There should be only one unhandledrejection error.",
        });
    });

    test("makeAsyncHandler does not retrigger the same error", async () => {
        expect.errors(1);
        const asyncHandler = makeAsyncHandler(
            () => new Promise((_, reject) => (rejectPromise = reject))
        );
        asyncHandler();
    });

    test("makeButtonHandler does not retrigger the same error", async () => {
        expect.errors(1);

        const fixture = getFixture();
        const button = document.createElement("button");
        fixture.appendChild(button);

        const buttonHandler = makeButtonHandler(
            () => new Promise((_, reject) => (rejectPromise = reject))
        );
        buttonHandler({ target: button });
        await advanceTime(DEBOUNCE + 1);
    });
});

describe("patch dynamic content", () => {
    test("patch applies new values", () => {
        const parent = {
            somewhere: {
                "t-att-doNotTouch": 123,
            },
        };
        const patch = {
            somewhere: {
                "t-att-class": () => ({
                    abc: true,
                }),
                "t-att-xyz": "123",
            },
            elsewhere: {
                "t-att-class": () => ({
                    xyz: true,
                }),
                "t-att-abc": "123",
            },
        };
        patchDynamicContent(parent, patch);
        expect(Object.keys(parent)).toEqual(["somewhere", "elsewhere"]);
        expect(Object.keys(parent.somewhere)).toEqual([
            "t-att-doNotTouch",
            "t-att-class",
            "t-att-xyz",
        ]);
        expect(Object.keys(parent.elsewhere)).toEqual(["t-att-class", "t-att-abc"]);
    });

    test("patch removes undefined values", () => {
        const parent = {
            somewhere: {
                "t-att-doNotTouch": 123,
                "t-att-removeMe": "abc",
            },
        };
        const patch = {
            somewhere: {
                "t-att-removeMe": undefined,
            },
        };
        patchDynamicContent(parent, patch);
        expect(parent).toEqual({
            somewhere: {
                "t-att-doNotTouch": 123,
            },
        });
    });

    test("patch combines function outputs", () => {
        const parent = {
            somewhere: {
                "t-att-style": () => ({
                    doNotTouch: true,
                    changeMe: 10,
                    doubleMe: 100,
                }),
            },
        };
        const patch = {
            somewhere: {
                "t-att-style": (el, old) => ({
                    changeMe: 50,
                    doubleMe: old.doubleMe * 2,
                    addMe: 1000,
                }),
            },
        };
        patchDynamicContent(parent, patch);
        expect(parent.somewhere["t-att-style"]()).toEqual({
            doNotTouch: true,
            changeMe: 50,
            doubleMe: 200,
            addMe: 1000,
        });
    });

    test("patch t-on-... provides access to super", () => {
        const parent = {
            somewhere: {
                "t-on-click": () => {
                    expect.step("base");
                },
            },
        };
        const patch = {
            somewhere: {
                "t-on-click": (el, oldFn) => {
                    oldFn();
                    expect.step("patch");
                },
            },
        };
        patchDynamicContent(parent, patch);
        parent.somewhere["t-on-click"]();
        expect.verifySteps(["base", "patch"]);
    });

    test("patch t-on-... does not require knowledge about there being a super", () => {
        const parent = {
            // No t-on-click here.
        };
        const patch = {
            somewhere: {
                "t-on-click": (el, oldFn) => {
                    oldFn();
                    expect.step("patch");
                },
            },
        };
        patchDynamicContent(parent, patch);
        parent.somewhere["t-on-click"]();
        expect.verifySteps(["patch"]);
    });
});

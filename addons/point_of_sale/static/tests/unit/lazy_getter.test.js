import { describe, expect, mountOnFixture, test } from "@odoo/hoot";
import { Component, onWillRender, reactive, useState, xml } from "@odoo/owl";
import { animationFrame } from "@odoo/hoot-mock";
import { WithLazyGetterTrap, clearGettersCache } from "@point_of_sale/lazy_getter";
import { patch } from "@web/core/utils/patch";
import { zip } from "@web/core/utils/arrays";

/**
 * This returns an object which provides a custom `step` and `verifySteps` behavior.
 * See the definition of each method for more details.
 */
function makeUnorderedVerifySteps() {
    let steps = [];
    return {
        step(val) {
            steps.push(val);
        },
        /**
         * Makes multiple assertions:
         * - Are all items in `vals` in steps?
         * - Are the items in `steps` ordered according to each item in `orderedValsArr`?
         * Then it clears the `steps`.
         * @param {any[]} vals
         * @param {any[][]} [orderedValsArr]
         */
        verifySteps(vals, orderedValsArr = []) {
            const stepsSet = new Set(steps);
            const valsSet = new Set(vals);
            vals.forEach((val) => expect(stepsSet.has(val)).toBe(true));
            steps.forEach((val) => expect(valsSet.has(val)).toBe(true));

            orderedValsArr.forEach((orderedVals) => {
                expect(
                    zip(orderedVals.slice(0, -1), orderedVals.slice(1)).reduce((acc, [a, b]) => {
                        return acc && steps.indexOf(a) < steps.indexOf(b);
                    }, true)
                ).toEqual(true);
            });

            steps = [];
        },
    };
}

const unorderedExpect = makeUnorderedVerifySteps();

class AppStore extends WithLazyGetterTrap {
    constructor() {
        super({ traps: {} });
        this.a = 0;
        this.b = 0;
        this.c = 0;
        this.d = 0;
    }
    get ab() {
        return this.a + this.b;
    }
    get abc() {
        let result = 0;
        for (let i = 0; i < 10; i++) {
            result += this.ab;
        }
        return result + this.c;
    }
    get bc() {
        return this.b + this.c;
    }
    get cd() {
        return this.c + this.d;
    }
    get x() {
        return this.abc + this.bc;
    }
    get y() {
        return this.cd + this.x;
    }
}

class WithStore extends Component {
    setup() {
        this.store = useState(this.env.store);
        onWillRender(() => this.onWillRender());
    }
    onWillRender() {}
}

class A extends WithStore {
    static template = xml`
    <span class="a">A: <t t-esc="this.store.a" /></span>
`;
}

class B extends WithStore {
    static template = xml`
    <span class="b">B: <t t-esc="this.store.b" /></span>
`;
}

class C extends WithStore {
    static template = xml`
    <span class="c">C: <t t-esc="this.store.c" /></span>
`;
}

class D extends WithStore {
    static template = xml`
    <span class="d">D: <t t-esc="this.store.d" /></span>
`;
}

class AB extends WithStore {
    static template = xml`
    <span class="ab">AB: <t t-esc="this.store.ab" /></span>
`;
}

class ABC extends WithStore {
    static template = xml`
    <span class="abc">ABC: <t t-esc="this.store.abc" /></span>
`;
}

class BC extends WithStore {
    static template = xml`
    <span class="bc">BC: <t t-esc="this.store.bc" /></span>
`;
}

class CD extends WithStore {
    static template = xml`
    <span class="cd">CD: <t t-esc="this.store.cd" /></span>
`;
}

class Root extends Component {
    static components = { A, B, C, D, AB, ABC, BC, CD };
    static template = xml`
    <div>
        <A />
        <B />
        <C />
        <D />
        <AB />
        <ABC />
        <BC />
        <CD />
    </div>
`;
}

describe("lazy getters", () => {
    test("each getter should only be called once and only when needed", async () => {
        const unpatch = patch(AppStore.prototype, {
            get ab() {
                unorderedExpect.step("ab");
                return super.ab;
            },
            get abc() {
                unorderedExpect.step("abc");
                return super.abc;
            },
            get bc() {
                unorderedExpect.step("bc");
                return super.bc;
            },
            get cd() {
                unorderedExpect.step("cd");
                return super.cd;
            },
        });

        const store = reactive(new AppStore());

        await mountOnFixture(Root, { env: { store }, warnIfNoStaticProps: false });

        unorderedExpect.verifySteps(["ab", "abc", "bc", "cd"]);

        store.a = 1;

        // Before rerendering, the getters should not be called
        unorderedExpect.verifySteps([]);

        await animationFrame();
        // Only during rerendering that the getters are called
        unorderedExpect.verifySteps(["ab", "abc"]);

        store.b = 1;
        unorderedExpect.verifySteps([]);
        await animationFrame();
        unorderedExpect.verifySteps(["bc", "ab", "abc"]);

        store.c = 1;
        unorderedExpect.verifySteps([]);
        await animationFrame();
        unorderedExpect.verifySteps(["cd", "bc", "abc"]);

        store.d = 1;
        unorderedExpect.verifySteps([]);
        await animationFrame();
        unorderedExpect.verifySteps(["cd"]);

        unpatch();
        clearGettersCache();
    });

    test("only dependent components rerender", async () => {
        const unpatches = [A, B, C, D, AB, ABC, CD, BC].map((Class) => {
            return patch(Class.prototype, {
                onWillRender() {
                    unorderedExpect.step(Class);
                    return super.onWillRender();
                },
            });
        });

        const store = reactive(new AppStore());
        await mountOnFixture(Root, { env: { store }, warnIfNoStaticProps: false });
        unorderedExpect.verifySteps([A, B, C, D, AB, ABC, BC, CD]);

        store.a = 1;
        await animationFrame();
        unorderedExpect.verifySteps([A, AB, ABC]);

        store.b = 1;
        await animationFrame();
        unorderedExpect.verifySteps([B, AB, ABC, BC]);

        store.c = 1;
        await animationFrame();
        unorderedExpect.verifySteps([C, ABC, BC, CD]);

        store.d = 1;
        await animationFrame();
        unorderedExpect.verifySteps([D, CD]);

        for (const unpatch of unpatches) {
            unpatch();
        }
        clearGettersCache();
    });

    test("only dependent getters are called and in correct order", () => {
        clearGettersCache();

        const unpatch = patch(AppStore.prototype, {
            get ab() {
                const result = super.ab;
                unorderedExpect.step("ab");
                return result;
            },
            get abc() {
                const result = super.abc;
                unorderedExpect.step("abc");
                return result;
            },
            get bc() {
                const result = super.bc;
                unorderedExpect.step("bc");
                return result;
            },
            get cd() {
                const result = super.cd;
                unorderedExpect.step("cd");
                return result;
            },
            get x() {
                const result = super.x;
                unorderedExpect.step("x");
                return result;
            },
            get y() {
                const result = super.y;
                unorderedExpect.step("y");
                return result;
            },
        });
        const store = reactive(new AppStore());

        expect(store.y).toBe(0);
        unorderedExpect.verifySteps(["ab", "bc", "cd", "abc", "x", "y"], [["ab", "abc", "x", "y"]]);

        store.a = 1;
        expect(store.y).toBe(10);
        unorderedExpect.verifySteps(["ab", "abc", "x", "y"], [["ab", "abc", "x", "y"]]);

        store.b = 1;
        expect(store.y).toBe(21);
        unorderedExpect.verifySteps(
            ["ab", "bc", "abc", "x", "y"],
            [
                ["ab", "abc", "x", "y"],
                ["bc", "x", "y"],
            ]
        );

        store.c = 1;
        expect(store.y).toBe(24);
        unorderedExpect.verifySteps(
            ["abc", "bc", "cd", "x", "y"],
            [
                ["abc", "x", "y"],
                ["bc", "x", "y"],
                ["cd", "y"],
            ]
        );

        store.d = 1;
        expect(store.y).toBe(25);
        unorderedExpect.verifySteps(["cd", "y"], [["cd", "y"]]);

        unpatch();
        clearGettersCache();
    });
});

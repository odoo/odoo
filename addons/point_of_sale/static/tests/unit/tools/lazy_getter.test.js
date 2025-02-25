import { afterEach, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { Component, onWillRender, reactive, useState, xml } from "@odoo/owl";
import {
    mountWithCleanup,
    allowTranslations,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

import {
    WithLazyGetterTrap,
    clearGettersCache,
    createLazyGetter,
} from "@point_of_sale/lazy_getter";
import { zip } from "@web/core/utils/arrays";

/**
 * @param {string} value
 */
function unorderedStep(value) {
    unorderedSteps.push(value);
}

/**
 * Makes multiple assertions:
 * - Are all items in `vals` in steps?
 * - Are the items in `steps` ordered according to each item in `stepOrders`?
 * Then it clears the `steps`.
 * @param {string[]} expectedSteps
 * @param {Iterable<string[]>} [stepOrders=[]]
 */
function verifyUnorderedSteps(expectedSteps, stepOrders = []) {
    expect([...unorderedSteps].sort()).toEqual([...expectedSteps].sort());
    for (const stepOrder of stepOrders) {
        expect(
            zip(stepOrder.slice(0, -1), stepOrder.slice(1)).reduce(
                (acc, [a, b]) => acc && unorderedSteps.indexOf(a) < unorderedSteps.indexOf(b),
                true
            )
        ).toBe(true);
    }
    unorderedSteps = [];
}

let unorderedSteps = [];

allowTranslations();
afterEach(clearGettersCache);

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
    static props = {};
    static template = xml`
        <span t-att-class="property">
            <t t-esc="constructor.name" />: <t t-esc="this.store[property]" />
        </span>
    `;

    property = "";

    setup() {
        this.store = useState(this.env.store);
        onWillRender(() => this.onWillRender());
    }

    onWillRender() {}
}

class A extends WithStore {
    property = "a";
}

class B extends WithStore {
    property = "b";
}

class C extends WithStore {
    property = "c";
}

class D extends WithStore {
    property = "d";
}

class AB extends WithStore {
    property = "ab";
}

class ABC extends WithStore {
    property = "abc";
}

class BC extends WithStore {
    property = "bc";
}

class CD extends WithStore {
    property = "cd";
}

class Root extends Component {
    static components = { A, B, C, D, AB, ABC, BC, CD };
    static props = {};
    static template = xml`
        <t t-foreach="constructor.components" t-as="key" t-key="key">
            <t t-component="constructor.components[key]" />
        </t>
    `;
}

test("each getter should only be called once and only when needed", async () => {
    patchWithCleanup(AppStore.prototype, {
        get ab() {
            unorderedStep("ab");
            return super.ab;
        },
        get abc() {
            unorderedStep("abc");
            return super.abc;
        },
        get bc() {
            unorderedStep("bc");
            return super.bc;
        },
        get cd() {
            unorderedStep("cd");
            return super.cd;
        },
    });

    const store = reactive(new AppStore());
    await mountWithCleanup(Root, {
        env: { store },
        noMainContainer: true,
    });

    verifyUnorderedSteps(["ab", "abc", "bc", "cd"]);

    store.a = 1;

    // Getters should only be called after an interface re-render
    verifyUnorderedSteps([]);
    await animationFrame();
    verifyUnorderedSteps(["ab", "abc"]);

    store.b = 1;

    verifyUnorderedSteps([]);
    await animationFrame();
    verifyUnorderedSteps(["bc", "ab", "abc"]);

    store.c = 1;

    verifyUnorderedSteps([]);
    await animationFrame();
    verifyUnorderedSteps(["cd", "bc", "abc"]);

    store.d = 1;

    verifyUnorderedSteps([]);
    await animationFrame();
    verifyUnorderedSteps(["cd"]);
});

test("only dependent components rerender", async () => {
    patchWithCleanup(WithStore.prototype, {
        onWillRender() {
            unorderedStep(this.property);
        },
    });

    const store = reactive(new AppStore());
    await mountWithCleanup(Root, {
        env: { store },
        noMainContainer: true,
    });

    verifyUnorderedSteps(["a", "b", "c", "d", "ab", "abc", "bc", "cd"]);

    store.a = 1;
    await animationFrame();

    verifyUnorderedSteps(["a", "ab", "abc"]);

    store.b = 1;
    await animationFrame();

    verifyUnorderedSteps(["b", "ab", "abc", "bc"]);

    store.c = 1;
    await animationFrame();

    verifyUnorderedSteps(["c", "abc", "bc", "cd"]);

    store.d = 1;
    await animationFrame();

    verifyUnorderedSteps(["d", "cd"]);
});

test("only dependent getters are called and in correct order", () => {
    patchWithCleanup(AppStore.prototype, {
        get ab() {
            const result = super.ab;
            unorderedStep("ab");
            return result;
        },
        get abc() {
            const result = super.abc;
            unorderedStep("abc");
            return result;
        },
        get bc() {
            const result = super.bc;
            unorderedStep("bc");
            return result;
        },
        get cd() {
            const result = super.cd;
            unorderedStep("cd");
            return result;
        },
        get x() {
            const result = super.x;
            unorderedStep("x");
            return result;
        },
        get y() {
            const result = super.y;
            unorderedStep("y");
            return result;
        },
    });
    const store = reactive(new AppStore());

    expect(store.y).toBe(0);
    verifyUnorderedSteps(["ab", "bc", "cd", "abc", "x", "y"], [["ab", "abc", "x", "y"]]);

    store.a = 1;

    expect(store.y).toBe(10);
    verifyUnorderedSteps(["ab", "abc", "x", "y"], [["ab", "abc", "x", "y"]]);

    store.b = 1;
    expect(store.y).toBe(21);

    verifyUnorderedSteps(
        ["ab", "bc", "abc", "x", "y"],
        [
            ["ab", "abc", "x", "y"],
            ["bc", "x", "y"],
        ]
    );

    store.c = 1;
    expect(store.y).toBe(24);

    verifyUnorderedSteps(
        ["abc", "bc", "cd", "x", "y"],
        [
            ["abc", "x", "y"],
            ["bc", "x", "y"],
            ["cd", "y"],
        ]
    );

    store.d = 1;
    expect(store.y).toBe(25);

    verifyUnorderedSteps(["cd", "y"], [["cd", "y"]]);
});

test("dynamically creates a lazy getter", () => {
    class DemoClass extends WithLazyGetterTrap {
        constructor(params = {}) {
            super(params);
        }
    }

    const reactiveObj = reactive(new DemoClass());
    reactiveObj.name = "demo";

    let computeCallCount = 0;
    function computeValue() {
        computeCallCount++;
        return "Hello " + this.name;
    }

    createLazyGetter(reactiveObj, "hello", computeValue);

    expect(reactiveObj.hello).toBe("Hello demo");
    expect(computeCallCount).toBe(1);

    // On the second call, the computed method is not executed again.
    expect(reactiveObj.hello).toBe("Hello demo");
    expect(computeCallCount).toBe(1);

    // Modifying the value will invalidate the computed value
    expect(computeCallCount).toBe(1);
    reactiveObj.name = "World";
    expect(reactiveObj.hello).toBe("Hello World");
    expect(computeCallCount).toBe(2);

    reactiveObj.notRelatedValue = 1;
    expect(reactiveObj.hello).toBe("Hello World");
    expect(computeCallCount).toBe(2);
});

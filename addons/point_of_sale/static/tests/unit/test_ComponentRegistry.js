/** @odoo-module */

import Registries from "@point_of_sale/js/Registries";

QUnit.module("unit tests for ComponentRegistry", {
    before() {},
});

QUnit.test("basic extend", async function (assert) {
    assert.expect(5);

    class A {
        constructor() {
            assert.step("A");
        }
    }
    Registries.Component.add(A);

    const A1 = (x) =>
        class extends x {
            constructor() {
                super();
                assert.step("A1");
            }
        };
    Registries.Component.extend(A, A1);

    Registries.Component.freeze();

    const RegA = Registries.Component.get(A);
    const a = new RegA();
    assert.verifySteps(["A", "A1"]);
    assert.ok(a instanceof RegA);
    assert.ok(RegA.name === "A");
});

QUnit.test("addByExtending", async function (assert) {
    assert.expect(8);

    class A {
        constructor() {
            assert.step("A");
        }
    }
    Registries.Component.add(A);

    const B = (x) =>
        class extends x {
            constructor() {
                super();
                assert.step("B");
            }
        };
    Registries.Component.addByExtending(B, A);

    const A1 = (x) =>
        class extends x {
            constructor() {
                super();
                assert.step("A1");
            }
        };
    Registries.Component.extend(A, A1);

    const A2 = (x) =>
        class extends x {
            constructor() {
                super();
                assert.step("A2");
            }
        };
    Registries.Component.extend(A, A2);

    Registries.Component.freeze();

    const RegA = Registries.Component.get(A);
    const RegB = Registries.Component.get(B);
    const b = new RegB();
    assert.verifySteps(["A", "A1", "A2", "B"]);
    assert.ok(b instanceof RegA);
    assert.ok(b instanceof RegB);
    assert.ok(RegB.name === "B");
});

QUnit.test("extend the one that is added by extending", async function (assert) {
    assert.expect(6);

    class A {
        constructor() {
            assert.step("A");
        }
    }
    Registries.Component.add(A);

    const B = (x) =>
        class extends x {
            constructor() {
                super();
                assert.step("B");
            }
        };
    Registries.Component.addByExtending(B, A);

    const B1 = (x) =>
        class extends x {
            constructor() {
                super();
                assert.step("B1");
            }
        };
    Registries.Component.extend(B, B1);

    const B2 = (x) =>
        class extends x {
            constructor() {
                super();
                assert.step("B2");
            }
        };
    Registries.Component.extend(B, B2);

    const A1 = (x) =>
        class extends x {
            constructor() {
                super();
                assert.step("A1");
            }
        };
    Registries.Component.extend(A, A1);

    Registries.Component.freeze();

    const RegB = Registries.Component.get(B);
    new RegB();
    assert.verifySteps(["A", "A1", "B", "B1", "B2"]);
});

QUnit.test("addByExtending based on added by extending", async function (assert) {
    assert.expect(10);

    class A {
        constructor() {
            assert.step("A");
        }
    }
    Registries.Component.add(A);

    const B = (x) =>
        class extends x {
            constructor() {
                super();
                assert.step("B");
            }
        };
    Registries.Component.addByExtending(B, A);

    const A1 = (x) =>
        class extends x {
            constructor() {
                super();
                assert.step("A1");
            }
        };
    Registries.Component.extend(A, A1);

    const C = (x) =>
        class extends x {
            constructor() {
                super();
                assert.step("C");
            }
        };
    Registries.Component.addByExtending(C, B);

    const B7 = (x) =>
        class extends x {
            constructor() {
                super();
                assert.step("B7");
            }
        };
    Registries.Component.extend(B, B7);

    Registries.Component.freeze();

    const RegA = Registries.Component.get(A);
    const RegB = Registries.Component.get(B);
    const RegC = Registries.Component.get(C);
    const c = new RegC();
    assert.verifySteps(["A", "A1", "B", "B7", "C"]);
    assert.ok(c instanceof RegA);
    assert.ok(c instanceof RegB);
    assert.ok(c instanceof RegC);
    assert.ok(RegC.name === "C");
});

QUnit.test("deeper inheritance", async function (assert) {
    assert.expect(9);

    class A {
        constructor() {
            assert.step("A");
        }
    }
    Registries.Component.add(A);

    const B = (x) =>
        class extends x {
            constructor() {
                super();
                assert.step("B");
            }
        };
    Registries.Component.addByExtending(B, A);

    const A1 = (x) =>
        class extends x {
            constructor() {
                super();
                assert.step("A1");
            }
        };
    Registries.Component.extend(A, A1);

    const C = (x) =>
        class extends x {
            constructor() {
                super();
                assert.step("C");
            }
        };
    Registries.Component.addByExtending(C, B);

    const B2 = (x) =>
        class extends x {
            constructor() {
                super();
                assert.step("B2");
            }
        };
    Registries.Component.extend(B, B2);

    const B3 = (x) =>
        class extends x {
            constructor() {
                super();
                assert.step("B3");
            }
        };
    Registries.Component.extend(B, B3);

    const A9 = (x) =>
        class extends x {
            constructor() {
                super();
                assert.step("A9");
            }
        };
    Registries.Component.extend(A, A9);

    const E = (x) =>
        class extends x {
            constructor() {
                super();
                assert.step("E");
            }
        };
    Registries.Component.addByExtending(E, C);

    Registries.Component.freeze();

    // |A| => A9 -> A1 -> A
    // |B| => B3 -> B2 -> B -> |A|
    // |C| => C -> |B|
    // |E| => E -> |C|

    new (Registries.Component.get(E))();
    assert.verifySteps(["A", "A1", "A9", "B", "B2", "B3", "C", "E"]);
});

QUnit.test("mixins?", async function (assert) {
    assert.expect(12);

    let A = class A {
        constructor() {
            assert.step("A");
        }
    };
    Registries.Component.add(A);

    const Mixin = (x) =>
        class extends x {
            constructor() {
                super();
                assert.step("Mixin");
            }
            mixinMethod() {
                return "mixinMethod";
            }
            get mixinGetter() {
                return "mixinGetter";
            }
        };

    // use the mixin when declaring B.
    let B = (x) =>
        class extends Mixin(x) {
            constructor() {
                super();
                assert.step("B");
            }
        };
    Registries.Component.addByExtending(B, A);

    const A1 = (x) =>
        class extends x {
            constructor() {
                super();
                assert.step("A1");
            }
        };
    Registries.Component.extend(A, A1);

    Registries.Component.freeze();

    B = Registries.Component.get(B);
    const b = new B();
    assert.verifySteps(["A", "A1", "Mixin", "B"]);
    // instance of B should have the mixin properties
    assert.strictEqual(b.mixinMethod(), "mixinMethod");
    assert.strictEqual(b.mixinGetter, "mixinGetter");

    // instance of A should not have the mixin properties
    A = Registries.Component.get(A);
    const a = new A();
    assert.verifySteps(["A", "A1"]);
    assert.notOk(a.mixinMethod);
    assert.notOk(a.mixinGetter);
});

QUnit.test("extending methods", async function (assert) {
    assert.expect(16);

    let A = class A {
        foo() {
            assert.step("A foo");
        }
    };
    Registries.Component.add(A);

    let B = (x) =>
        class extends x {
            bar() {
                assert.step("B bar");
            }
        };
    Registries.Component.addByExtending(B, A);

    const A1 = (x) =>
        class extends x {
            bar() {
                assert.step("A1 bar");
                // should only be for A.
            }
        };
    Registries.Component.extend(A, A1);

    const B1 = (x) =>
        class extends x {
            foo() {
                super.foo();
                assert.step("B1 foo");
            }
        };
    Registries.Component.extend(B, B1);

    let C = (x) =>
        class extends x {
            foo() {
                super.foo();
                assert.step("C foo");
            }
            bar() {
                super.bar();
                assert.step("C bar");
            }
        };
    Registries.Component.addByExtending(C, B);

    Registries.Component.freeze();

    A = Registries.Component.get(A);
    B = Registries.Component.get(B);
    C = Registries.Component.get(C);
    const a = new A();
    const b = new B();
    const c = new C();

    a.foo();
    assert.verifySteps(["A foo"]);
    b.foo();
    assert.verifySteps(["A foo", "B1 foo"]);
    c.foo();
    assert.verifySteps(["A foo", "B1 foo", "C foo"]);

    a.bar();
    assert.verifySteps(["A1 bar"]);
    b.bar();
    assert.verifySteps(["B bar"]);
    c.bar();
    assert.verifySteps(["B bar", "C bar"]);
});

odoo.define("web.patchMixin_tests", function (require) {
"use strict";

const patchMixin = require('web.patchMixin');

QUnit.module('core', {}, function () {

    QUnit.module('patchMixin', {}, function () {

        QUnit.test('basic use', function (assert) {
            assert.expect(4);

            const A = patchMixin(
                class {
                    constructor() {
                        assert.step('A.constructor');
                    }
                    f() {
                        assert.step('A.f');
                    }
                }
            );

            const a = new A();
            a.f();

            assert.ok(a instanceof A);
            assert.verifySteps([
                'A.constructor',
                'A.f',
            ]);
        });

        QUnit.test('simple patch', function (assert) {
            assert.expect(5);

            const A = patchMixin(
                class {
                    constructor() {
                        assert.step('A.constructor');
                    }
                    f() {
                        assert.step('A.f');
                    }
                }
            );

            A.patch('patch', T =>
                class extends T {
                    constructor() {
                        super();
                        assert.step('patch.constructor');
                    }
                    f() {
                        super.f();
                        assert.step('patch.f');
                    }
                }
            );

            (new A()).f();

            assert.verifySteps([
                'A.constructor',
                'patch.constructor',
                'A.f',
                'patch.f',
            ]);
        });

        QUnit.test('two patches on same base class', function (assert) {
            assert.expect(7);

            const A = patchMixin(
                class {
                    constructor() {
                        assert.step('A.constructor');
                    }
                    f() {
                        assert.step('A.f');
                    }
                }
            );

            A.patch('patch1', T =>
                class extends T {
                    constructor() {
                        super();
                        assert.step('patch1.constructor');
                    }
                    f() {
                        super.f();
                        assert.step('patch1.f');
                    }
                }
            );

            A.patch('patch2', T =>
                class extends T {
                    constructor() {
                        super();
                        assert.step('patch2.constructor');
                    }
                    f() {
                        super.f();
                        assert.step('patch2.f');
                    }
                }
            );

            (new A()).f();

            assert.verifySteps([
                'A.constructor',
                'patch1.constructor',
                'patch2.constructor',
                'A.f',
                'patch1.f',
                'patch2.f',
            ]);
        });

        QUnit.test('two patches with same name on same base class', function (assert) {
            assert.expect(1);

            const A = patchMixin(class {});

            A.patch('patch', T => class extends T {});

            // keys should be unique
            assert.throws(() => {
                A.patch('patch', T => class extends T {});
            });
        });

        QUnit.test('unpatch', function (assert) {
            assert.expect(8);

            const A = patchMixin(
                class {
                    constructor() {
                        assert.step('A.constructor');
                    }
                    f() {
                        assert.step('A.f');
                    }
                }
            );

            A.patch('patch', T =>
                class extends T {
                    constructor() {
                        super();
                        assert.step('patch.constructor');
                    }
                    f() {
                        super.f();
                        assert.step('patch.f');
                    }
                }
            );

            (new A()).f();

            assert.verifySteps([
                'A.constructor',
                'patch.constructor',
                'A.f',
                'patch.f',
            ]);

            A.unpatch('patch');

            (new A()).f();

            assert.verifySteps([
                'A.constructor',
                'A.f',
            ]);
        });

        QUnit.test('unpatch 2', function (assert) {
            assert.expect(12);

            const A = patchMixin(
                class {
                    constructor() {
                        assert.step('A.constructor');
                    }
                    f() {
                        assert.step('A.f');
                    }
                }
            );

            A.patch('patch1', T =>
                class extends T {
                    constructor() {
                        super();
                        assert.step('patch1.constructor');
                    }
                    f() {
                        super.f();
                        assert.step('patch1.f');
                    }
                }
            );

            A.patch('patch2', T =>
                class extends T {
                    constructor() {
                        super();
                        assert.step('patch2.constructor');
                    }
                    f() {
                        super.f();
                        assert.step('patch2.f');
                    }
                }
            );

            (new A()).f();

            assert.verifySteps([
                'A.constructor',
                'patch1.constructor',
                'patch2.constructor',
                'A.f',
                'patch1.f',
                'patch2.f',
            ]);

            A.unpatch('patch1');

            (new A()).f();

            assert.verifySteps([
                'A.constructor',
                'patch2.constructor',
                'A.f',
                'patch2.f',
            ]);
        });

        QUnit.test('unpatch inexistent', function (assert) {
            assert.expect(1);

            const A = patchMixin(class {});
            A.patch('patch', T => class extends T {});

            A.unpatch('patch');
            assert.throws(() => {
                A.unpatch('inexistent-patch');
            });
        });

        QUnit.test('patch for specialization', function (assert) {
            assert.expect(1);

            let args = [];

            const A = patchMixin(
                class {
                    constructor() {
                        args = ['A', ...arguments];
                    }
                }
            );

            A.patch('patch', T =>
                class extends T {
                    constructor() {
                        super('patch', ...arguments);
                    }
                }
            );

            new A('instantiation');

            assert.deepEqual(args, ['A', 'patch', 'instantiation']);
        });

        QUnit.test('instance fields', function (assert) {
            assert.expect(1);

            const A = patchMixin(
                class {
                    constructor() {
                        this.x = ['A'];
                    }
                }
            );

            A.patch('patch', T =>
                class extends T {
                    constructor() {
                        super();
                        this.x.push('patch');
                    }
                }
            );

            const a = new A();
            assert.deepEqual(a.x, ['A', 'patch']);
        });

        QUnit.test('call instance method defined in patch', function (assert) {
            assert.expect(3);

            const A = patchMixin(
                class {}
            );

            assert.notOk((new A()).f);

            A.patch('patch', T =>
                class extends T {
                    f() {
                        assert.step('patch.f');
                    }
                }
            );

            (new A()).f();
            assert.verifySteps(['patch.f']);
        });

        QUnit.test('class methods', function (assert) {
            assert.expect(7);

            const A = patchMixin(
                class {
                    static f() {
                        assert.step('A');
                    }
                }
            );

            A.f();
            assert.verifySteps(['A']);

            A.patch('patch', T =>
                class extends T {
                    static f() {
                        super.f();
                        assert.step('patch');
                    }
                }
            );

            A.f();
            assert.verifySteps(['A', 'patch']);

            A.unpatch('patch');

            A.f();
            assert.verifySteps(['A']);
        });

        QUnit.test('class fields', function (assert) {
            assert.expect(4);

            class A {}
            A.foo = ['A'];
            A.bar = 'A';

            const PatchableA = patchMixin(A);

            PatchableA.patch('patch', T => {
                class Patch extends T {}

                Patch.foo = [...T.foo, 'patched A'];
                Patch.bar = 'patched A';

                return Patch;
            });

            assert.deepEqual(PatchableA.foo, ['A', 'patched A']);
            assert.strictEqual(PatchableA.bar, 'patched A');

            PatchableA.unpatch('patch');

            assert.deepEqual(PatchableA.foo, ['A']);
            assert.strictEqual(PatchableA.bar, 'A');
        });

        QUnit.test('lazy patch', function (assert) {
            assert.expect(4);

            const A = patchMixin(
                class {
                    constructor() {
                        assert.step('A.constructor');
                    }
                    f() {
                        assert.step('A.f');
                    }
                }
            );

            const a = new A();

            A.patch('patch', T =>
                class extends T {
                    constructor() {
                        super();
                        // will not be called
                        assert.step('patch.constructor');
                    }
                    f() {
                        super.f();
                        assert.step('patch.f');
                    }
                }
            );

            a.f();

            assert.verifySteps([
                'A.constructor',
                'A.f',
                'patch.f',
            ]);
        });


        QUnit.module('inheritance');

        QUnit.test('inheriting a patchable class', function (assert) {
            assert.expect(8);

            const A = patchMixin(
                class {
                    constructor() {
                        assert.step('A.constructor');
                    }
                    f() {
                        assert.step('A.f');
                    }
                }
            );

            class B extends A {
                constructor() {
                    super();
                    assert.step('B.constructor');
                }
                f() {
                    super.f();
                    assert.step('B.f');
                }
            }

            (new A()).f();

            assert.verifySteps([
                'A.constructor',
                'A.f',
            ]);

            (new B()).f();

            assert.verifySteps([
                'A.constructor',
                'B.constructor',
                'A.f',
                'B.f',
            ]);
        });

        QUnit.test('inheriting a patchable class that has patch', function (assert) {
            assert.expect(12);

            const A = patchMixin(
                class {
                    constructor() {
                        assert.step('A.constructor');
                    }
                    f() {
                        assert.step('A.f');
                    }
                }
            );

            A.patch('patch', T =>
                class extends T {
                    constructor() {
                        super();
                        assert.step('patch.constructor');
                    }
                    f() {
                        super.f();
                        assert.step('patch.f');
                    }
                }
            );

            class B extends A {
                constructor() {
                    super();
                    assert.step('B.constructor');
                }
                f() {
                    super.f();
                    assert.step('B.f');
                }
            }

            (new A()).f();

            assert.verifySteps([
                'A.constructor',
                'patch.constructor',
                'A.f',
                'patch.f',
            ]);

            (new B()).f();

            assert.verifySteps([
                'A.constructor',
                'patch.constructor',
                'B.constructor',
                'A.f',
                'patch.f',
                'B.f',
            ]);
        });

        QUnit.test('patch inherited patchable class', function (assert) {
            assert.expect(10);

            const A = patchMixin(
                class {
                    constructor() {
                        assert.step('A.constructor');
                    }
                    f() {
                        assert.step('A.f');
                    }
                }
            );

            const B = patchMixin(
                class extends A {
                    constructor() {
                        super();
                        assert.step('B.constructor');
                    }
                    f() {
                        super.f();
                        assert.step('B.f');
                    }
                }
            );

            B.patch('patch', T =>
                class extends T {
                    constructor() {
                        super();
                        assert.step('patch.constructor');
                    }
                    f() {
                        super.f();
                        assert.step('patch.f');
                    }
                }
            );

            (new A()).f();

            assert.verifySteps([
                'A.constructor',
                'A.f',
            ]);

            (new B()).f();

            assert.verifySteps([
                'A.constructor',
                'B.constructor',
                'patch.constructor',
                'A.f',
                'B.f',
                'patch.f',
            ]);
        });

        QUnit.test('patch inherited patched class', function (assert) {
            assert.expect(14);

            const A = patchMixin(
                class {
                    constructor() {
                        assert.step('A.constructor');
                    }
                    f() {
                        assert.step('A.f');
                    }
                }
            );

            A.patch('patch', T =>
                class extends T {
                    constructor() {
                        super();
                        assert.step('A.patch.constructor');
                    }
                    f() {
                        super.f();
                        assert.step('A.patch.f');
                    }
                }
            );

            /**
             * /!\ WARNING /!\
             *
             * If you want to patch class B, make it patchable
             * otherwise it will patch class A!
             */
            const B = patchMixin(
                class extends A {
                    constructor() {
                        super();
                        assert.step('B.constructor');
                    }
                    f() {
                        super.f();
                        assert.step('B.f');
                    }
                }
            );

            B.patch('patch', T =>
                class extends T {
                    constructor() {
                        super();
                        assert.step('B.patch.constructor');
                    }
                    f() {
                        super.f();
                        assert.step('B.patch.f');
                    }
                }
            );

            const a = new A();
            a.f();

            assert.verifySteps([
                'A.constructor',
                'A.patch.constructor',
                'A.f',
                'A.patch.f',
            ]);

            const b = new B();
            b.f();

            assert.verifySteps([
                'A.constructor',
                'A.patch.constructor',
                'B.constructor',
                'B.patch.constructor',
                'A.f',
                'A.patch.f',
                'B.f',
                'B.patch.f',
            ]);
        });

        QUnit.test('unpatch inherited patched class', function (assert) {
            assert.expect(15);

            const A = patchMixin(
                class {
                    constructor() {
                        assert.step('A.constructor');
                    }
                    f() {
                        assert.step('A.f');
                    }
                }
            );

            A.patch('patch', T =>
                class extends T {
                    constructor() {
                        super();
                        assert.step('A.patch.constructor');
                    }
                    f() {
                        super.f();
                        assert.step('A.patch.f');
                    }
                }
            );

            const B = patchMixin(
                class extends A {
                    constructor() {
                        super();
                        assert.step('B.constructor');
                    }
                    f() {
                        super.f();
                        assert.step('B.f');
                    }
                }
            );

            B.patch('patch', T =>
                class extends T {
                    constructor() {
                        super();
                        assert.step('B.patch.constructor');
                    }
                    f() {
                        super.f();
                        assert.step('B.patch.f');
                    }
                }
            );

            A.unpatch('patch');

            (new A()).f();

            assert.verifySteps([
                'A.constructor',
                'A.f',
            ]);

            (new B()).f();

            assert.verifySteps([
                'A.constructor',
                'B.constructor',
                'B.patch.constructor',
                'A.f',
                'B.f',
                'B.patch.f',
            ]);

            B.unpatch('patch');

            (new B()).f();

            assert.verifySteps([
                'A.constructor',
                'B.constructor',
                'A.f',
                'B.f',
            ]);
        });

        QUnit.test('unpatch inherited patched class 2', function (assert) {
            assert.expect(12);

            const A = patchMixin(
                class {
                    constructor() {
                        assert.step('A.constructor');
                    }
                    f() {
                        assert.step('A.f');
                    }
                }
            );

            A.patch('patch', T =>
                class extends T {
                    constructor() {
                        super();
                        assert.step('A.patch.constructor');
                    }
                    f() {
                        super.f();
                        assert.step('A.patch.f');
                    }
                }
            );

            const B = patchMixin(
                class extends A {
                    constructor() {
                        super();
                        assert.step('B.constructor');
                    }
                    f() {
                        super.f();
                        assert.step('B.f');
                    }
                }
            );

            B.patch('patch', T =>
                class extends T {
                    constructor() {
                        super();
                        assert.step('B.patch.constructor');
                    }
                    f() {
                        super.f();
                        assert.step('B.patch.f');
                    }
                }
            );

            B.unpatch('patch');

            (new B()).f();

            assert.verifySteps([
                'A.constructor',
                'A.patch.constructor',
                'B.constructor',
                'A.f',
                'A.patch.f',
                'B.f',
            ]);

            A.unpatch('patch');

            (new B()).f();

            assert.verifySteps([
                'A.constructor',
                'B.constructor',
                'A.f',
                'B.f',
            ]);
        });

        QUnit.test('class methods', function (assert) {
            assert.expect(12);

            const A = patchMixin(
                class {
                    static f() {
                        assert.step('A');
                    }
                }
            );

            const B = patchMixin(
                class extends A {
                    static f() {
                        super.f();
                        assert.step('B');
                    }
                }
            );

            A.patch('patch', T =>
                class extends T {
                    static f() {
                        super.f();
                        assert.step('A.patch');
                    }
                }
            );

            B.patch('patch', T =>
                class extends T {
                    static f() {
                        super.f();
                        assert.step('B.patch');
                    }
                }
            );

            B.f();
            assert.verifySteps(['A', 'A.patch', 'B', 'B.patch']);

            A.unpatch('patch');

            B.f();
            assert.verifySteps(['A', 'B', 'B.patch']);

            B.unpatch('patch');

            B.f();
            assert.verifySteps(['A', 'B']);
        });

        QUnit.test('class fields', function (assert) {
            assert.expect(3);

            class A {}
            A.foo = ['A'];
            A.bar = 'A';

            const PatchableA = patchMixin(A);

            class B extends PatchableA {}
            // /!\ This is not dynamic
            // so if A.foo is patched after this assignment
            // B.foo won't have the patches of A.foo
            B.foo = [...PatchableA.foo, 'B'];
            B.bar = 'B';

            const PatchableB = patchMixin(B);

            PatchableA.patch('patch', T => {
                class Patch extends T {}

                Patch.foo = [...T.foo, 'patched A'];
                Patch.bar = 'patched A';

                return Patch;
            });

            PatchableB.patch('patch', T => {
                class Patch extends T {}

                Patch.foo = [...T.foo, 'patched B'];
                Patch.bar = 'patched B';

                return Patch;
            });

            assert.deepEqual(PatchableB.foo, [ 'A', /* 'patched A', */ 'B', 'patched B' ]);
            assert.deepEqual(PatchableA.foo, [ 'A', 'patched A' ]);
            assert.strictEqual(PatchableB.bar, 'patched B');
        });

        QUnit.test('inheritance and lazy patch', function (assert) {
            assert.expect(6);

            const A = patchMixin(
                class {
                    constructor() {
                        assert.step('A.constructor');
                    }
                    f() {
                        assert.step('A.f');
                    }
                }
            );

            class B extends A {
                constructor() {
                    super();
                    assert.step('B.constructor');
                }
                f() {
                    super.f();
                    assert.step('B.f');
                }
            }

            const b = new B();

            A.patch('patch', T =>
                class extends T {
                    constructor() {
                        super();
                        // will not be called
                        assert.step('patch.constructor');
                    }
                    f() {
                        super.f();
                        assert.step('patch.f');
                    }
                }
            );

            b.f();

            assert.verifySteps([
                'A.constructor',
                'B.constructor',
                'A.f',
                'patch.f',
                'B.f',
            ]);
        });

        QUnit.test('patch not patchable class that inherits patchable class', function (assert) {
            assert.expect(1);

            const A = patchMixin(class {});
            class B extends A {}

            // class B is not patchable
            assert.throws(() => {
                B.patch('patch', T => class extends T {});
            });
        });
    });
});
});

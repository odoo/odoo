/** @odoo-module **/

import { patch } from "@web/core/utils/patch";

function makeBaseClass(assert, assertInSetup) {
    class BaseClass {
        constructor() {
            this.setup();
        }
        setup() {
            this._dynamic = "base";

            this.str = "base";
            this.obj = { base: "base" };
            this.arr = ["base"];

            if (assertInSetup !== false) {
                assert.step("base.setup");
            }
        }
        fn() {
            assert.step("base.fn");
        }
        async asyncFn() {
            // also check this binding
            assert.step(`base.${this.str}`);
        }
        get dynamic() {
            return this._dynamic;
        }
        set dynamic(value) {
            this._dynamic = value;
        }
    }

    BaseClass.staticStr = "base";
    BaseClass.staticObj = { base: "base" };
    BaseClass.staticArr = ["base"];
    BaseClass.staticFn = function () {
        assert.step("base.staticFn");
    };

    return BaseClass;
}

QUnit.module("utils", () => {
    QUnit.module("Patch", () => {
        QUnit.test("simple patch", async function (assert) {
            assert.expect(5);

            const BaseClass = makeBaseClass(assert);

            patch(BaseClass.prototype, {
                setup() {
                    super.setup();
                    assert.step("patch.setup");
                },
                fn() {
                    super.fn();
                    assert.step("patch.fn");
                },
            });

            new BaseClass().fn();

            assert.verifySteps(["base.setup", "patch.setup", "base.fn", "patch.fn"]);
        });

        QUnit.test("two patches on same base class", async function (assert) {
            assert.expect(7);

            const BaseClass = makeBaseClass(assert);

            patch(BaseClass.prototype, {
                setup() {
                    super.setup();
                    assert.step("patch1.setup");
                },
                fn() {
                    super.fn();
                    assert.step("patch1.fn");
                },
            });

            patch(BaseClass.prototype, {
                setup() {
                    super.setup();
                    assert.step("patch2.setup");
                },
                fn() {
                    super.fn();
                    assert.step("patch2.fn");
                },
            });

            new BaseClass().fn();
            assert.verifySteps([
                "base.setup",
                "patch1.setup",
                "patch2.setup",
                "base.fn",
                "patch1.fn",
                "patch2.fn",
            ]);
        });

        QUnit.test("unpatch", async function (assert) {
            assert.expect(8);

            const BaseClass = makeBaseClass(assert);

            const unpatch = patch(BaseClass.prototype, {
                setup() {
                    super.setup();
                    assert.step("patch.setup");
                },
                fn() {
                    super.fn();
                    assert.step("patch.fn");
                },
            });

            new BaseClass().fn();

            assert.verifySteps(["base.setup", "patch.setup", "base.fn", "patch.fn"]);
            unpatch();

            new BaseClass().fn();

            assert.verifySteps(["base.setup", "base.fn"]);
        });

        QUnit.test("unpatch two patches on the same base class", async function (assert) {
            assert.expect(15);

            const BaseClass = makeBaseClass(assert);

            const unpatch1 = patch(BaseClass.prototype, {
                setup() {
                    super.setup();
                    assert.step("patch1.setup");
                },
                fn() {
                    super.fn();
                    assert.step("patch1.fn");
                },
            });

            const unpatch2 = patch(BaseClass.prototype, {
                setup() {
                    super.setup();
                    assert.step("patch2.setup");
                },
                fn() {
                    super.fn();
                    assert.step("patch2.fn");
                },
            });

            new BaseClass().fn();

            assert.verifySteps([
                "base.setup",
                "patch1.setup",
                "patch2.setup",
                "base.fn",
                "patch1.fn",
                "patch2.fn",
            ]);

            unpatch1();

            new BaseClass().fn();

            assert.verifySteps(["base.setup", "patch2.setup", "base.fn", "patch2.fn"]);

            unpatch2();

            new BaseClass().fn();

            assert.verifySteps(["base.setup", "base.fn"]);
        });

        QUnit.test(
            "unpatch two patches on the same base class (returned by patch)",
            async function (assert) {
                assert.expect(15);

                const BaseClass = makeBaseClass(assert);

                const unpatch1 = patch(BaseClass.prototype, {
                    setup() {
                        super.setup();
                        assert.step("patch1.setup");
                    },
                    fn() {
                        super.fn();
                        assert.step("patch1.fn");
                    },
                });

                const unpatch2 = patch(BaseClass.prototype, {
                    setup() {
                        super.setup();
                        assert.step("patch2.setup");
                    },
                    fn() {
                        super.fn();
                        assert.step("patch2.fn");
                    },
                });

                new BaseClass().fn();

                assert.verifySteps([
                    "base.setup",
                    "patch1.setup",
                    "patch2.setup",
                    "base.fn",
                    "patch1.fn",
                    "patch2.fn",
                ]);

                unpatch1();

                new BaseClass().fn();

                assert.verifySteps(["base.setup", "patch2.setup", "base.fn", "patch2.fn"]);

                unpatch2();

                new BaseClass().fn();

                assert.verifySteps(["base.setup", "base.fn"]);
            }
        );

        QUnit.test("patch for specialization", async function (assert) {
            assert.expect(1);

            let args = [];

            const A = class {
                constructor() {
                    this.setup(...arguments);
                }
                setup() {
                    args = ["A", ...arguments];
                }
            };

            patch(A.prototype, {
                setup() {
                    super.setup("patch", ...arguments);
                },
            });

            new A("instantiation");

            assert.deepEqual(args, ["A", "patch", "instantiation"]);
        });

        QUnit.test("instance fields", async function (assert) {
            assert.expect(3);

            const BaseClass = makeBaseClass(assert, false);
            patch(BaseClass.prototype, {
                setup() {
                    super.setup(...arguments);

                    this.str += "patch";
                    this.arr.push("patch");
                    this.obj.patch = "patch";
                },
            });

            const instance = new BaseClass();
            assert.strictEqual(instance.str, "basepatch");
            assert.deepEqual(instance.arr, ["base", "patch"]);
            assert.deepEqual(instance.obj, { base: "base", patch: "patch" });
        });

        QUnit.test("call instance method defined in patch", async function (assert) {
            assert.expect(4);

            const BaseClass = makeBaseClass(assert, false);

            assert.notOk(new BaseClass().f);

            const unpatch = patch(BaseClass.prototype, {
                f() {
                    assert.step("patch.f");
                },
            });

            new BaseClass().f();
            assert.verifySteps(["patch.f"]);

            unpatch();

            assert.notOk(new BaseClass().f);
        });

        QUnit.test("class methods", async function (assert) {
            assert.expect(7);

            const BaseClass = makeBaseClass(assert);

            BaseClass.staticFn();
            assert.verifySteps(["base.staticFn"]);

            const unpatch = patch(BaseClass, {
                staticFn() {
                    super.staticFn();
                    assert.step("patch.staticFn");
                },
            });

            BaseClass.staticFn();
            assert.verifySteps(["base.staticFn", "patch.staticFn"]);

            unpatch();

            BaseClass.staticFn();
            assert.verifySteps(["base.staticFn"]);
        });

        QUnit.test("class fields", async function (assert) {
            assert.expect(6);

            const BaseClass = makeBaseClass(assert);

            const unpatch = patch(BaseClass, {
                staticStr: BaseClass.staticStr + "patch",
                staticArr: [...BaseClass.staticArr, "patch"],
                staticObj: { ...BaseClass.staticObj, patch: "patch" },
            });

            assert.strictEqual(BaseClass.staticStr, "basepatch");
            assert.deepEqual(BaseClass.staticArr, ["base", "patch"]);
            assert.deepEqual(BaseClass.staticObj, { base: "base", patch: "patch" });

            unpatch();

            assert.strictEqual(BaseClass.staticStr, "base");
            assert.deepEqual(BaseClass.staticArr, ["base"]);
            assert.deepEqual(BaseClass.staticObj, { base: "base" });
        });

        QUnit.test("lazy patch", async function (assert) {
            assert.expect(6);

            const BaseClass = makeBaseClass(assert);
            const instance = new BaseClass();

            const unpatch = patch(BaseClass.prototype, {
                setup() {
                    super.setup();
                    // will not be called
                    assert.step("patch.setup");
                },
                fn() {
                    super.fn();
                    assert.step("patch.fn");
                },
            });

            instance.fn();
            assert.verifySteps(["base.setup", "base.fn", "patch.fn"]);

            unpatch();

            instance.fn();
            assert.verifySteps(["base.fn"]);
        });

        QUnit.test("getter", async function (assert) {
            assert.expect(2);

            const BaseClass = makeBaseClass(assert, false);

            const unpatch = patch(BaseClass.prototype, {
                get dynamic() {
                    return super.dynamic + "patch";
                },
            });

            const instance = new BaseClass();
            assert.strictEqual(instance.dynamic, "basepatch");

            unpatch();
            assert.strictEqual(instance.dynamic, "base");
        });

        QUnit.test("setter", async function (assert) {
            assert.expect(3);

            const BaseClass = makeBaseClass(assert, false);

            const unpatch = patch(BaseClass.prototype, {
                set dynamic(value) {
                    super.dynamic = "patch:" + value;
                },
            });

            const instance = new BaseClass();

            assert.strictEqual(instance.dynamic, "base");
            instance.dynamic = "patch";
            assert.strictEqual(instance.dynamic, "patch:patch");

            unpatch();

            instance.dynamic = "base";
            assert.strictEqual(instance.dynamic, "base");
        });

        QUnit.test("patch getter/setter with value", async function (assert) {
            assert.expect(4);

            const BaseClass = makeBaseClass(assert, false);

            const originalDescriptor = Object.getOwnPropertyDescriptor(
                BaseClass.prototype,
                "dynamic"
            );
            const unpatch = patch(BaseClass.prototype, {
                dynamic: "patched",
            });

            const instance = new BaseClass();

            assert.deepEqual(Object.getOwnPropertyDescriptor(BaseClass.prototype, "dynamic"), {
                value: "patched",
                writable: true,
                configurable: true,
                enumerable: false, // class properties are not enumerable
            });
            assert.equal(instance.dynamic, "patched");

            unpatch();

            instance.dynamic = "base";
            assert.deepEqual(
                Object.getOwnPropertyDescriptor(BaseClass.prototype, "dynamic"),
                originalDescriptor
            );
            assert.strictEqual(instance.dynamic, "base");
        });

        QUnit.test("async function", async function (assert) {
            assert.expect(3);

            const BaseClass = makeBaseClass(assert, false);

            patch(BaseClass.prototype, {
                async asyncFn() {
                    await Promise.resolve();
                    await super.asyncFn(...arguments);
                    assert.step("patch.asyncFn");
                },
            });

            const instance = new BaseClass();
            instance.str = "asyncFn";
            await instance.asyncFn();

            assert.verifySteps(["base.asyncFn", "patch.asyncFn"]);
        });

        QUnit.test("async function (multiple patches)", async function (assert) {
            assert.expect(4);

            const BaseClass = makeBaseClass(assert, false);

            patch(BaseClass.prototype, {
                async asyncFn() {
                    await Promise.resolve();
                    await super.asyncFn(...arguments);
                    // also check this binding
                    assert.step(`patch1.${this.str}`);
                },
            });
            patch(BaseClass.prototype, {
                async asyncFn() {
                    await Promise.resolve();
                    await super.asyncFn(...arguments);
                    // also check this binding
                    assert.step(`patch2.${this.str}`);
                },
            });

            const instance = new BaseClass();
            instance.str = "asyncFn";
            await instance.asyncFn();

            assert.verifySteps(["base.asyncFn", "patch1.asyncFn", "patch2.asyncFn"]);
        });

        QUnit.test("call another super method", async function (assert) {
            const BaseClass = makeBaseClass(assert);
            patch(BaseClass.prototype, {
                setup() {
                    assert.step("patch.setup");
                    super.fn();
                },
                fn() {
                    assert.step("patch.fn"); // should not called
                },
            });

            new BaseClass();
            assert.verifySteps([
                "patch.setup",
                "base.fn",
            ]);
        });

        QUnit.module("inheritance");

        QUnit.test("inherit a patched class (extends before patch)", async function (assert) {
            assert.expect(12);

            const BaseClass = makeBaseClass(assert);

            class Extension extends BaseClass {
                setup() {
                    super.setup();
                    assert.step("extension.setup");
                }
                fn() {
                    super.fn();
                    assert.step("extension.fn");
                }
            }

            new Extension().fn();
            assert.verifySteps(["base.setup", "extension.setup", "base.fn", "extension.fn"]);

            patch(BaseClass.prototype, {
                setup() {
                    super.setup();
                    assert.step("patch.setup");
                },
                fn() {
                    super.fn();
                    assert.step("patch.fn");
                },
            });

            new Extension().fn();
            assert.verifySteps([
                "base.setup",
                "patch.setup",
                "extension.setup",
                "base.fn",
                "patch.fn",
                "extension.fn",
            ]);
        });

        QUnit.test("inherit a patched class (extends after patch)", async function (assert) {
            assert.expect(7);

            const BaseClass = makeBaseClass(assert);

            patch(BaseClass.prototype, {
                setup() {
                    super.setup();
                    assert.step("patch.setup");
                },
                fn() {
                    super.fn();
                    assert.step("patch.fn");
                },
            });

            class Extension extends BaseClass {
                setup() {
                    super.setup();
                    assert.step("extension.setup");
                }
                fn() {
                    super.fn();
                    assert.step("extension.fn");
                }
            }

            new Extension().fn();

            assert.verifySteps([
                "base.setup",
                "patch.setup",
                "extension.setup",
                "base.fn",
                "patch.fn",
                "extension.fn",
            ]);
        });

        QUnit.test("patch an inherited class", async function (assert) {
            assert.expect(12);

            const BaseClass = makeBaseClass(assert);

            class Extension extends BaseClass {
                setup() {
                    super.setup();
                    assert.step("extension.setup");
                }
                fn() {
                    super.fn();
                    assert.step("extension.fn");
                }
            }

            new Extension().fn();
            assert.verifySteps(["base.setup", "extension.setup", "base.fn", "extension.fn"]);

            patch(Extension.prototype, {
                setup() {
                    super.setup();
                    assert.step("patch.setup");
                },
                fn() {
                    super.fn();
                    assert.step("patch.fn");
                },
            });

            new Extension().fn();
            assert.verifySteps([
                "base.setup",
                "extension.setup",
                "patch.setup",
                "base.fn",
                "extension.fn",
                "patch.fn",
            ]);
        });

        QUnit.test("patch an inherited patched class", async function (assert) {
            assert.expect(9);

            const BaseClass = makeBaseClass(assert);

            patch(BaseClass.prototype, {
                setup() {
                    super.setup();
                    assert.step("patch.setup");
                },
                fn() {
                    super.fn();
                    assert.step("patch.fn");
                },
            });

            class Extension extends BaseClass {
                setup() {
                    super.setup();
                    assert.step("extension.setup");
                }
                fn() {
                    super.fn();
                    assert.step("extension.fn");
                }
            }

            patch(Extension.prototype, {
                setup() {
                    super.setup();
                    assert.step("patch.extension.setup");
                },
                fn() {
                    super.fn();
                    assert.step("patch.extension.fn");
                },
            });

            new Extension().fn();
            assert.verifySteps([
                "base.setup",
                "patch.setup",
                "extension.setup",
                "patch.extension.setup",
                "base.fn",
                "patch.fn",
                "extension.fn",
                "patch.extension.fn",
            ]);
        });

        QUnit.test("patch an inherited patched class 2", async function (assert) {
            assert.expect(7);

            const BaseClass = makeBaseClass(assert);

            class Extension extends BaseClass {
                // nothing in the prototype
            }

            // First patch Extension
            patch(Extension.prototype, {
                setup() {
                    super.setup();
                    assert.step("patch.extension.setup");
                },
                fn() {
                    super.fn();
                    assert.step("patch.extension.fn");
                },
            });

            // Then patch BaseClass
            patch(BaseClass.prototype, {
                setup() {
                    super.setup();
                    assert.step("patch.setup");
                },
                fn() {
                    super.fn();
                    assert.step("patch.fn");
                },
            });

            new Extension().fn();
            assert.verifySteps([
                "base.setup",
                "patch.setup",
                "patch.extension.setup",
                "base.fn",
                "patch.fn",
                "patch.extension.fn",
            ]);
        });

        QUnit.test("unpatch base class", async function (assert) {
            assert.expect(12);

            const BaseClass = makeBaseClass(assert);

            class Extension extends BaseClass {
                setup() {
                    super.setup();
                    assert.step("extension.setup");
                }
                fn() {
                    super.fn();
                    assert.step("extension.fn");
                }
            }

            const unpatch = patch(BaseClass.prototype, {
                setup() {
                    super.setup();
                    assert.step("patch.setup");
                },
                fn() {
                    super.fn();
                    assert.step("patch.fn");
                },
            });

            new Extension().fn();
            assert.verifySteps([
                "base.setup",
                "patch.setup",
                "extension.setup",
                "base.fn",
                "patch.fn",
                "extension.fn",
            ]);

            unpatch();

            new Extension().fn();
            assert.verifySteps(["base.setup", "extension.setup", "base.fn", "extension.fn"]);
        });

        QUnit.test("unpatch an inherited class", async function (assert) {
            assert.expect(12);

            const BaseClass = makeBaseClass(assert);

            class Extension extends BaseClass {
                setup() {
                    super.setup();
                    assert.step("extension.setup");
                }
                fn() {
                    super.fn();
                    assert.step("extension.fn");
                }
            }

            const unpatch = patch(Extension.prototype, {
                setup() {
                    super.setup();
                    assert.step("patch.setup");
                },
                fn() {
                    super.fn();
                    assert.step("patch.fn");
                },
            });

            new Extension().fn();
            assert.verifySteps([
                "base.setup",
                "extension.setup",
                "patch.setup",
                "base.fn",
                "extension.fn",
                "patch.fn",
            ]);

            unpatch();

            new Extension().fn();
            assert.verifySteps(["base.setup", "extension.setup", "base.fn", "extension.fn"]);
        });

        QUnit.test(
            "unpatch an inherited class and its base class (unpatch base first)",
            async function (assert) {
                assert.expect(21);

                const BaseClass = makeBaseClass(assert);

                const unpatchBase = patch(BaseClass.prototype, {
                    setup() {
                        super.setup();
                        assert.step("patch.setup");
                    },
                    fn() {
                        super.fn();
                        assert.step("patch.fn");
                    },
                });

                class Extension extends BaseClass {
                    setup() {
                        super.setup();
                        assert.step("extension.setup");
                    }
                    fn() {
                        super.fn();
                        assert.step("extension.fn");
                    }
                }

                const unpatchExtension = patch(Extension.prototype, {
                    setup() {
                        super.setup();
                        assert.step("patch.extension.setup");
                    },
                    fn() {
                        super.fn();
                        assert.step("patch.extension.fn");
                    },
                });

                new Extension().fn();
                assert.verifySteps([
                    "base.setup",
                    "patch.setup",
                    "extension.setup",
                    "patch.extension.setup",
                    "base.fn",
                    "patch.fn",
                    "extension.fn",
                    "patch.extension.fn",
                ]);

                unpatchBase();

                new Extension().fn();
                assert.verifySteps([
                    "base.setup",
                    "extension.setup",
                    "patch.extension.setup",
                    "base.fn",
                    "extension.fn",
                    "patch.extension.fn",
                ]);

                unpatchExtension();

                new Extension().fn();
                assert.verifySteps(["base.setup", "extension.setup", "base.fn", "extension.fn"]);
            }
        );

        QUnit.test(
            "unpatch an inherited class and its base class (unpatch extension first)",
            async function (assert) {
                assert.expect(21);

                const BaseClass = makeBaseClass(assert);

                const unpatchBase = patch(BaseClass.prototype, {
                    setup() {
                        super.setup();
                        assert.step("patch.setup");
                    },
                    fn() {
                        super.fn();
                        assert.step("patch.fn");
                    },
                });

                class Extension extends BaseClass {
                    setup() {
                        super.setup();
                        assert.step("extension.setup");
                    }
                    fn() {
                        super.fn();
                        assert.step("extension.fn");
                    }
                }

                const unpatchExtension = patch(Extension.prototype, {
                    setup() {
                        super.setup();
                        assert.step("patch.extension.setup");
                    },
                    fn() {
                        super.fn();
                        assert.step("patch.extension.fn");
                    },
                });

                new Extension().fn();
                assert.verifySteps([
                    "base.setup",
                    "patch.setup",
                    "extension.setup",
                    "patch.extension.setup",
                    "base.fn",
                    "patch.fn",
                    "extension.fn",
                    "patch.extension.fn",
                ]);

                unpatchExtension();

                new Extension().fn();
                assert.verifySteps([
                    "base.setup",
                    "patch.setup",
                    "extension.setup",
                    "base.fn",
                    "patch.fn",
                    "extension.fn",
                ]);

                unpatchBase();

                new Extension().fn();
                assert.verifySteps(["base.setup", "extension.setup", "base.fn", "extension.fn"]);
            }
        );

        QUnit.test("class methods", async function (assert) {
            assert.expect(12);

            const BaseClass = makeBaseClass(assert);

            class Extension extends BaseClass {
                static staticFn() {
                    super.staticFn();
                    assert.step("extension.staticFn");
                }
            }

            const unpatchBase = patch(BaseClass, {
                staticFn() {
                    super.staticFn();
                    assert.step("patch.staticFn");
                },
            });

            const unpatchExtension = patch(Extension, {
                staticFn() {
                    super.staticFn();
                    assert.step("patch.extension.staticFn");
                },
            });

            Extension.staticFn();
            assert.verifySteps([
                "base.staticFn",
                "patch.staticFn",
                "extension.staticFn",
                "patch.extension.staticFn",
            ]);

            unpatchBase();

            Extension.staticFn();
            assert.verifySteps(["base.staticFn", "extension.staticFn", "patch.extension.staticFn"]);

            unpatchExtension();

            Extension.staticFn();
            assert.verifySteps(["base.staticFn", "extension.staticFn"]);
        });

        QUnit.test("class fields (patch before inherit)", async function (assert) {
            assert.expect(6);

            const BaseClass = makeBaseClass(assert);

            const unpatch = patch(BaseClass, {
                staticStr: BaseClass.staticStr + "patch",
                staticArr: [...BaseClass.staticArr, "patch"],
                staticObj: { ...BaseClass.staticObj, patch: "patch" },
            });

            class Extension extends BaseClass {}
            Extension.staticStr = BaseClass.staticStr + "extension";
            Extension.staticArr = [...BaseClass.staticArr, "extension"];
            Extension.staticObj = { ...BaseClass.staticObj, extension: "extension" };

            assert.strictEqual(Extension.staticStr, "basepatchextension");
            assert.deepEqual(Extension.staticArr, ["base", "patch", "extension"]);
            assert.deepEqual(Extension.staticObj, {
                base: "base",
                patch: "patch",
                extension: "extension",
            });

            unpatch();

            // /!\ WARNING /!\
            // If inherit comes after the patch then extension will still have
            // the patched data when unpatching.
            assert.strictEqual(Extension.staticStr, "basepatchextension");
            assert.deepEqual(Extension.staticArr, ["base", "patch", "extension"]);
            assert.deepEqual(Extension.staticObj, {
                base: "base",
                patch: "patch",
                extension: "extension",
            });
        });

        QUnit.test("class fields (inherit before patch)", async function (assert) {
            assert.expect(6);

            const BaseClass = makeBaseClass(assert);

            class Extension extends BaseClass {}
            Extension.staticStr = BaseClass.staticStr + "extension";
            Extension.staticArr = [...BaseClass.staticArr, "extension"];
            Extension.staticObj = { ...BaseClass.staticObj, extension: "extension" };

            // /!\ WARNING /!\
            // If patch comes after the inherit then extension won't have
            // the patched data.
            const unpatch = patch(BaseClass, {
                staticStr: BaseClass.staticStr + "patch",
                staticArr: [...BaseClass.staticArr, "patch"],
                staticObj: { ...BaseClass.staticObj, patch: "patch" },
            });

            assert.strictEqual(Extension.staticStr, "baseextension");
            assert.deepEqual(Extension.staticArr, ["base", "extension"]);
            assert.deepEqual(Extension.staticObj, { base: "base", extension: "extension" });

            unpatch();

            assert.strictEqual(Extension.staticStr, "baseextension");
            assert.deepEqual(Extension.staticArr, ["base", "extension"]);
            assert.deepEqual(Extension.staticObj, { base: "base", extension: "extension" });
        });

        QUnit.test("lazy patch", async function (assert) {
            assert.expect(9);

            const BaseClass = makeBaseClass(assert);
            class Extension extends BaseClass {
                setup() {
                    super.setup();
                    assert.step("extension.setup");
                }
                fn() {
                    super.fn();
                    assert.step("extension.fn");
                }
            }

            const instance = new Extension();

            const unpatch = patch(BaseClass.prototype, {
                setup() {
                    super.setup();
                    // will not be called
                    assert.step("patch.setup");
                },
                fn() {
                    super.fn();
                    assert.step("patch.fn");
                },
            });

            instance.fn();
            assert.verifySteps([
                "base.setup",
                "extension.setup",
                "base.fn",
                "patch.fn",
                "extension.fn",
            ]);

            unpatch();

            instance.fn();
            assert.verifySteps(["base.fn", "extension.fn"]);
        });

        QUnit.test("keep original descriptor details", async function (assert) {
            class BaseClass {
                // getter declared in classes are not enumerable
                get getter() {
                    return false;
                }
            }
            let descriptor = Object.getOwnPropertyDescriptor(BaseClass.prototype, "getter");
            const getterFn = descriptor.get;
            assert.strictEqual(descriptor.configurable, true);
            assert.strictEqual(descriptor.enumerable, false);

            patch(BaseClass.prototype, {
                // getter declared in object are enumerable
                get getter() {
                    return true;
                },
            });
            descriptor = Object.getOwnPropertyDescriptor(BaseClass.prototype, "getter");
            assert.strictEqual(descriptor.configurable, true);
            assert.strictEqual(descriptor.enumerable, false);
            assert.notStrictEqual(getterFn, descriptor.get);
        });

        QUnit.module("other");

        QUnit.test("patch an object", async function (assert) {
            assert.expect(7);

            const obj = {
                var: "obj",
                fn() {
                    assert.step("obj");
                },
            };

            const unpatch = patch(obj, {
                var: obj.var + "patch",
                fn() {
                    super.fn(...arguments);
                    assert.step("patch");
                },
            });

            assert.strictEqual(obj.var, "objpatch");

            obj.fn();
            assert.verifySteps(["obj", "patch"]);

            unpatch();

            assert.strictEqual(obj.var, "obj");

            obj.fn();
            assert.verifySteps(["obj"]);
        });

        QUnit.test("can call a non bound patched method", async function (assert) {
            // use case: patching a function on window (e.g. setTimeout)
            assert.expect(3);

            const obj = {
                fn() {
                    assert.step("original");
                },
            };

            const originalFn = obj.fn;
            patch(obj, {
                fn() {
                    assert.step("patched");
                    originalFn();
                },
            });

            const fn = obj.fn; // purposely not bound
            fn();

            assert.verifySteps(["patched", "original"]);
        });
    });
});

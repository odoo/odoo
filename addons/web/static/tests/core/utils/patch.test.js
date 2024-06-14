import { describe, expect, test } from "@odoo/hoot";
import { patch } from "@web/core/utils/patch";

class BaseClass {
    static staticStr = "base";
    static staticObj = { base: "base" };
    static staticArr = ["base"];
    static staticFn() {
        expect.step("base.staticFn");
    }

    constructor() {
        this.setup();
    }
    setup() {
        this._dynamic = "base";

        this.str = "base";
        this.obj = { base: "base" };
        this.arr = ["base"];

        expect.step("base.setup");
    }
    fn() {
        expect.step("base.fn");
    }
    async asyncFn() {
        // also check this binding
        expect.step(`base.${this.str}`);
    }
    get dynamic() {
        return this._dynamic;
    }
    set dynamic(value) {
        this._dynamic = value;
    }
}

function applyGenericPatch(Klass, tag) {
    return patch(Klass.prototype, {
        setup() {
            super.setup();
            expect.step(`${tag}.setup`);
        },
        fn() {
            super.fn();
            expect.step(`${tag}.fn`);
        },
        async asyncFn() {
            await Promise.resolve();
            await super.asyncFn(...arguments);
            // also check this binding
            expect.step(`${tag}.${this.str}`);
        },
    });
}

function applyGenericStaticPatch(Klass, tag) {
    return patch(Klass, {
        staticStr: Klass.staticStr + tag,
        staticArr: [...Klass.staticArr, tag],
        staticObj: { ...Klass.staticObj, patch: tag },
        staticFn() {
            super.staticFn();
            expect.step(`${tag}.staticFn`);
        },
    });
}

function createGenericExtension() {
    return class Extension extends BaseClass {
        static staticStr = BaseClass.staticStr + "extension";
        static staticArr = [...BaseClass.staticArr, "extension"];
        static staticObj = { ...BaseClass.staticObj, extension: "extension" };
        static staticFn() {
            super.staticFn();
            expect.step("extension.staticFn");
        }
        setup() {
            super.setup();
            expect.step("extension.setup");
        }
        fn() {
            super.fn();
            expect.step("extension.fn");
        }
    };
}

describe.current.tags("headless");

test("one patch/unpatch", () => {
    new BaseClass().fn();
    expect(["base.setup", "base.fn"]).toVerifySteps();

    const unpatch = applyGenericPatch(BaseClass, "patch");
    new BaseClass().fn();
    expect(["base.setup", "patch.setup", "base.fn", "patch.fn"]).toVerifySteps();

    unpatch();
    new BaseClass().fn();
    expect(["base.setup", "base.fn"]).toVerifySteps();
});

test("two patch/unpatch (unpatch 1 > 2)", () => {
    new BaseClass().fn();
    expect(["base.setup", "base.fn"]).toVerifySteps();

    const unpatch1 = applyGenericPatch(BaseClass, "patch1");
    new BaseClass().fn();
    expect(["base.setup", "patch1.setup", "base.fn", "patch1.fn"]).toVerifySteps();

    const unpatch2 = applyGenericPatch(BaseClass, "patch2");
    new BaseClass().fn();
    expect([
        "base.setup",
        "patch1.setup",
        "patch2.setup",
        "base.fn",
        "patch1.fn",
        "patch2.fn",
    ]).toVerifySteps();

    unpatch1();
    new BaseClass().fn();
    expect(["base.setup", "patch2.setup", "base.fn", "patch2.fn"]).toVerifySteps();

    unpatch2();
    new BaseClass().fn();
    expect(["base.setup", "base.fn"]).toVerifySteps();
});

test("two patch/unpatch (unpatch 2 > 1)", () => {
    new BaseClass().fn();
    expect(["base.setup", "base.fn"]).toVerifySteps();

    const unpatch1 = applyGenericPatch(BaseClass, "patch1");
    new BaseClass().fn();
    expect(["base.setup", "patch1.setup", "base.fn", "patch1.fn"]).toVerifySteps();

    const unpatch2 = applyGenericPatch(BaseClass, "patch2");
    new BaseClass().fn();
    expect([
        "base.setup",
        "patch1.setup",
        "patch2.setup",
        "base.fn",
        "patch1.fn",
        "patch2.fn",
    ]).toVerifySteps();

    unpatch2();
    new BaseClass().fn();
    expect(["base.setup", "patch1.setup", "base.fn", "patch1.fn"]).toVerifySteps();

    unpatch1();
    new BaseClass().fn();
    expect(["base.setup", "base.fn"]).toVerifySteps();
});

test("patch for specialization", () => {
    let args = [];
    class A {
        constructor() {
            this.setup(...arguments);
        }
        setup() {
            args = ["A", ...arguments];
        }
    }

    const unpatch = patch(A.prototype, {
        setup() {
            super.setup("patch", ...arguments);
        },
    });

    new A("instantiation");
    expect(args).toEqual(["A", "patch", "instantiation"]);
    unpatch();
});

test("instance fields", () => {
    const unpatch = patch(BaseClass.prototype, {
        setup() {
            super.setup();
            this.str += "patch";
            this.arr.push("patch");
            this.obj.patch = "patch";
        },
    });

    const instance = new BaseClass();
    expect(["base.setup"]).toVerifySteps();
    expect(instance.str).toBe("basepatch");
    expect(instance.arr).toEqual(["base", "patch"]);
    expect(instance.obj).toEqual({ base: "base", patch: "patch" });

    unpatch();
    // unpatch does not change instance fields' values
    expect(instance.str).toBe("basepatch");
    expect(instance.arr).toEqual(["base", "patch"]);
    expect(instance.obj).toEqual({ base: "base", patch: "patch" });
});

test("call instance method defined in patch", () => {
    const instance = new BaseClass();
    expect(["base.setup"]).toVerifySteps();
    expect("f" in instance).toBe(false);

    const unpatch = patch(BaseClass.prototype, {
        f() {
            expect.step("patch.f");
        },
    });
    instance.f();
    expect("f" in instance).toBe(true);
    expect(["patch.f"]).toVerifySteps();

    unpatch();
    expect("f" in instance).toBe(false);
});

test("class methods", () => {
    BaseClass.staticFn();
    expect(["base.staticFn"]).toVerifySteps();

    const unpatch = applyGenericStaticPatch(BaseClass, "patch");
    BaseClass.staticFn();
    expect(["base.staticFn", "patch.staticFn"]).toVerifySteps();

    unpatch();
    BaseClass.staticFn();
    expect(["base.staticFn"]).toVerifySteps();
});

test("class fields", () => {
    expect(BaseClass.staticStr).toBe("base");
    expect(BaseClass.staticArr).toEqual(["base"]);
    expect(BaseClass.staticObj).toEqual({ base: "base" });

    const unpatch = applyGenericStaticPatch(BaseClass, "patch");
    expect(BaseClass.staticStr).toBe("basepatch");
    expect(BaseClass.staticArr).toEqual(["base", "patch"]);
    expect(BaseClass.staticObj).toEqual({ base: "base", patch: "patch" });

    unpatch();
    expect(BaseClass.staticStr).toBe("base");
    expect(BaseClass.staticArr).toEqual(["base"]);
    expect(BaseClass.staticObj).toEqual({ base: "base" });
});

test("lazy patch", () => {
    const instance = new BaseClass();
    const unpatch = applyGenericPatch(BaseClass, "patch");
    instance.fn();
    expect(["base.setup", "base.fn", "patch.fn"]).toVerifySteps();

    unpatch();
    instance.fn();
    expect(["base.fn"]).toVerifySteps();
});

test("getter", () => {
    const instance = new BaseClass();
    expect(["base.setup"]).toVerifySteps();
    expect(instance.dynamic).toBe("base");

    const unpatch = patch(BaseClass.prototype, {
        get dynamic() {
            return super.dynamic + "patch";
        },
    });
    expect(instance.dynamic).toBe("basepatch");

    unpatch();
    expect(instance.dynamic).toBe("base");
});

test("setter", () => {
    const instance = new BaseClass();
    expect(["base.setup"]).toVerifySteps();
    expect(instance.dynamic).toBe("base");
    instance.dynamic = "1";
    expect(instance.dynamic).toBe("1");

    const unpatch = patch(BaseClass.prototype, {
        set dynamic(value) {
            super.dynamic = "patch:" + value;
        },
    });
    expect(instance.dynamic).toBe("1"); // nothing changed

    instance.dynamic = "2";
    expect(instance.dynamic).toBe("patch:2");

    unpatch();
    instance.dynamic = "3";
    expect(instance.dynamic).toBe("3");
});

test("patch getter/setter with value", () => {
    const originalDescriptor = Object.getOwnPropertyDescriptor(BaseClass.prototype, "dynamic");

    const unpatch = patch(BaseClass.prototype, { dynamic: "patched" });
    const instance = new BaseClass();
    expect(["base.setup"]).toVerifySteps();
    expect(Object.getOwnPropertyDescriptor(BaseClass.prototype, "dynamic")).toEqual({
        value: "patched",
        writable: true,
        configurable: true,
        enumerable: false, // class properties are not enumerable
    });
    expect(instance.dynamic).toBe("patched");

    unpatch();
    instance.dynamic = "base";
    expect(Object.getOwnPropertyDescriptor(BaseClass.prototype, "dynamic")).toEqual(
        originalDescriptor
    );
    expect(instance.dynamic).toBe("base");
});

test("async function", async () => {
    const instance = new BaseClass();
    instance.str = "async1";
    await instance.asyncFn();
    expect(["base.setup", "base.async1"]).toVerifySteps();

    const unpatch = applyGenericPatch(BaseClass, "patch");
    instance.str = "async2";
    await instance.asyncFn();
    expect(["base.async2", "patch.async2"]).toVerifySteps();

    unpatch();
    instance.str = "async3";
    await instance.asyncFn();
    expect(["base.async3"]).toVerifySteps();
});

test("async function (multiple patches)", async () => {
    const instance = new BaseClass();
    instance.str = "async1";
    await instance.asyncFn();
    expect(["base.setup", "base.async1"]).toVerifySteps();

    const unpatch1 = applyGenericPatch(BaseClass, "patch1");
    const unpatch2 = applyGenericPatch(BaseClass, "patch2");
    instance.str = "async2";
    await instance.asyncFn();
    expect(["base.async2", "patch1.async2", "patch2.async2"]).toVerifySteps();

    unpatch1();
    unpatch2();
    instance.str = "async3";
    await instance.asyncFn();
    expect(["base.async3"]).toVerifySteps();
});

test("call another super method", () => {
    new BaseClass();
    expect(["base.setup"]).toVerifySteps();

    const unpatch = patch(BaseClass.prototype, {
        setup() {
            expect.step("patch.setup");
            super.fn();
        },
        fn() {
            expect.step("patch.fn"); // should not called
        },
    });

    new BaseClass();
    expect(["patch.setup", "base.fn"]).toVerifySteps();

    unpatch();
    new BaseClass();
    expect(["base.setup"]).toVerifySteps();
});

describe("inheritance", () => {
    test("extend > patch base > unpatch base", () => {
        const Extension = createGenericExtension();
        new Extension().fn();
        expect(["base.setup", "extension.setup", "base.fn", "extension.fn"]).toVerifySteps();

        const unpatch = applyGenericPatch(BaseClass, "patch");
        new Extension().fn();
        expect([
            "base.setup",
            "patch.setup",
            "extension.setup",
            "base.fn",
            "patch.fn",
            "extension.fn",
        ]).toVerifySteps();

        unpatch();
        new Extension().fn();
        expect(["base.setup", "extension.setup", "base.fn", "extension.fn"]).toVerifySteps();
    });

    test("patch base > extend > unpatch base", () => {
        const unpatch = applyGenericPatch(BaseClass, "patch");
        const Extension = createGenericExtension();
        new Extension().fn();
        expect([
            "base.setup",
            "patch.setup",
            "extension.setup",
            "base.fn",
            "patch.fn",
            "extension.fn",
        ]).toVerifySteps();

        unpatch();
        new Extension().fn();
        expect(["base.setup", "extension.setup", "base.fn", "extension.fn"]).toVerifySteps();
    });

    test("extend > patch extension > unpatch extension", () => {
        const Extension = createGenericExtension();
        new Extension().fn();
        expect(["base.setup", "extension.setup", "base.fn", "extension.fn"]).toVerifySteps();

        const unpatch = applyGenericPatch(Extension, "patch.extension");
        new Extension().fn();
        expect([
            "base.setup",
            "extension.setup",
            "patch.extension.setup",
            "base.fn",
            "extension.fn",
            "patch.extension.fn",
        ]).toVerifySteps();

        unpatch();
        new Extension().fn();
        expect(["base.setup", "extension.setup", "base.fn", "extension.fn"]).toVerifySteps();
    });

    test("extend > patch base > patch extension > unpatch base > unpatch extension", () => {
        const Extension = createGenericExtension();
        new Extension().fn();
        expect(["base.setup", "extension.setup", "base.fn", "extension.fn"]).toVerifySteps();

        const unpatchBase = applyGenericPatch(BaseClass, "patch");
        new Extension().fn();
        expect([
            "base.setup",
            "patch.setup",
            "extension.setup",
            "base.fn",
            "patch.fn",
            "extension.fn",
        ]).toVerifySteps();

        const unpatchExtension = applyGenericPatch(Extension, "patch.extension");
        new Extension().fn();
        expect([
            "base.setup",
            "patch.setup",
            "extension.setup",
            "patch.extension.setup",
            "base.fn",
            "patch.fn",
            "extension.fn",
            "patch.extension.fn",
        ]).toVerifySteps();

        unpatchBase();
        new Extension().fn();
        expect([
            "base.setup",
            "extension.setup",
            "patch.extension.setup",
            "base.fn",
            "extension.fn",
            "patch.extension.fn",
        ]).toVerifySteps();

        unpatchExtension();
        new Extension().fn();
        expect(["base.setup", "extension.setup", "base.fn", "extension.fn"]).toVerifySteps();
    });

    test("extend > patch base > patch extension > unpatch extension > unpatch base", () => {
        const Extension = createGenericExtension();
        new Extension().fn();
        expect(["base.setup", "extension.setup", "base.fn", "extension.fn"]).toVerifySteps();

        const unpatchBase = applyGenericPatch(BaseClass, "patch");
        new Extension().fn();
        expect([
            "base.setup",
            "patch.setup",
            "extension.setup",
            "base.fn",
            "patch.fn",
            "extension.fn",
        ]).toVerifySteps();

        const unpatchExtension = applyGenericPatch(Extension, "patch.extension");
        new Extension().fn();
        expect([
            "base.setup",
            "patch.setup",
            "extension.setup",
            "patch.extension.setup",
            "base.fn",
            "patch.fn",
            "extension.fn",
            "patch.extension.fn",
        ]).toVerifySteps();

        unpatchExtension();
        new Extension().fn();
        expect([
            "base.setup",
            "patch.setup",
            "extension.setup",
            "base.fn",
            "patch.fn",
            "extension.fn",
        ]).toVerifySteps();

        unpatchBase();
        new Extension().fn();
        expect(["base.setup", "extension.setup", "base.fn", "extension.fn"]).toVerifySteps();
    });

    test("extend > patch extension > patch base > unpatch base > unpatch extension", () => {
        const Extension = createGenericExtension();
        new Extension().fn();
        expect(["base.setup", "extension.setup", "base.fn", "extension.fn"]).toVerifySteps();

        const unpatchExtension = applyGenericPatch(Extension, "patch.extension");
        new Extension().fn();
        expect([
            "base.setup",
            "extension.setup",
            "patch.extension.setup",
            "base.fn",
            "extension.fn",
            "patch.extension.fn",
        ]).toVerifySteps();

        const unpatchBase = applyGenericPatch(BaseClass, "patch");
        new Extension().fn();
        expect([
            "base.setup",
            "patch.setup",
            "extension.setup",
            "patch.extension.setup",
            "base.fn",
            "patch.fn",
            "extension.fn",
            "patch.extension.fn",
        ]).toVerifySteps();

        unpatchBase();
        new Extension().fn();
        expect([
            "base.setup",
            "extension.setup",
            "patch.extension.setup",
            "base.fn",
            "extension.fn",
            "patch.extension.fn",
        ]).toVerifySteps();

        unpatchExtension();
        new Extension().fn();
        expect(["base.setup", "extension.setup", "base.fn", "extension.fn"]).toVerifySteps();
    });

    test("extend > patch extension > patch base > unpatch extension > unpatch base", () => {
        const Extension = createGenericExtension();
        new Extension().fn();
        expect(["base.setup", "extension.setup", "base.fn", "extension.fn"]).toVerifySteps();

        const unpatchExtension = applyGenericPatch(Extension, "patch.extension");
        new Extension().fn();
        expect([
            "base.setup",
            "extension.setup",
            "patch.extension.setup",
            "base.fn",
            "extension.fn",
            "patch.extension.fn",
        ]).toVerifySteps();

        const unpatchBase = applyGenericPatch(BaseClass, "patch");
        new Extension().fn();
        expect([
            "base.setup",
            "patch.setup",
            "extension.setup",
            "patch.extension.setup",
            "base.fn",
            "patch.fn",
            "extension.fn",
            "patch.extension.fn",
        ]).toVerifySteps();

        unpatchExtension();
        new Extension().fn();
        expect([
            "base.setup",
            "patch.setup",
            "extension.setup",
            "base.fn",
            "patch.fn",
            "extension.fn",
        ]).toVerifySteps();

        unpatchBase();
        new Extension().fn();
        expect(["base.setup", "extension.setup", "base.fn", "extension.fn"]).toVerifySteps();
    });

    test("patch base > extend > patch extension > unpatch base > unpatch extension", () => {
        const unpatchBase = applyGenericPatch(BaseClass, "patch");
        const Extension = createGenericExtension();
        new Extension().fn();
        expect([
            "base.setup",
            "patch.setup",
            "extension.setup",
            "base.fn",
            "patch.fn",
            "extension.fn",
        ]).toVerifySteps();

        const unpatchExtension = applyGenericPatch(Extension, "patch.extension");
        new Extension().fn();
        expect([
            "base.setup",
            "patch.setup",
            "extension.setup",
            "patch.extension.setup",
            "base.fn",
            "patch.fn",
            "extension.fn",
            "patch.extension.fn",
        ]).toVerifySteps();

        unpatchBase();
        new Extension().fn();
        expect([
            "base.setup",
            "extension.setup",
            "patch.extension.setup",
            "base.fn",
            "extension.fn",
            "patch.extension.fn",
        ]).toVerifySteps();

        unpatchExtension();
        new Extension().fn();
        expect(["base.setup", "extension.setup", "base.fn", "extension.fn"]).toVerifySteps();
    });

    test("patch base > extend > patch extension > unpatch extension > unpatch base", () => {
        const unpatchBase = applyGenericPatch(BaseClass, "patch");
        const Extension = createGenericExtension();
        new Extension().fn();
        expect([
            "base.setup",
            "patch.setup",
            "extension.setup",
            "base.fn",
            "patch.fn",
            "extension.fn",
        ]).toVerifySteps();

        const unpatchExtension = applyGenericPatch(Extension, "patch.extension");
        new Extension().fn();
        expect([
            "base.setup",
            "patch.setup",
            "extension.setup",
            "patch.extension.setup",
            "base.fn",
            "patch.fn",
            "extension.fn",
            "patch.extension.fn",
        ]).toVerifySteps();

        unpatchExtension();
        new Extension().fn();
        expect([
            "base.setup",
            "patch.setup",
            "extension.setup",
            "base.fn",
            "patch.fn",
            "extension.fn",
        ]).toVerifySteps();

        unpatchBase();
        new Extension().fn();
        expect(["base.setup", "extension.setup", "base.fn", "extension.fn"]).toVerifySteps();
    });

    test("class methods", () => {
        const Extension = createGenericExtension();
        Extension.staticFn();
        expect(["base.staticFn", "extension.staticFn"]).toVerifySteps();

        const unpatchBase = applyGenericStaticPatch(BaseClass, "patch");
        Extension.staticFn();
        expect(["base.staticFn", "patch.staticFn", "extension.staticFn"]).toVerifySteps();

        const unpatchExtension = applyGenericStaticPatch(Extension, "patch.extension");
        Extension.staticFn();
        expect([
            "base.staticFn",
            "patch.staticFn",
            "extension.staticFn",
            "patch.extension.staticFn",
        ]).toVerifySteps();

        unpatchBase();
        Extension.staticFn();
        expect(["base.staticFn", "extension.staticFn", "patch.extension.staticFn"]).toVerifySteps();

        unpatchExtension();
        Extension.staticFn();
        expect(["base.staticFn", "extension.staticFn"]).toVerifySteps();
    });

    test("class fields (patch before inherit)", () => {
        const unpatch = applyGenericStaticPatch(BaseClass, "patch");
        const Extension = createGenericExtension();
        expect(Extension.staticStr).toBe("basepatchextension");
        expect(Extension.staticArr).toEqual(["base", "patch", "extension"]);
        expect(Extension.staticObj).toEqual({
            base: "base",
            patch: "patch",
            extension: "extension",
        });

        // /!\ WARNING /!\
        // If inherit comes after the patch then extension will still have
        // the patched data when unpatching.
        unpatch();
        expect(Extension.staticStr).toBe("basepatchextension");
        expect(Extension.staticArr).toEqual(["base", "patch", "extension"]);
        expect(Extension.staticObj).toEqual({
            base: "base",
            patch: "patch",
            extension: "extension",
        });
    });

    test("class fields (inherit before patch)", () => {
        const Extension = createGenericExtension();
        expect(Extension.staticStr).toBe("baseextension");
        expect(Extension.staticArr).toEqual(["base", "extension"]);
        expect(Extension.staticObj).toEqual({ base: "base", extension: "extension" });

        // /!\ WARNING /!\
        // If patch comes after the inherit then extension won't have
        // the patched data.
        const unpatch = applyGenericStaticPatch(BaseClass, "patch");
        expect(Extension.staticStr).toBe("baseextension");
        expect(Extension.staticArr).toEqual(["base", "extension"]);
        expect(Extension.staticObj).toEqual({ base: "base", extension: "extension" });

        unpatch();
        expect(Extension.staticStr).toBe("baseextension");
        expect(Extension.staticArr).toEqual(["base", "extension"]);
        expect(Extension.staticObj).toEqual({ base: "base", extension: "extension" });
    });

    test("lazy patch", () => {
        const Extension = createGenericExtension();
        const instance = new Extension();
        const unpatch = applyGenericPatch(BaseClass, "patch");

        instance.fn();
        expect([
            "base.setup",
            "extension.setup",
            "base.fn",
            "patch.fn",
            "extension.fn",
        ]).toVerifySteps();

        unpatch();
        instance.fn();
        expect(["base.fn", "extension.fn"]).toVerifySteps();
    });

    test("keep original descriptor details", () => {
        class Klass {
            // getter declared in classes are not enumerable
            get getter() {
                return false;
            }
        }
        let descriptor = Object.getOwnPropertyDescriptor(Klass.prototype, "getter");
        const getterFn = descriptor.get;
        expect(descriptor.configurable).toBe(true);
        expect(descriptor.enumerable).toBe(false);

        patch(Klass.prototype, {
            // getter declared in object are enumerable
            get getter() {
                return true;
            },
        });
        descriptor = Object.getOwnPropertyDescriptor(Klass.prototype, "getter");
        expect(descriptor.configurable).toBe(true);
        expect(descriptor.enumerable).toBe(false);
        expect(getterFn).not.toBe(descriptor.get);
    });
});

describe("other", () => {
    test("patch an object", () => {
        const obj = {
            var: "obj",
            fn() {
                expect.step("obj");
            },
        };

        const unpatch = patch(obj, {
            var: obj.var + "patch",
            fn() {
                super.fn();
                expect.step("patch");
            },
        });
        expect(obj.var).toBe("objpatch");

        obj.fn();
        expect(["obj", "patch"]).toVerifySteps();

        unpatch();
        expect(obj.var).toBe("obj");

        obj.fn();
        expect(["obj"]).toVerifySteps();
    });

    test("can call a non bound patched method", () => {
        // use case: patching a function on window (e.g. setTimeout)

        const obj = {
            fn() {
                expect.step("original");
            },
        };

        const originalFn = obj.fn;
        patch(obj, {
            fn() {
                expect.step("patched");
                originalFn();
            },
        });

        const fn = obj.fn; // purposely not bound
        fn();
        expect(["patched", "original"]).toVerifySteps();
    });
});

import { expect, getFixture, test } from "@odoo/hoot";
import { microTick, tick } from "@odoo/hoot-dom";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";

/** @type {typeof OdooModuleLoader} */
const ModuleLoader = Object.getPrototypeOf(odoo.loader.constructor);

test.tags("headless");
test("define: simple case", async () => {
    const loader = new ModuleLoader();

    const modA = {};
    const modC = {};

    expect(loader.factories).toBeEmpty();
    expect(loader.modules).toBeEmpty();
    expect(loader.checkErrorProm).toBe(null);

    loader.define("b", ["c"], (req) => req("c"));
    loader.define("c", [], () => modC);
    loader.define("a", ["b"], () => modA);

    expect(loader.factories).toHaveLength(3);
    expect(loader.modules).toHaveLength(3);
    expect(loader.failed).toBeEmpty();
    expect(loader.jobs).toBeEmpty();

    expect(loader.modules.get("a")).toBe(modA);
    expect(loader.modules.get("b")).toBe(modC);
    expect(loader.modules.get("c")).toBe(modC);

    Promise.resolve(loader.checkErrorProm).then(() => expect.step("check done"));

    expect.verifySteps([]);

    await tick();

    expect.verifySteps(["check done"]);
});

test.tags("headless");
test("define: invalid module error handling", async () => {
    const loader = new ModuleLoader(getFixture());

    expect(() => loader.define(null, null, null)).toThrow(/Module name should be a string/);
    expect(() => loader.define("a", null, null)).toThrow(
        /Module dependencies should be a list of strings/
    );
    expect(() => loader.define("a", [], null)).toThrow(/Module factory should be a function/);

    expect(loader.checkErrorProm).toBe(null);
});

test.tags("headless");
test("define: duplicate name", async () => {
    const loader = new ModuleLoader(getFixture());

    loader.define("a", [], () => ":)");
    loader.define("a", [], () => {
        throw new Error("This factory should be ignored");
    });

    await microTick();

    expect(loader.modules.get("a")).toBe(":)");
});

test("define: missing module", async () => {
    patchWithCleanup(browser.console, {
        error: (msg, args) => {
            expect.step(msg + args);
        },
    });

    const loader = new ModuleLoader(getFixture());

    loader.define("b", ["a"], () => {});
    loader.define("c", ["a"], () => {});

    await microTick();

    expect.verifySteps([
        "The following modules are needed by other modules but have not been defined, they may not be present in the correct asset bundle:a",
        "The following modules could not be loaded because they have unmet dependencies, this is a secondary error which is likely caused by one of the above problems:b,c",
    ]);
});

test("define: dependency cycle", async () => {
    patchWithCleanup(browser.console, {
        error: (msg, args) => {
            expect.step(msg + args);
        },
    });

    const loader = new ModuleLoader(getFixture());

    loader.define("a", ["b"], () => {});
    loader.define("b", ["c"], () => {});
    loader.define("c", ["a"], () => {});

    await microTick();

    expect.verifySteps([
        `The following modules could not be loaded because they form a dependency cycle:"a" => "b" => "c" => "a"`,
        "The following modules could not be loaded because they have unmet dependencies, this is a secondary error which is likely caused by one of the above problems:a,b,c",
    ]);
});

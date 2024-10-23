import { expect, getFixture, test } from "@odoo/hoot";
import { microTick } from "@odoo/hoot-dom";

/** @type {typeof OdooModuleLoader} */
const ModuleLoader = Object.getPrototypeOf(odoo.loader.constructor);

test.tags("headless")("define: simple case", async () => {
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

    await microTick();

    expect.verifySteps(["check done"]);
});

test.tags("headless")("define: invalid module error handling", async () => {
    const loader = new ModuleLoader(getFixture());

    expect(() => loader.define(null, null, null)).toThrow(/Module name should be a string/);
    expect(() => loader.define("a", null, null)).toThrow(
        /Module dependencies should be a list of strings/
    );
    expect(() => loader.define("a", [], null)).toThrow(/Module factory should be a function/);

    expect(loader.checkErrorProm).toBe(null);
});

test.tags("headless")("define: duplicate name", async () => {
    const loader = new ModuleLoader(getFixture());

    loader.define("a", [], () => ":)");
    loader.define("a", [], () => {
        throw new Error("This factory should be ignored");
    });

    await microTick();

    expect(loader.modules.get("a")).toBe(":)");
});

test("define: missing module", async () => {
    const loader = new ModuleLoader(getFixture());

    loader.define("b", ["a"], () => {});
    loader.define("c", ["a"], () => {});

    await microTick();

    expect(".o_module_error").toHaveCount(1);
    expect(".o_module_error ul:first").toHaveText("a");
    expect(".o_module_error ul:last").toHaveText("b\nc");
});

test("define: dependency cycle", async () => {
    const loader = new ModuleLoader(getFixture());

    loader.define("a", ["b"], () => {});
    loader.define("b", ["c"], () => {});
    loader.define("c", ["a"], () => {});

    await microTick();

    expect(".o_module_error").toHaveCount(1);
    expect(".o_module_error ul:first").toHaveText(`"a" => "b" => "c" => "a"`);
});

import { describe, expect, test } from "@odoo/hoot";

/**
 * @param {string} folder folder that can only import from `allowedFolders`
 * @param {string[]} allowedFolders folders from which `folder` can import
 * @returns {{[key: string]: string[]}} an object where the keys are modules and
 *  the values are an array of imports that the module is not allowed to import
 */
function invalidImportsFrom(folder, allowedFolders) {
    // modules within a folder can always depend on one another
    allowedFolders.push(folder);
    const modulesToCheck = Array.from(odoo.loader.modules.keys()).filter((module) =>
        module.startsWith(`@web/${folder}/`)
    );
    const invalidDeps = {};
    for (const module of modulesToCheck) {
        const invalid = odoo.loader.factories.get(module).deps.filter((dep) => {
            // owl and @web/session are allowed everywhere
            if (dep === "@odoo/owl" || dep === "@web/session") {
                return false;
            }
            return !allowedFolders.some((allowed) => dep.startsWith(`@web/${allowed}/`));
        });
        if (invalid.length) {
            invalidDeps[module] = invalid;
        }
    }
    return invalidDeps;
}

describe.current.tags("headless");

test("modules only import from allowed folders", () => {
    expect(invalidImportsFrom("core", [])).toEqual({});
    expect(invalidImportsFrom("search", ["core"])).toEqual({});
    expect(invalidImportsFrom("model", ["core", "search"])).toEqual({});
    expect(invalidImportsFrom("views", ["core", "search", "model"])).toEqual({});
});

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
    // FIXME: this dependency should not exist. Temporarily whitelist it so we don't add more, and remove ASAP
    expect(invalidImportsFrom("core", [])).toEqual({ "@web/core/utils/hooks": ["@web/env"] });
    expect(invalidImportsFrom("search", ["core"])).toEqual({
        // FIXME: this dependency should not exist. Temporarily whitelist it so we don't add more, and remove ASAP
        "@web/search/control_panel/control_panel": ["@web/webclient/breadcrumbs/breadcrumbs"],
        "@web/search/search_panel/search_panel": ["@web/webclient/actions/action_hook"],
        "@web/search/with_search/with_search": ["@web/webclient/actions/action_hook"],
    });
    expect(invalidImportsFrom("model", ["core", "search"])).toEqual({
        // FIXME: this dependency should not exist. Temporarily whitelist it so we don't add more, and remove ASAP
        "@web/model/model": ["@web/views/view_hook"],
    });
    expect(invalidImportsFrom("views", ["core", "search", "model"])).toEqual({
        // FIXME: these dependencies should not exist. Temporarily whitelist them so we don't add more, and remove ASAP
        "@web/views/fields/many2one/many2one_field": ["@web/webclient/barcode/barcode_scanner"],
        "@web/views/view_hook": ["@web/webclient/actions/action_hook"],
    });
});

/** @odoo-module **/

import { loadBundle } from "@web/core/assets";

export async function loadLegacyWysiwygAssets(additionnalAssets = []) {
    const xmlids = ["web_editor.assets_legacy_wysiwyg", ...additionnalAssets];
    await loadBundle({ assetLibs: xmlids });
}

export async function requireLegacyModule(moduleName, loadCallback = () => {}) {
    if (!(await odoo.ready(moduleName))) {
        await loadCallback();
        await odoo.ready(moduleName);
    }
    const mod = odoo.__DEBUG__.services[moduleName]
    return mod[Symbol.for('default')] || mod;
}

export async function requireWysiwygLegacyModule(moduleName) {
    return requireLegacyModule(moduleName, loadLegacyWysiwygAssets);
}

/** @odoo-module **/

import { loadBundle } from "@web/core/assets";

export async function loadLegacyWysiwygAssets(additionnalAssets = []) {
    const xmlids = ["web_editor.assets_legacy_wysiwyg", ...additionnalAssets];
    await loadBundle({ assetLibs: xmlids });
}

export async function requireLegacyModule(moduleName, loadCallback = () => {}) {
    await loadCallback();
    return odoo.loader.modules.get(moduleName)[Symbol.for('default')] || odoo.loader.modules.get(moduleName);
}

export async function requireWysiwygLegacyModule(moduleName) {
    return requireLegacyModule(moduleName, loadLegacyWysiwygAssets);
}

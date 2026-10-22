import { loadBundle } from "@web/core/assets";

/**
 * Lazy loads a frontend bundle that requires the editor.
 *
 * @param {string} bundle
 */
export async function loadEditorBundle(bundle) {
    await loadBundle("html_editor.assets_editor_frontend");
    await loadBundle(bundle);
}

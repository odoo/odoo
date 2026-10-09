import { loadBundle } from "@web/core/assets";

/**
 * Lazy loads, in the frontend, a bundle that requires the editor. The editor
 * is loaded separately so that it is loaded only once when several such
 * bundles are used on the same page.
 *
 * @param {string} bundle
 */
export async function loadEditorBundle(bundle) {
    await loadBundle("html_editor.assets_editor_frontend");
    await loadBundle(bundle);
}

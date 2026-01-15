import { Plugin } from "@html_editor/plugin";

export class CoreSetupEditorPlugin extends Plugin {
    // TODO: remove in master
    static id = "core_setup_editor_plugin";
    /** @type {import("plugins").BuilderResources} */
    resources = {
        o_editable_selectors: "[data-oe-model]",
    };
}

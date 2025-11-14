import { Plugin } from "@html_editor/plugin";

export class TranslateSetupEditorPlugin extends Plugin {
    // TODO: remove in master
    static id = "translate_setup_editor_plugin";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        o_editable_selectors: "[data-oe-model]",
    };
}

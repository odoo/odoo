import { Plugin } from "@html_editor/plugin";

export class CoreSetupEditorPlugin extends Plugin {
    static id = "core_setup_editor_plugin";
    resources = {
        o_editable_selectors: "[data-oe-model]",
    };
}

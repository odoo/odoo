import { Plugin } from "@html_editor/plugin";

export class TranslateSetupEditorPlugin extends Plugin {
    // TODO: remove in master
    static id = "translate_setup_editor_plugin";
    resources = {
        o_editable_selectors: "[data-oe-model]",
    };
}

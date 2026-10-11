import { Plugin } from "@html_editor/plugin";

export class DisableImplicitFormatShortcutsPlugin extends Plugin {
    static id = "disable-implicit-format-shortcuts";
    /** @type {import("plugins").EditorResources} */
    resources = {
        on_beforeinput_handlers: (ev) => {
            if (["formatBold", "formatItalic", "formatUnderline"].includes(ev.inputType)) {
                ev.preventDefault();
                ev.stopPropagation();
            }
        },
    };
}

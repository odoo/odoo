import { Plugin } from "@html_editor/plugin";

export class DisableImplicitFormatShortcutsPlugin extends Plugin {
    static id = "disable-implicit-format-shortcuts";
    /** @type {import("plugins").EditorResources} */
    resources = {
        on_beforeinput_handlers: (ev) => {
            if (!(ev instanceof InputEvent)) {
                return;
            }
            if (
                ev.inputType === "formatBold" ||
                ev.inputType === "formatItalic" ||
                ev.inputType === "formatUnderline"
            ) {
                ev.preventDefault();
                ev.stopPropagation();
                return;
            }
        },
    };
}

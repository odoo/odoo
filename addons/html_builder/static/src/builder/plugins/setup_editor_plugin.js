import { Plugin } from "@html_editor/plugin";

export class SetupEditorPlugin extends Plugin {
    static id = "setup_editor_plugin";

    resources = {
        clean_for_save_handlers: ({ root }) => {
            root.querySelectorAll(".o_editable").forEach((el) => {
                el.classList.remove("o_editable");
            });
        },
    };

    setup() {
        // Add the `o_editable` class on the editable elements
        const editableEls = Array.from(this.editable.querySelectorAll("[data-oe-model]"))
            .filter((el) => !el.classList.contains("o_not_editable"))
            .filter((el) => {
                const parent = el.closest(".o_editable, .o_not_editable");
                return !parent || parent.classList.contains("o_editable");
            })
            .filter((el) => !el.matches("link, script"))
            .filter((el) => !el.hasAttribute("data-oe-readonly"))
            .filter(
                (el) =>
                    !el.matches(
                        'img[data-oe-field="arch"], br[data-oe-field="arch"], input[data-oe-field="arch"]'
                    )
            )
            .filter((el) => !el.classList.contains("oe_snippet_editor"))
            .filter((el) => !el.matches("hr, br, input, textarea"))
            .filter((el) => !el.hasAttribute("data-oe-sanitize-prevent-edition"));
        editableEls.concat(Array.from(this.editable.querySelectorAll(".o_editable")));
        editableEls.forEach((el) => el.classList.add("o_editable"));
    }
}

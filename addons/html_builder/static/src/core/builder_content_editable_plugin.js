import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class BuilderContentEditablePlugin extends Plugin {
    static id = "builderContentEditablePlugin";
    resources = {
        force_not_editable_selector: [
            "section:has(> .o_container_small, > .container, > .container-fluid)",
            ".o_not_editable",
            "[data-oe-field='arch']:empty",
        ],
        force_editable_selector: [
            "section > .o_container_small",
            "section > .container",
            "section > .container-fluid",
            ".o_editable",
        ],
        filter_contenteditable_handlers: this.filterContentEditable.bind(this),
        contenteditable_to_remove_selector: "[contenteditable]",
    };

    setup() {
        this.editable.setAttribute("contenteditable", false);
    }

    filterContentEditable(contentEditableEls) {
        return contentEditableEls.filter(
            (el) =>
                !el.matches("input, [data-oe-readonly]") &&
                el.closest(".o_editable") &&
                !el.closest(".o_not_editable")
        );
    }
}
registry
    .category("website-plugins")
    .add(BuilderContentEditablePlugin.id, BuilderContentEditablePlugin);

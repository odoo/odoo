import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BuilderAction } from "@html_builder/core/builder_action";

class DisclaimerOptionPlugin extends Plugin {
    static id = "DisclaimerOption";
    resources = {
        builder_options: [
            {
                template: "website.DisclaimerOption",
                selector: ".s_disclaimer",
            },
        ],
        builder_actions: {
            ShowOnPageAction,
        },
        dropzone_selector: [
            {
                selector: ".s_disclaimer",
                dropIn: "#o_snippet_above_header",
            },
        ],
    };
}

export class ShowOnPageAction extends BuilderAction {
    static id = "showOnPage";

    isApplied({ editingElement: el, value }) {
        const snippetPosition = el.closest("#o_snippet_above_header") ? "allPages" : "currentPage";
        return value === snippetPosition;
    }
    apply({ editingElement: el, value }) {
        const snippetEl = el.closest(".s_disclaimer");
        // Decide target container:
        // "allPages": move snippet to dedicated `#o_snippet_above_header`.
        // "currentPage": move snippet to first editable content area.
        const targetContainerEl =
            value === "allPages"
                ? this.editable.querySelector("#o_snippet_above_header")
                : this.editable.querySelector("main .oe_structure.o_editable");
        targetContainerEl?.prepend(snippetEl);
    }
}

registry.category("website-plugins").add(DisclaimerOptionPlugin.id, DisclaimerOptionPlugin);

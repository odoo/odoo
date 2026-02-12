import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent } from "@html_builder/core/utils";

class HeadlineOption extends BaseOptionComponent {
    static template = "website.HeadlineOption";
    static selector = ".s_headline";
}
class HeadlineOptionPlugin extends Plugin {
    static id = "headlineOption";
    resources = {
        builder_options: [HeadlineOption],
        builder_actions: {
            ShowOnPageAction,
        },
        dropzone_selector: [
            {
                selector: ".s_headline",
                dropNear: ".s_headline",
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
        const snippetEl = el.closest(".s_headline");
        // Decide target container:
        // "allPages": move snippet to dedicated `#o_snippet_above_header`.
        // "currentPage": move snippet to first editable content area.
        const targetContainerEl =
            value === "allPages"
                ? this.editable.querySelector("#o_snippet_above_header")
                : this.editable.querySelector("main .oe_structure.o_savable");
        targetContainerEl?.prepend(snippetEl);
    }
}

registry.category("website-plugins").add(HeadlineOptionPlugin.id, HeadlineOptionPlugin);

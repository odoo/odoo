import { Plugin } from "@html_editor/plugin";
import { selectElements } from "@html_editor/utils/dom_traversal";
import { registry } from "@web/core/registry";

export class BuilderContentEditablePlugin extends Plugin {
    static id = "builderContentEditablePlugin";
    resources = {
        content_not_editable_selectors: [
            "section:has(> .o_container_small, > .container, > .container-fluid)",
            ".o_not_editable",
            "[data-oe-field='arch']:empty",
        ],
        content_editable_selectors: [
            "section > .o_container_small",
            "section > .container",
            "section > .container-fluid",
            ".o_editable",
        ],
        valid_contenteditable_predicates: this.isValidContentEditable.bind(this),
        content_editable_providers: this.getContentEditableEls.bind(this),
        content_not_editable_providers: this.getContentNotEditableEls.bind(this),
        contenteditable_to_remove_selector: "[contenteditable]",
    };

    setup() {
        this.editable.setAttribute("contenteditable", false);
    }

    getContentEditableEls(rootEl) {
        const editableSelector = this.getResource("content_editable_selectors").join(",");
        return [...selectElements(rootEl, editableSelector)];
    }

    getContentNotEditableEls(rootEl) {
        const notEditableSelector = this.getResource("content_not_editable_selectors").join(",");
        return [...selectElements(rootEl, notEditableSelector)];
    }

    isValidContentEditable(contentEditableEl) {
        // Check if an element is inside a ".o_not_editable" element that is not
        // inside a snippet.
        const isDescendantOfNotEditableNotSnippet = (el) => {
            let notEditableEl = el.closest(".o_not_editable");
            if (!notEditableEl) {
                return false;
            }
            while (notEditableEl.parentElement.closest(".o_not_editable")) {
                notEditableEl = notEditableEl.parentElement.closest(".o_not_editable");
            }
            return !notEditableEl.closest("[data-snippet]");
        };
        return (
            !contentEditableEl.matches("input, [data-oe-readonly]") &&
            contentEditableEl.closest(".o_editable") &&
            !isDescendantOfNotEditableNotSnippet(contentEditableEl)
        );
    }
}
registry
    .category("builder-plugins")
    .add(BuilderContentEditablePlugin.id, BuilderContentEditablePlugin);

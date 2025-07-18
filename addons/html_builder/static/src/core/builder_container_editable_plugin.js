import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { closestElement } from "@html_editor/utils/dom_traversal";

export class BuilderContainerEditablePlugin extends Plugin {
    static id = "builderContainerEditable";
    static dependencies = ["history"];

    resources = {
        change_current_options_containers_listeners: this.restrictEditableArea.bind(this),
        system_classes: ["o_restricted_editable_area"],
        is_element_editable_predicates: this.isElementEditableRestricted.bind(this),
        clean_for_save_handlers: this.cleanForSave.bind(this),
    };

    setup() {
        this.restrictedElements = new Map();
    }

    destroy() {
        super.destroy();
        this.restoreRestrictedElements();
    }

    cleanForSave({ root }) {
        [root, ...root.querySelectorAll(".o_restricted_editable_area")].forEach((el) => {
            el.classList.remove("o_restricted_editable_area");
        });
    }

    isElementEditableRestricted(element) {
        const closestElementRestricted = closestElement(element, ".o_restricted_editable_area");
        if (
            element &&
            (element.isContentEditable ||
                (closestElementRestricted &&
                    this.restrictedElements.get(closestElementRestricted)?.contenteditable !==
                        false))
        ) {
            // if the element is contenteditable or was previously restricted, we consider it as editable
            return true;
        }
        return false;
    }

    restoreRestrictedElements() {
        // restore the previous state of previously restricted elements
        this.dependencies.history.ignoreDOMMutations(() => {
            this.restrictedElements.forEach((value, key) => {
                if (value.contenteditable === null) {
                    key.removeAttribute("contenteditable");
                } else {
                    key.setAttribute("contenteditable", value.contenteditable);
                }
                key.classList.remove("o_restricted_editable_area");
            });
        });

        this.restrictedElements.clear();
    }

    restrictEditableArea(optionsContainer) {
        this.restoreRestrictedElements();

        // if there is only one or 0 option container, we do not restrict the selection
        // as it is the only one option container in the editable area or a blank editable area
        if (optionsContainer.length <= 1) {
            return;
        }

        const mostInnerContainerParentEl = optionsContainer.at(-1).element?.parentElement;
        const mostInnerContainerEl = optionsContainer.at(-1).element;

        if (!mostInnerContainerParentEl) {
            return;
        }
        // if the most inner container is not contenteditable, we do not restrict it
        // as it is not editable by the user
        if (mostInnerContainerEl && !mostInnerContainerEl.isContentEditable) {
            return;
        }

        // store the current state
        this.restrictedElements.set(mostInnerContainerParentEl, {
            contenteditable: mostInnerContainerParentEl.getAttribute("contenteditable"),
        });
        this.restrictedElements.set(mostInnerContainerEl, {
            contenteditable: mostInnerContainerEl.getAttribute("contenteditable"),
        });

        // Restrict the editable area to the most inner container
        // set contenteditable to false on the parent element to block the selection
        // inside the inner container element
        this.dependencies.history.ignoreDOMMutations(() => {
            mostInnerContainerParentEl.setAttribute("contenteditable", "false");
            mostInnerContainerEl.setAttribute("contenteditable", "true");

            // set temporary class to both manipulated elements
            mostInnerContainerParentEl.classList.add("o_restricted_editable_area");
            mostInnerContainerEl.classList.add("o_restricted_editable_area");
        });
    }
}

registry
    .category("website-plugins")
    .add(BuilderContainerEditablePlugin.id, BuilderContainerEditablePlugin);

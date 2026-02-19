import { before, SNIPPET_SPECIFIC_END } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { AnimatedNumberOption } from "./animated_number_option";
import { BuilderAction } from "@html_builder/core/builder_action";
import { firstLeaf } from "@html_editor/utils/dom_traversal";
import { ClassAction } from "@html_builder/core/core_builder_action_plugin";

class AnimatedNumberOptionPlugin extends Plugin {
    static id = "AnimatedNumberOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: [withSequence(before(SNIPPET_SPECIFIC_END), AnimatedNumberOption)],
        so_content_addition_selector: [".s_animated_number"],
        builder_actions: {
            ToggleTitleAnimatedNumberAction,
            ToggleAnimatedNumberTextAction,
        },
        clean_for_save_handlers: this.cleanForSave.bind(this),
    };

    cleanForSave({ root }) {
        for (const el of root.querySelectorAll(".s_animated_numer")) {
            const numberEl = el.querySelector(".s_animated_number_value");
            numberEl.textContent = el.dataset.startValue || 0;
        }
    }
}

export class ToggleTitleAnimatedNumberAction extends ClassAction {
    static id = "toggleTitleAnimatedNumber";

    isApplied({ editingElement, value }) {
        if (!value) {
            return !editingElement.querySelector(".s_animated_number_label");
        } else {
            return true;
        }
    }
    apply({ editingElement, value }) {
        if (!value) {
            editingElement.querySelector(".s_animated_number_label")?.remove();
        }
        if (value && !editingElement.querySelector(".s_animated_number_label")) {
            const titleEl = document.createElement("div");
            titleEl.classList.add(
                "s_animated_number_label",
                "d-flex",
                "justify-content-center",
                "align-items-center"
            );
            const h2El = document.createElement("h2");
            h2El.textContent = "Clients";
            titleEl.append(h2El);
            editingElement.prepend(titleEl);
        }
    }
}

export class ToggleAnimatedNumberTextAction extends BuilderAction {
    static id = "toggleAnimatedNumberText";

    isApplied({ editingElement, params: { mainParam: position } }) {
        if (position == "prefix") {
            return !!editingElement.querySelector(".s_animated_number_prefix");
        } else {
            return !!editingElement.querySelector(".s_animated_number_postfix");
        }
    }
    apply({ editingElement, params: { mainParam: position } }) {
        const isPrefix = position == "prefix";
        const numberEl = editingElement.querySelector(".s_animated_number_value");
        const textEl = numberEl.cloneNode(true);
        firstLeaf(textEl, (el) => el.childNodes.length != 1).textContent = isPrefix ? "+" : "%";
        textEl.classList.remove("s_animated_number_value");
        textEl.classList.add(isPrefix ? "s_animated_number_prefix" : "s_animated_number_postfix");
        const displayEl = editingElement.querySelector(".s_animated_number_display");
        displayEl.insertAdjacentElement(isPrefix ? "afterbegin" : "beforeend", textEl);
    }
    clean({ editingElement, params: { mainParam: position } }) {
        if (position == "prefix") {
            return editingElement.querySelector(".s_animated_number_prefix")?.remove();
        } else {
            return editingElement.querySelector(".s_animated_number_postfix")?.remove();
        }
    }
}

registry.category("website-plugins").add(AnimatedNumberOptionPlugin.id, AnimatedNumberOptionPlugin);

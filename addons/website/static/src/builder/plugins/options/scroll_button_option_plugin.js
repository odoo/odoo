import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { ScrollButtonOption } from "./scroll_button_option";
import { BuilderAction } from "@html_builder/core/builder_action";
import { ClassAction } from "@html_builder/core/core_builder_action_plugin";
import { withSequence } from "@html_editor/utils/resource";
import { SCROLL_BUTTON } from "@website/builder/option_sequence";

class ScrollButtonOptionPlugin extends Plugin {
    static id = "scrollButtonOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: [withSequence(SCROLL_BUTTON, ScrollButtonOption)],
        builder_actions: {
            AddScrollButtonAction,
            ScrollButtonSectionHeightClassAction,
        },
    };
}

class ScrollButtonManager {
    constructor() {
        this.buttonCache = new Map();
    }

    createButton() {
        const anchor = document.createElement("a");
        anchor.classList.add(
            "o_scroll_button",
            "mb-3",
            "rounded-circle",
            "align-items-center",
            "justify-content-center",
            "mx-auto",
            "bg-primary",
            "o_not_editable"
        );
        anchor.href = "#";
        anchor.contentEditable = "false";
        anchor.title = _t("Scroll down to next section");

        const arrow = document.createElement("i");
        arrow.classList.add("fa", "fa-angle-down", "fa-3x");
        anchor.appendChild(arrow);

        return anchor;
    }

    ensureButton(editingElement) {
        let button = this.buttonCache.get(editingElement);
        if (!button) {
            button = this.createButton();
            this.buttonCache.set(editingElement, button);
        }
        return button;
    }

    attachButton(editingElement) {
        const button = this.ensureButton(editingElement);
        editingElement.appendChild(button);
    }

    removeButton(editingElement) {
        const button = editingElement.querySelector(":scope > .o_scroll_button");
        if (button) {
            button.remove();
            this.buttonCache.set(editingElement, button); // Cache for reuse
        }
    }

    isButtonPresent(editingElement) {
        return !!editingElement.querySelector(":scope > .o_scroll_button");
    }
}

const scrollButtonManager = new ScrollButtonManager();

export class AddScrollButtonAction extends BuilderAction {
    static id = "addScrollButton";
    setup() {
        this.manager = scrollButtonManager;
    }

    isApplied({ editingElement }) {
        return this.manager.isButtonPresent(editingElement);
    }

    apply({ editingElement }) {
        this.manager.attachButton(editingElement);
    }

    clean({ editingElement }) {
        this.manager.removeButton(editingElement);
    }
}

export class ScrollButtonSectionHeightClassAction extends ClassAction {
    static id = "scrollButtonSectionHeightClass";
    setup() {
        this.manager = scrollButtonManager;
    }

    apply({ editingElement, params: { mainParam } }) {
        super.apply(...arguments);
        if (mainParam) {
            editingElement.classList.replace("d-lg-block", "d-lg-flex");
        } else if (editingElement.classList.contains("d-lg-flex")) {
            editingElement.classList.remove("d-lg-flex");
            const style = window.getComputedStyle(editingElement);
            const display = style.getPropertyValue("display");
            editingElement.classList.add(display === "flex" ? "d-lg-flex" : "d-lg-block");
        }
    }

    clean(args) {
        super.clean(args);
        if (args.params.mainParam === "o_full_screen_height") {
            this.manager.removeButton(args.editingElement);
        }
    }
}

registry.category("website-plugins").add(ScrollButtonOptionPlugin.id, ScrollButtonOptionPlugin);

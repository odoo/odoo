import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { isElementInViewport } from "@html_builder/utils/utils";
import { isRemovable } from "../remove/remove_plugin";

export class ClonePlugin extends Plugin {
    static id = "clone";
    static dependencies = ["history", "builder-options"];
    static shared = ["cloneElement"];

    resources = {
        builder_actions: this.getActions(),
        get_overlay_buttons: withSequence(2, this.getActiveOverlayButtons.bind(this)),
    };

    // TODO find why the images should not have the clone buttons.
    setup() {
        this.overlayTarget = null;
    }

    getActions() {
        return {
            // TODO maybe rename to cloneItem ?
            addItem: {
                apply: ({ editingElement, param: itemSelector, value: position }) => {
                    const itemEl = editingElement.querySelector(itemSelector);
                    this.cloneElement(itemEl, { position, scrollToClone: true });
                },
            },
        };
    }

    getActiveOverlayButtons(target) {
        if (!isRemovable(target)) {
            this.overlayTarget = null;
            return [];
        }
        const buttons = [];
        this.overlayTarget = target;
        buttons.push({
            class: "o_snippet_clone fa fa-clone",
            title: _t("Duplicate"),
            handler: () => this.cloneElement(this.overlayTarget, { scrollToClone: true }),
        });
        return buttons;
    }

    cloneElement(el, { position = "afterend", scrollToClone = false } = {}) {
        // TODO snippet_will_be_cloned ?
        // TODO cleanUI resource for each option
        const cloneEl = el.cloneNode(true);
        el.insertAdjacentElement(position, cloneEl);
        this.dependencies["builder-options"].updateContainers(cloneEl);
        this.dispatchTo("on_clone_handlers", { cloneEl: cloneEl, originalEl: el });
        if (scrollToClone && !isElementInViewport(cloneEl)) {
            cloneEl.scrollIntoView({ behavior: "smooth", block: "center" });
        }
        // TODO snippet_cloned ?
        this.dependencies.history.addStep();
    }
}

import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { isElementInViewport } from "@html_builder/utils/utils";
import { isRemovable } from "./remove_plugin";
import { isMovable } from "./move_plugin";

const clonableSelector = "a.btn:not(.oe_unremovable)";

export function isClonable(el) {
    return el.matches(clonableSelector) || (isRemovable(el) && isMovable(el));
}

export class ClonePlugin extends Plugin {
    static id = "clone";
    static dependencies = ["history", "builder-options"];
    static shared = ["cloneElement"];

    resources = {
        builder_actions: this.getActions(),
        get_overlay_buttons: withSequence(2, {
            getButtons: this.getActiveOverlayButtons.bind(this),
        }),
        // Resource definitions:
        on_will_clone_handlers: [
            // ({ originalEl: el }) => {
            //     called on the original element before clone
            // }
        ],
        on_cloned_handlers: [
            // ({ cloneEl: cloneEl, originalEl: el }) => {
            //     called after an element was cloned and inserted in the DOM
            // }
        ],
    };

    setup() {
        this.overlayTarget = null;
        this.ignoredClasses = new Set(this.getResource("system_classes"));
        this.ignoredAttrs = new Set(this.getResource("system_attributes"));
    }

    getActions() {
        return {
            // TODO maybe rename to cloneItem ?
            addItem: {
                apply: ({
                    editingElement,
                    params: { mainParam: itemSelector },
                    value: position,
                }) => {
                    const itemEl = editingElement.querySelector(itemSelector);
                    this.cloneElement(itemEl, { position, scrollToClone: true });
                    this.dependencies.history.addStep();
                },
            },
        };
    }

    getActiveOverlayButtons(target) {
        if (!isClonable(target)) {
            this.overlayTarget = null;
            return [];
        }
        const buttons = [];
        this.overlayTarget = target;
        const disabledReason = this.dependencies["builder-options"].getCloneDisabledReason(target);
        buttons.push({
            class: "o_snippet_clone fa fa-clone",
            title: _t("Duplicate"),
            disabledReason,
            handler: () => {
                this.cloneElement(this.overlayTarget, { scrollToClone: true });
                this.dependencies.history.addStep();
            },
        });
        return buttons;
    }

    cloneElement(el, { position = "afterend", scrollToClone = false } = {}) {
        this.dispatchTo("on_will_clone_handlers", { originalEl: el });
        // TODO cleanUI resource for each option
        const cloneEl = el.cloneNode(true);
        this.cleanElement(cloneEl);
        el.insertAdjacentElement(position, cloneEl);
        this.dependencies["builder-options"].updateContainers(cloneEl);
        this.dispatchTo("on_cloned_handlers", { cloneEl: cloneEl, originalEl: el });
        if (scrollToClone && !isElementInViewport(cloneEl)) {
            cloneEl.scrollIntoView({ behavior: "smooth", block: "center" });
        }
        // TODO snippet_cloned ?
        return cloneEl;
    }

    cleanElement(toCleanEl) {
        this.ignoredClasses.forEach((ignoredClass) => {
            [toCleanEl, ...toCleanEl.querySelectorAll(`.${ignoredClass}`)].forEach((el) =>
                el.classList.remove(ignoredClass)
            );
        });
        this.ignoredAttrs.forEach((ignoredAttr) => {
            [toCleanEl, ...toCleanEl.querySelectorAll(`[${ignoredAttr}]`)].forEach((el) =>
                el.removeAttribute(ignoredAttr)
            );
        });
    }
}

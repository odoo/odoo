import { Plugin } from "@html_editor/plugin";
import { isElementInViewport } from "@html_builder/utils/utils";
import { withSequence } from "@html_editor/utils/resource";
import { InvisibleElementsPanel } from "@html_builder/sidebar/invisible_elements_panel";
import { EventBus } from "@odoo/owl";

export class VisibilityPlugin extends Plugin {
    static id = "visibility";
    static dependencies = ["builderOptions", "disableSnippets", "history"];
    static shared = ["invalidateVisibility", "getVisibleSibling"];

    invalidateBus = new EventBus();

    resources = {
        lower_panel_entries: withSequence(20, {
            Component: InvisibleElementsPanel,
            props: {
                getEntries: this.getInvisibleEntries.bind(this),
                invalidateEntriesBus: this.invalidateBus,
            },
        }),
        /** @param {{step: import("@html_editor/core/history_plugin").HistoryStep, isPreviewing: boolean}} args */
        step_added_handlers: ({ step: { type, extraStepInfos }, isPreviewing }) => {
            if (isPreviewing) {
                return;
            }
            if (type === "undo") {
                this.show(extraStepInfos.currentTarget);
            }
            if (type === "redo") {
                this.show(extraStepInfos.nextTarget ?? extraStepInfos.currentTarget);
            }
            if (this.checkTargetVisibility() === false) {
                this.dependencies.builderOptions.deactivateContainers();
                this.dependencies.disableSnippets.disableUndroppableSnippets();
            }
            this.refreshInvisibleElementsPanel();
        },
        on_snippet_dropped_handlers: ({ snippetEl }) => {
            if (this.checkTargetVisibility(snippetEl) === false) {
                this.show(snippetEl);
            }
        },
        reveal_target_handlers: (targetEl) => {
            this.show(targetEl);
            this.refreshInvisibleElementsPanel();
            const { activeItems, selectorAll } = this.activeItemsAndSelectorAll();
            let scrollDestination = targetEl;
            if (targetEl.matches(selectorAll)) {
                const { target } = activeItems.find(({ selector }) => targetEl.matches(selector));
                if (target) {
                    scrollDestination = targetEl.querySelector(target);
                }
            }
            if (!isElementInViewport(scrollDestination)) {
                scrollDestination.scrollIntoView({ behavior: "smooth", block: "center" });
            }
        },

        // The data-invisible attribute is not needed/used anymore.
        // It was used to try to track if an element is invisible.
        // It persisted through saves, so we remove it from existing pages.
        clean_for_save_handlers: ({ root }) =>
            [...root.querySelectorAll("[data-invisible]")].forEach((el) =>
                el.removeAttribute("data-invisible")
            ),

        invisible_items: [
            /*
            {
                selector: "the element listed in invisible panel",
                target: "inside the element matching `selector` on which we `checkVisibility`",
                isDisabled: () => bool,
                toggle: (el, show) => { make the `el` visible of not depending on `show` }, // called inside a `ignoreDOMMutations`
            }
            */
        ],
    };

    /**
     * @param {HTMLElement} target
     * @param {"prev"|"next"} direction
     * @returns {HTMLElement?}
     */
    getVisibleSibling(target, direction) {
        const siblingEls = [...target.parentNode.children];
        const visibleSiblingEls = siblingEls.filter((el) => this.checkTargetVisibility(el));
        const targetMobileOrder = target.style.order;
        // On mobile, if the target has a mobile order (which is independent
        // from desktop), consider these orders instead of the DOM order.
        if (targetMobileOrder && this.config.isMobileView(target)) {
            visibleSiblingEls.sort((a, b) => parseInt(a.style.order) - parseInt(b.style.order));
        }
        const targetIndex = visibleSiblingEls.indexOf(target);
        const siblingIndex = direction === "prev" ? targetIndex - 1 : targetIndex + 1;
        if (siblingIndex === -1 || siblingIndex === visibleSiblingEls.length) {
            return false;
        }
        return visibleSiblingEls[siblingIndex];
    }

    activeItemsAndSelectorAll() {
        const activeItems = this.getResource("invisible_items")
            .filter(({ isDisabled }) => !isDisabled?.())
            .map((item) => ({
                ...item,
                selector: item.target ? `${item.selector}:has(${item.target})` : item.selector,
            }));
        return {
            activeItems,
            selectorAll: activeItems.map(({ selector }) => selector).join(", ") || ":not(*)",
        };
    }

    show(el) {
        if (!el) {
            return;
        }
        const { activeItems, selectorAll } = this.activeItemsAndSelectorAll();
        const ancestors = [];
        {
            let climbingEl = el;
            while ((climbingEl = climbingEl?.closest(selectorAll))) {
                ancestors.push(climbingEl);
                climbingEl = climbingEl.parentElement;
            }
        }
        ancestors.reverse();
        this.dependencies.history.ignoreDOMMutations(() => {
            for (const ancestor of ancestors) {
                activeItems
                    .filter(({ selector }) => ancestor.matches(selector))
                    .filter(
                        ({ target }) =>
                            !(target ? ancestor.querySelector(target) : ancestor).checkVisibility()
                    )
                    .forEach(({ toggle }) => toggle(ancestor, true));
            }
        });
    }

    hide(el) {
        const { activeItems, selectorAll } = this.activeItemsAndSelectorAll();
        if (!el.matches(selectorAll)) {
            return;
        }
        this.dependencies.history.ignoreDOMMutations(() =>
            activeItems
                .filter(({ selector }) => el.matches(selector))
                .forEach(({ toggle }) => toggle(el, false))
        );
    }

    checkTargetVisibility(targetEl = this.dependencies.builderOptions.getTarget()) {
        const visible = targetEl?.checkVisibility();
        if (visible) {
            // If the options' target is visible, maybe it matches an item whose target is invisible
            const { activeItems, selectorAll } = this.activeItemsAndSelectorAll();
            if (targetEl.matches(selectorAll)) {
                for (const { selector, target } of activeItems) {
                    if (
                        target &&
                        targetEl.matches(selector) &&
                        !targetEl.querySelector(target).checkVisibility()
                    ) {
                        return false;
                    }
                }
            }
        }
        return visible;
    }

    /**
     * Recompute content of the "invisible elements" panel
     */
    invalidateVisibility() {
        this.refreshInvisibleElementsPanel();
        if (this.checkTargetVisibility() === false) {
            this.dependencies.builderOptions.deactivateContainers();
            this.dependencies.disableSnippets.disableUndroppableSnippets();
        }
    }

    refreshInvisibleElementsPanel() {
        this.invalidateBus.trigger("INVALIDATE_INVISIBLE_ENTRIES");
    }

    getInvisibleEntries() {
        const { activeItems, selectorAll } = this.activeItemsAndSelectorAll();
        const entries = new Map(
            [...this.editable.querySelectorAll(selectorAll)].map((el) => {
                const matchingItems = activeItems.filter(({ selector }) => el.matches(selector));
                const visible = matchingItems.every(({ target }) =>
                    (target ? el.querySelector(target) : el).checkVisibility()
                );
                const entry = {
                    el,
                    toggle: () => {
                        if (visible) {
                            this.hide(el);
                            this.refreshInvisibleElementsPanel();
                            this.dependencies.builderOptions.deactivateContainers();
                        } else {
                            this.dispatchTo("reveal_target_handlers", el);
                        }
                        this.dependencies.disableSnippets.disableUndroppableSnippets();
                    },
                    visible,
                    children: [],
                };
                return [el, entry];
            })
        );
        const roots = [];
        for (const [el, entry] of entries.entries()) {
            const parent = entries.get(el.parentElement?.closest(selectorAll));
            (parent ? parent.children : roots).push(entry);
        }
        return roots;
    }
}

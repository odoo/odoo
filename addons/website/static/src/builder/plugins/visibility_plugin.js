import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { InvisibleElementsPanel } from "./invisible_elements_panel";
import { reactive } from "@odoo/owl";
import { registry } from "@web/core/registry";

/**
 * @typedef { Object } VisibilityShared
 * @property { VisibilityPlugin['invalidateVisibility'] } invalidateVisibility
 */

/**
 * @typedef {import("plugins").CSSSelector} CSSSelector
 *
 * @typedef {Object} InvisibleItem
 * @property {CSSSelector} selector the element listed in invisible panel
 * @property {CSSSelector} target an element inside a match of `selector`, on
 * which we `checkVisibility`,
 * @property {() => boolean} isAvailable defaults to true
 * @property {(el: HTMLElement, show: boolean) => void} toggle make the `el`
 * visible or hidden depending on `show`,
 *
 * @typedef {InvisibleItem[]} invisible_items
 */

export class VisibilityPlugin extends Plugin {
    static id = "visibility";
    static dependencies = ["builderOptions", "disableSnippets", "history"];
    static shared = ["invalidateVisibility"];

    invisibleElementsPanelState = reactive({ invisibleEntries: [] });

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        lower_panel_entries: withSequence(20, {
            Component: InvisibleElementsPanel,
            props: { state: this.invisibleElementsPanelState },
        }),
        /** @param {{step: import("@html_editor/core/history_plugin").HistoryStep, isPreviewing: boolean}} args */
        step_added_handlers: ({ step: { type, extraStepInfos }, isPreviewing }) => {
            if (isPreviewing) {
                return;
            }
            const optionsTarget = this.dependencies.builderOptions.getTarget();
            if (
                optionsTarget &&
                this.getResource("hidden_element_predicates").some((p) => p(optionsTarget))
            ) {
                if (type === "original") {
                    extraStepInfos.nextTarget = false;
                }
                this.dependencies.builderOptions.deactivateContainers();
                this.dependencies.disableSnippets.disableUndroppableSnippets();
            }
            this.refreshInvisibleElementsPanel();
        },
        on_snippet_dropped_handlers: ({ snippetEl }) => this.showNewElement(snippetEl),
        on_cloned_handlers: ({ cloneEl }) => this.showNewElement(cloneEl, true),
        reveal_target_handlers: withSequence(5, (targetEl) => {
            this.showInvisibleElement(targetEl);
            this.refreshInvisibleElementsPanel();
        }),

        // The data-invisible attribute is not needed/used anymore.
        // It was used to try to track if an element is hidden.
        // It persisted through saves, so we remove it from existing pages.
        clean_for_save_handlers: ({ root }) => {
            for (const el of root.querySelectorAll("[data-invisible]")) {
                el.removeAttribute("data-invisible");
            }
        },
        hidden_element_predicates: (el) => {
            if (!el.checkVisibility()) {
                return true;
            }
            // el is visible, maybe it matches an item with hidden target
            const { activeItems, selectorAll } = this.activeItemsAndSelectorAll();
            if (el.matches(selectorAll)) {
                for (const { selectorWithTarget, target } of activeItems) {
                    if (
                        target &&
                        el.matches(selectorWithTarget) &&
                        !el.querySelector(target).checkVisibility()
                    ) {
                        return true;
                    }
                }
            }
            return false;
        },
        is_element_in_invisible_panel_predicates: (el) =>
            el.matches(this.activeItemsAndSelectorAll().selectorAll),
    };

    activeItemsAndSelectorAll() {
        const activeItems = this.getResource("invisible_items")
            .filter(({ isAvailable }) => !isAvailable || isAvailable())
            .map((item) => ({
                ...item,
                selectorWithTarget: item.target
                    ? `${item.selector}:has(${item.target})`
                    : item.selector,
            }));
        return {
            activeItems,
            selectorAll:
                activeItems.map(({ selectorWithTarget }) => selectorWithTarget).join(", ") ||
                ":not(*)",
        };
    }

    // Show an element by calling the corresponding `toggle` from the
    // `invisible_items` on it and/or on its ancestors
    showInvisibleElement(el) {
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
        for (const ancestor of ancestors) {
            for (const { selectorWithTarget, target, toggle } of activeItems) {
                if (
                    ancestor.matches(selectorWithTarget) &&
                    !(target ? ancestor.querySelector(target) : ancestor).checkVisibility()
                ) {
                    toggle(ancestor, true);
                }
            }
        }
    }

    hide(el) {
        const { activeItems, selectorAll } = this.activeItemsAndSelectorAll();
        if (!el.matches(selectorAll)) {
            return;
        }
        for (const { selectorWithTarget, toggle } of activeItems) {
            if (el.matches(selectorWithTarget)) {
                toggle(el, false);
            }
        }
    }

    // Dropped and cloned snippets do not become the target, so
    // `reveal_target_handlers` won't be called for them on redo. This function
    // calls `showInvisibleElement` if needed (and calls it again on redo)
    showNewElement(el, isClone) {
        const shouldShow = this.getResource("invisible_items").some(
            ({ selector, target, noShowAfterClone }) =>
                el.matches(selector) &&
                (!target || el.querySelector(target)) &&
                !(isClone && noShowAfterClone)
        );
        if (shouldShow) {
            this.dependencies.history.applyCustomMutation({
                apply: () => {
                    if (this.getResource("hidden_element_predicates").some((p) => p(el))) {
                        this.showInvisibleElement(el);
                    }
                },
                revert: () => {},
            });
        }
    }

    /**
     * Recompute content of the "invisible elements" panel
     */
    invalidateVisibility() {
        this.refreshInvisibleElementsPanel();
        const optionsTarget = this.dependencies.builderOptions.getTarget();
        if (
            optionsTarget &&
            this.getResource("hidden_element_predicates").some((p) => p(optionsTarget))
        ) {
            this.dependencies.builderOptions.deactivateContainers();
            this.dependencies.disableSnippets.disableUndroppableSnippets();
        }
    }

    refreshInvisibleElementsPanel() {
        this.invisibleElementsPanelState.invisibleEntries = this.getInvisibleEntries();
    }

    getInvisibleEntries() {
        const { activeItems, selectorAll } = this.activeItemsAndSelectorAll();
        const entries = new Map(
            [...this.editable.querySelectorAll(selectorAll)].map((el) => {
                const matchingItems = activeItems.filter(({ selectorWithTarget }) =>
                    el.matches(selectorWithTarget)
                );
                const visible = matchingItems.every(({ target }) =>
                    (target ? el.querySelector(target) : el).checkVisibility()
                );
                const entry = {
                    el,
                    toggleInvisibleEntry: () => {
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

registry.category("website-plugins").add(VisibilityPlugin.id, VisibilityPlugin);
registry.category("translation-plugins").add(VisibilityPlugin.id, VisibilityPlugin);

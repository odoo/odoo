import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { InvisibleElementsPanel } from "@html_builder/sidebar/invisible_elements_panel";
import { proxy } from "@odoo/owl";

/**
 * @typedef { Object } VisibilityShared
 * @property { VisibilityPlugin['invalidateVisibility'] } invalidateVisibility
 * @property { VisibilityPlugin['isElementHidden'] } isElementHidden
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
 * @property {boolean} showAfterClone set to `false` to prevent showing the
 * element on (the redo of) clone (defaults to `true` if absent)
 *
 * @typedef {InvisibleItem[]} invisible_items
 * @typedef {(() => void)[]} on_visibility_impacted_droppable_snippets_handlers
 */

export class VisibilityPlugin extends Plugin {
    static id = "visibility";
    static dependencies = ["builderOptions", "domObserver", "history"];
    static shared = ["invalidateVisibility", "isElementHidden"];

    invisibleElementsPanelState = proxy({ invisibleEntries: [] });

    /** @type {import("plugins").BuilderResources} */
    resources = {
        lower_panel_entries: withSequence(20, {
            Component: InvisibleElementsPanel,
            props: { state: this.invisibleElementsPanelState },
        }),
        on_editor_started_handlers: () => this.refreshInvisibleElementsPanel(),
        pending_history_commit_data_processors: withSequence(20, (data) => {
            if (this.dependencies.history.getIsPreviewing()) {
                return data;
            }
            const optionsTarget = data.nextTarget ?? data.currentTarget;
            if (optionsTarget && optionsTarget.isConnected && this.isElementHidden(optionsTarget)) {
                if (!data.relatedCommit) {
                    data.nextTarget = false;
                }
                this.trigger("on_visibility_impacted_droppable_snippets_handlers");
            }
            this.refreshInvisibleElementsPanel();
            return data;
        }),
        on_snippet_dropped_handlers: ({ snippetEl }) => {
            this.showInvisibleElement(snippetEl);
            // The snippet is not in the dom on revert, so we use the previous
            // or parent element to reveal the spot where the change occured
            const parentEl = snippetEl.parentElement;
            const prevEl = snippetEl.previousElementSibling;
            this.dependencies.domObserver.stageCustomMutation({
                apply: () => this.trigger("on_target_revealed_handlers", snippetEl),
                revert: () => {
                    this.showInvisibleElement(parentEl);
                    let el = prevEl;
                    while (el && this.isElementHidden(el)) {
                        el = el.previousElementSibling;
                    }
                    this.trigger("on_target_revealed_handlers", el ?? parentEl);
                },
            });
        },
        on_cloned_handlers: ({ cloneEl }) => {
            // Cloned snippet do not become the target, but we usually want to
            // show them when they are created
            const shouldShow = this.getResource("invisible_items").some(
                ({ selector, target, showAfterClone }) =>
                    cloneEl.matches(selector) &&
                    (!target || cloneEl.querySelector(target)) &&
                    (showAfterClone ?? true)
            );
            if (shouldShow) {
                this.dependencies.domObserver.applyCustomMutation({
                    apply: () => this.showInvisibleElement(cloneEl),
                    revert: () => {},
                });
            }
        },
        on_target_revealed_handlers: withSequence(5, (targetEl) => {
            this.showInvisibleElement(targetEl);
            this.refreshInvisibleElementsPanel();
        }),
        // The data-invisible attribute and the o_snippet_invisible class are
        // not needed/used anymore.
        // They were used to try to track if an element is or can be hidden.
        // They persisted through saves, so we remove them from existing pages.
        clean_for_save_processors: (root) => {
            for (const el of root.querySelectorAll("[data-invisible]")) {
                el.removeAttribute("data-invisible");
            }
            for (const el of root.querySelectorAll(".o_snippet_invisible")) {
                el.classList.remove("o_snippet_invisible");
            }
            return root;
        },
        is_element_in_invisible_panel_predicates: (el) =>
            el.matches(this.matchingItemsAndSelectorAll().selectorAll),
    };

    matchingItemsAndSelectorAll() {
        const activeItems = this.getResource("invisible_items")
            .filter(({ isAvailable }) => !isAvailable || isAvailable())
            .map((item) => ({
                ...item,
                selectorWithTarget: item.target
                    ? `${item.selector}:has(${item.target})`
                    : item.selector,
            }));
        return {
            getMatchingItems: (el) =>
                activeItems.filter(({ selectorWithTarget }) => el.matches(selectorWithTarget)),
            selectorAll:
                activeItems.map(({ selectorWithTarget }) => selectorWithTarget).join(", ") ||
                ":not(*)",
        };
    }

    // Show an element by calling the corresponding `toggle` from the
    // `invisible_items` on it and/or on its ancestors
    showInvisibleElement(el) {
        const { getMatchingItems, selectorAll } = this.matchingItemsAndSelectorAll();
        const _show = (el) => {
            if (!el) {
                return;
            }
            if (!el.checkVisibility()) {
                _show(el.parentElement?.closest(selectorAll));
            }
            for (const { toggle } of getMatchingItems(el)) {
                toggle(el, true);
            }
        };
        _show(el.closest(selectorAll));
    }

    hide(el) {
        const { getMatchingItems } = this.matchingItemsAndSelectorAll();
        for (const { toggle } of getMatchingItems(el)) {
            toggle(el, false);
        }
    }

    /**
     * Check whether the given element is currently hidden
     *
     * @param {HTMLElement} el
     */
    isElementHidden(el) {
        if (!el.checkVisibility()) {
            return true;
        }
        // el is visible, maybe it matches an item with hidden target
        const { getMatchingItems } = this.matchingItemsAndSelectorAll();
        for (const { target } of getMatchingItems(el)) {
            if (target && !el.querySelector(target).checkVisibility()) {
                return true;
            }
        }
        return false;
    }

    /**
     * Recompute content of the "invisible elements" panel
     */
    invalidateVisibility() {
        this.refreshInvisibleElementsPanel();
        const optionsTarget = this.dependencies.builderOptions.getTarget();
        if (optionsTarget && this.isElementHidden(optionsTarget)) {
            this.dependencies.builderOptions.deactivateContainers();
            this.trigger("on_visibility_impacted_droppable_snippets_handlers");
        }
    }

    refreshInvisibleElementsPanel() {
        this.invisibleElementsPanelState.invisibleEntries = this.getInvisibleEntries();
    }

    getInvisibleEntries() {
        const { getMatchingItems, selectorAll } = this.matchingItemsAndSelectorAll();
        const entries = new Map(
            [...this.editable.querySelectorAll(selectorAll)].map((el) => {
                const visible = getMatchingItems(el).every(({ target }) =>
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
                            this.trigger("on_target_revealed_handlers", el);
                            this.dependencies.builderOptions.updateContainers(el);
                        }
                        this.trigger("on_visibility_impacted_droppable_snippets_handlers");
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

import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

/** @typedef {import("plugins").LazyTranslatedString} LazyTranslatedString */
/** @typedef {import("plugins").CSSSelector} CSSSelector */
/**
 * @typedef {{
 *      label: LazyTranslatedString;
 *      containerSelector: CSSSelector;
 *      isThisPage?: Boolean;
 * }[]} floating_snippet_scope_providers
 *
 * Register snippet scopes for the "Show on" dropdown. `containerSelector`
 * points to a container where the snippet might be stored.
 *
 * Ordering (via `withSequence`) matters: providers are checked in sequence
 * order and the first `this page` container whose `containerSelector` matches
 * a container on the page wins.
 *
 * @typedef {import("plugins").CSSSelector[]} floating_snippets_selectors
 * Snippets that do not depend on their position in the dom.
 */

export class FloatingSnippetsPlugin extends Plugin {
    static id = "floatingSnippets";
    static shared = ["getShowOnScopes"];

    resources = {
        builder_actions: {
            MoveBlockAction,
        },
        on_snippet_dropped_handlers: withSequence(0, this.onSnippetDropped.bind(this)),
        floating_snippet_scope_providers: [
            withSequence(50, {
                label: _t("This page"),
                containerSelector: "main .oe_structure.o_savable",
                isThisPage: true,
            }),
            // On some pages we want to prioritize this container, instead of
            // the one above, as it isn't very specific, and can target a shared
            // container instead.
            withSequence(40, {
                label: _t("This page"),
                containerSelector: "#wrap .o_savable[data-oe-field='description']",
                isThisPage: true,
            }),
            withSequence(1, {
                label: _t("All pages"),
                containerSelector: "#o_shared_blocks",
            }),
        ],
    };

    setup() {
        this.snippetSelectors = this.getResource("floating_snippets_selectors").join(", ");
        this.availableShowOnScopes = this.getShowOnScopes();
    }

    getShowOnScopes() {
        const availableShowOnScopes = [];
        let hasThisPageProvider = false;
        let previousSelectors = "";
        for (const provider of this.getResource("floating_snippet_scope_providers")) {
            // We want to add a selector for the "current" page only once.
            if (provider.isThisPage && hasThisPageProvider) {
                continue;
            }
            // To prevent a case when a user selects "This page" but it moves
            // the snippet to the end of some other scope provider, because
            // their selectors overlap, we exclude the previous selectors.
            const containerSelector = previousSelectors
                ? `:is(${provider.containerSelector}):not(${previousSelectors})`
                : provider.containerSelector;
            const containerEl = this.editable.querySelector(containerSelector);
            if (containerEl && containerEl.closest(".o_savable")) {
                availableShowOnScopes.push({ ...provider, containerSelector });
                previousSelectors = previousSelectors
                    ? `${previousSelectors}, ${provider.containerSelector}`
                    : provider.containerSelector;
                hasThisPageProvider ||= provider.isThisPage;
            }
        }
        return availableShowOnScopes;
    }

    onSnippetDropped({ snippetEl, dragState }) {
        if (!snippetEl.matches(this.snippetSelectors)) {
            return;
        }
        // If it wasn't drag and dropped, we would like to move it to the first
        // "this page" container.
        if (!Object.keys(dragState).length) {
            const thisPageScope = this.availableShowOnScopes.find((scope) => scope.isThisPage);
            if (thisPageScope) {
                const containerEl = this.editable.querySelector(thisPageScope.containerSelector);
                containerEl.insertAdjacentElement("beforeend", snippetEl);
                return;
            }
        }
        // Otherwise, find where it was dropped, and move it to the end of that
        // container.
        for (const scope of this.availableShowOnScopes) {
            const containerEl = snippetEl.closest(scope.containerSelector);
            if (containerEl && containerEl.closest(".o_savable")) {
                // We want to place those snippets at the end of the container
                // they were dropped in.
                containerEl.insertAdjacentElement("beforeend", snippetEl);
                return;
            }
        }
        // Place the snippets at the end of the current o_savable.
        const containerEl = snippetEl.closest(".o_savable");
        containerEl.insertAdjacentElement("beforeend", snippetEl);
    }
}

// Moves the snippet into the right container depending on its
// "show on" scope (current page, all pages or dedicated scoped
// container).
export class MoveBlockAction extends BuilderAction {
    static id = "moveBlock";
    setup() {
        this.preview = false;
    }
    getPriority({ params: { isThisPage } }) {
        // Some container providers might be missing, in that case we want to
        // display them as active, but they should have the lowest priority, so
        // they are active only if there's no other container that matches the
        // selector.
        return isThisPage ? 0 : 1;
    }
    isApplied({ editingElement, params: { selector, isThisPage } }) {
        return !!editingElement.closest(selector) || isThisPage;
    }
    apply({ editingElement, params: { selector } }) {
        const targetEl = editingElement.closest("[data-snippet]");
        const containerEl = this.editable.querySelector(selector);
        containerEl.insertAdjacentElement("beforeend", targetEl);
    }
}

export class ShowOnOption extends BaseOptionComponent {
    static id = "show_on_option";
    static template = "website.ShowOnOption";
    static dependencies = ["floatingSnippets"];

    setup() {
        super.setup();
        this.availableShowOnScopes = this.dependencies.floatingSnippets.getShowOnScopes();
    }
}

registry.category("website-plugins").add(FloatingSnippetsPlugin.id, FloatingSnippetsPlugin);

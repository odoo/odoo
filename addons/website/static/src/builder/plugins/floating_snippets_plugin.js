import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class FloatingSnippetsPlugin extends Plugin {
    static id = "floatingSnippets";

    resources = {
        builder_actions: {
            MoveBlockAction,
        },
        on_snippet_dropped_handlers: withSequence(0, this.onSnippetDropped.bind(this)),
        floating_snippet_scope_providers: [
            withSequence(50, {
                value: "currentPage",
                label: _t("This page"),
                containerSelector: "main .oe_structure.o_savable",
            }),
            withSequence(10, {
                value: "allPages",
                label: _t("All pages"),
                containerSelector: "#o_shared_blocks",
            }),
        ],
    };

    setup() {
        this.snippetSelectors = this.getResource("floating_snippets_selectors").join(", ");
    }

    onSnippetDropped({ snippetEl }) {
        if (!snippetEl.matches(this.snippetSelectors)) {
            return;
        }
        for (const provider of this.getResource("floating_snippet_scope_providers")) {
            const containerEls = this.editable.querySelectorAll(provider.containerSelector);
            for (const containerEl of containerEls) {
                if (containerEl.contains(snippetEl)) {
                    // We want to place those snippets at the end of the container
                    // they were dropped in.
                    containerEl.insertAdjacentElement("beforeend", snippetEl);
                    snippetEl.dataset.showOn = provider.value;
                    return;
                }
            }
        }
        // Otherwise, place the snippets at the end of the current o_savable.
        const containerEl = snippetEl.closest(".o_savable");
        containerEl.insertAdjacentElement("beforeend", snippetEl);
        snippetEl.dataset.showOn = "currentPage";
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
    isApplied({ editingElement, value }) {
        const targetEl = editingElement.closest("[data-snippet]");
        if (targetEl?.dataset.showOn) {
            return targetEl.dataset.showOn === value;
        }
        // Fallback for existing snippets saved without data-show-on.
        if (targetEl?.closest("#o_shared_blocks")) {
            return value === "allPages";
        }
        return value === "currentPage";
    }
    apply({ editingElement, value, params: { mainParam: containerSelector } }) {
        const targetEl = editingElement.closest("[data-snippet]");
        const containerEl = this.editable.querySelector(containerSelector);
        targetEl.dataset.showOn = value;
        containerEl?.insertAdjacentElement("beforeend", targetEl);
    }
}

/** @typedef {import("plugins").CSSSelector} CSSSelector */
/** @typedef {import("plugins").LazyTranslatedString} LazyTranslatedString */
/**
 * @typedef {{
 *      value: string;
 *      label: LazyTranslatedString;
 *      containerSelector: CSSSelector | null;
 * }[]} floating_snippet_scope_providers
 *
 * Register snippet presense scopes for the "Show on" dropdown.
 * `value` is stored in `data-show-on` on the snippet.
 * `containerSelector` points to a container where the snippet might be
 *  stored.
 *
 * Ordering (via `withSequence`) matters: providers are checked in
 * sequence order and the first one whose `containerSelector` matches a
 * container on the page wins.
 */

export class ShowOnOption extends BaseOptionComponent {
    static id = "show_on_option";
    static template = "website.ShowOnOption";
    static dependencies = ["floatingSnippets"];

    setup() {
        super.setup();
        this.availableShowOnScopes = [];
        // We don't want to have 2 options with the same value, e.g.,
        // "This Page", so we keep the first one we see.
        const seenScopeValues = new Set();
        for (const provider of this.getResource("floating_snippet_scope_providers")) {
            if (
                !seenScopeValues.has(provider.value) &&
                !!this.editable.querySelector(provider.containerSelector)
            ) {
                this.availableShowOnScopes.push(provider);
                seenScopeValues.add(provider.value);
            }
        }
    }
}

registry.category("website-plugins").add(FloatingSnippetsPlugin.id, FloatingSnippetsPlugin);

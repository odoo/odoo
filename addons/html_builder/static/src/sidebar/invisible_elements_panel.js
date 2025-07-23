import { Component, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";
import { getSnippetName, isElementInViewport } from "@html_builder/utils/utils";

export class InvisibleElementsPanel extends Component {
    static template = "html_builder.InvisibleElementsPanel";
    static props = {
        invisibleEls: { type: Array },
        invisibleSelector: { type: String },
    };

    setup() {
        this.state = useState({ invisibleEntries: null });

        onWillStart(() => this.updateInvisibleElementsPanel(this.props.invisibleEls));

        onWillUpdateProps((nextProps) => {
            const { invisibleEls, invisibleSelector } = nextProps;
            this.updateInvisibleElementsPanel(invisibleEls, invisibleSelector);
        });
    }

    get shared() {
        return this.env.editor.shared;
    }

    updateInvisibleElementsPanel(invisibleEls, invisibleSelector = this.props.invisibleSelector) {
        // descendantPerSnippet: a map with its keys set to invisible
        // snippets that have invisible descendants. The value corresponding
        // to an invisible snippet element is a list filled with all its
        // descendant invisible snippets except those that have a closer
        // invisible snippet ancestor.
        const descendantPerSnippet = new Map();
        // Filter the invisibleEls to only keep the root snippets
        // and create the map ("descendantPerSnippet") of the snippets and
        // their descendant snippets.
        const rootInvisibleSnippetEls = invisibleEls.filter((invisibleSnippetEl) => {
            const ancestorInvisibleEl = invisibleSnippetEl.parentElement.closest(invisibleSelector);
            if (!ancestorInvisibleEl) {
                return true;
            }
            const descendantSnippets = descendantPerSnippet.get(ancestorInvisibleEl) || [];
            descendantPerSnippet.set(ancestorInvisibleEl, [
                ...descendantSnippets,
                invisibleSnippetEl,
            ]);
            return false;
        });
        // Insert all the invisible snippets contained in "snippetEls" as
        // well as their descendants in the "parentEl" element. If
        // "snippetEls" is set to "rootInvisibleSnippetEls" and "parentEl"
        // is set to "$invisibleDOMPanelEl[0]", then fills the right
        // invisible panel like this:
        // rootInvisibleSnippet
        //     └ descendantInvisibleSnippet
        //          └ descendantOfDescendantInvisibleSnippet
        //               └ etc...
        const createInvisibleEntries = (snippetEls, parentEl = null) =>
            snippetEls.map((snippetEl) => {
                const descendantSnippetEls = descendantPerSnippet.get(snippetEl);
                // An element is considered as "RootParent" if it has one or
                // more invisible descendants but is not a descendant.
                const invisibleElement = {
                    snippetEl: snippetEl,
                    name: getSnippetName(snippetEl),
                    isRootParent: !parentEl && !!descendantSnippetEls,
                    isDescendant: !!parentEl,
                    isVisible: snippetEl.dataset.invisible !== "1",
                    children: [],
                    parentEl,
                };
                if (descendantSnippetEls) {
                    invisibleElement.children = createInvisibleEntries(
                        descendantSnippetEls,
                        invisibleElement
                    );
                }
                return invisibleElement;
            });
        this.state.invisibleEntries = createInvisibleEntries(rootInvisibleSnippetEls);
    }

    toggleElementVisibility(invisibleEntry) {
        const snippetEl = invisibleEntry.snippetEl;
        if (invisibleEntry.isVisible) {
            // Toggle the entry visibility to "Hide".
            invisibleEntry.isVisible = false;
            this.shared.visibility.toggleTargetVisibility(snippetEl, false);
            this.shared.builderOptions.deactivateContainers();
        } else {
            // Toggle the entry visibility to "Show".
            invisibleEntry.isVisible = true;
            this.shared.visibility.toggleTargetVisibility(snippetEl, true);
            this.shared.builderOptions.updateContainers(snippetEl);
            // Scroll to the target if not visible.
            if (!isElementInViewport(snippetEl) && !snippetEl.matches(".s_popup")) {
                snippetEl.scrollIntoView({ behavior: "smooth", block: "center" });
            }
        }
        this.shared.disableSnippets.disableUndroppableSnippets();
    }
}

import { Component, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";
import { WithSubEnv } from "../builder_helpers";
import { getSnippetName } from "../../utils";
export class InvisibleElementsPanel extends Component {
    static template = "html_builder.InvisibleElementsPanel";
    static components = { WithSubEnv };
    static props = {
        invisibleEls: { type: Array },
        invisibleSelector: { type: String },
    };

    setup() {
        this.state = useState({ invisibleEntries: null });

        onWillStart(() => this.updateInvisibleElementsPanel(this.props.invisibleEls));

        onWillUpdateProps((nextProps) => {
            this.updateInvisibleElementsPanel(nextProps["invisibleEls"]);
        });
    }

    updateInvisibleElementsPanel(invisibleEls) {
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
            const ancestorInvisibleEl = invisibleSnippetEl.parentElement.closest(
                this.props.invisibleSelector
            );
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
        const createInvisibleEntries = (snippetEls, isDescendant) =>
            snippetEls.map((snippetEl) => {
                const descendantSnippetEls = descendantPerSnippet.get(snippetEl);
                // An element is considered as "RootParent" if it has one or
                // more invisible descendants but is not a descendant.
                const invisibleElement = {
                    snippetEl: snippetEl,
                    name: getSnippetName(snippetEl),
                    isRootParent: !isDescendant && !!descendantSnippetEls,
                    isDescendant,
                    isVisible: snippetEl.dataset.invisible !== "1",
                    children: [],
                };
                if (descendantSnippetEls) {
                    invisibleElement.children = createInvisibleEntries(descendantSnippetEls, true);
                }
                return invisibleElement;
            });
        this.state.invisibleEntries = createInvisibleEntries(rootInvisibleSnippetEls, false);
    }

    toggleElementVisibility(invisibleEntry) {
        const snippetEl = invisibleEntry.snippetEl;
        const isVisibleEl = isSnippetVisible(snippetEl);
        setSnippetVisibility(invisibleEntry, !isVisibleEl);
    }
}

function isSnippetVisible(snippetEl) {
    return snippetEl.dataset.invisible !== "1";
}

function setSnippetVisibility(invisibleEntry, show) {
    const snippetEl = invisibleEntry.snippetEl;
    invisibleEntry.isVisible = show;
    if (show) {
        delete snippetEl.dataset.invisible;
        return;
    }
    snippetEl.dataset.invisible = "1";
    // TODO call the options linked to the snippet to display or hide the
    // snippet.
}

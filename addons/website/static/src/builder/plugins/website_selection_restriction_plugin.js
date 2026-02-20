import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class WebsiteSelectionRestrictionPlugin extends Plugin {
    static id = "websiteSelectionRestriction";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        // restricted_to_paragraph_blocks_selector: CSS selectors of elements
        // that the selection should be restricted to paragraph blocks.
        restricted_to_paragraph_blocks_selector: [".s_blockquote"],
        ignore_ctrl_a_predicates: (selection) => {
            const { anchorNode, commonAncestorContainer } = selection;
            // If we clicked on an image inside a <figure> element, keep the
            // selection on the image only, to not select the whole <figure>.
            const isFigure = commonAncestorContainer.nodeName === "FIGURE";
            // When main body is empty, and click the footer outer blue
            // container then ctrl+a, the selection is collapsed in editable but
            // to the main body div, which causes options updating.
            const isMainBodyEmpty = anchorNode.isContentEditable === false && selection.isCollapsed;
            return isFigure || isMainBodyEmpty;
        },
        uncrossable_element_selector: [".s_cta_badge"],
    };
}

registry
    .category("website-plugins")
    .add(WebsiteSelectionRestrictionPlugin.id, WebsiteSelectionRestrictionPlugin);

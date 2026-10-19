import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class WebsiteSelectionRestrictionPlugin extends Plugin {
    static id = "websiteSelectionRestriction";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        ignore_ctrl_a_predicates: (selection) => {
            const { anchorNode } = selection;
            // When main body is empty, if we click on the footer (not in its
            // content) then ctrl+a, the selection is collapsed in editable but
            // to the main body div, which causes options updating.
            if (anchorNode.isContentEditable === false && selection.isCollapsed) {
                return true;
            }
        },
        uncrossable_element_selector: [
            ".s_cta_badge",
            ".s_blockquote_line_elt",
            ".s_blockquote_wrap_icon",
            ".s_blockquote_infos",
        ],
    };
}

registry
    .category("website-plugins")
    .add(WebsiteSelectionRestrictionPlugin.id, WebsiteSelectionRestrictionPlugin);

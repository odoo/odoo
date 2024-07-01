/** @odoo-module **/

import { registry } from "@web/core/registry";
import {
    MultipleItems,
    SnippetOption,
} from "@web_editor/js/editor/snippets.options";
import {
    registerWebsiteOption,
} from "@website/js/editor/snippets.registry";

export class TimelineOption extends SnippetOption {
    static displayOverlayOptions = true;

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Moves the card to the right/left.
     *
     * @see this.selectClass for parameters
     */
    timelineCard(previewMode, widgetValue, params) {
        const timelineRowEl = this.$target[0].closest(".s_timeline_row");
        timelineRowEl.classList.toggle("flex-md-row-reverse");
        timelineRowEl.classList.toggle("flex-md-row");
        this.$target[0].classList.toggle("text-md-end");
    }
}

registerWebsiteOption("Timeline (Multiple)", {
    Class: MultipleItems,
    template: "website.s_timeline_multiple_option",
    selector: ".s_timeline",
});
registerWebsiteOption("Timeline (Move row)", {
    selector: ".s_timeline_row",
    dropNear: ".s_timeline_row",
});
registerWebsiteOption("Timeline (Overlay)", {
    Class: TimelineOption,
    template: "website.s_timeline_overlay_option",
    selector: ".s_timeline_card",
});
registerWebsiteOption("Timeline (Color)", {
    template: "website.s_timeline_color_option",
    selector: ".s_timeline",
});
registerWebsiteOption("Timeline (Dot Color)", {
    template: "website.s_timeline_row_color_option",
    selector: ".s_timeline_row",
});

const SnippetMoveOption = registry.category("snippet_options").get("SnippetMove (Vertical)");
SnippetMoveOption.selector = SnippetMoveOption.selector + ", .s_timeline_row";
registry.category("snippet_options").add("SnippetMove (Vertical)", SnippetMoveOption, { force: true });

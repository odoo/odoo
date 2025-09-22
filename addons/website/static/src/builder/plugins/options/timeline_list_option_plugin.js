import { BaseOptionComponent } from "@html_builder/core/utils";
import { after, SNIPPET_SPECIFIC, SNIPPET_SPECIFIC_END } from "@html_builder/utils/option_sequence";
import { WEBSITE_BACKGROUND_OPTIONS } from "@website/builder/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export const TIMELINE = after(WEBSITE_BACKGROUND_OPTIONS)
export const TIMELINE_ALIGNMENT = after(SNIPPET_SPECIFIC_END);

export class TimelineListOption extends BaseOptionComponent {
    static template = "website.TimelineListOption";
    static selector = ".s_timeline_list";
}

export class TimelineListAlignmentOption extends BaseOptionComponent {
    static template = "website.TimelineListAlignmentOption";
    static selector = ".s_timeline_list";
}

export class DotLinesColorOption extends BaseOptionComponent {
    static template = "website.DotLinesColorOption";
    static selector = ".s_timeline_list";
}

export class DotColorOption extends BaseOptionComponent {
    static template = "website.DotColorOption";
    static selector = ".s_timeline_list .s_timeline_list_row";
}

class TimelineListOptionPlugin extends Plugin {
    static id = "timelineListOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        remove_disabled_reason_providers: ({ el, reasons }) => {
            if (this.isLastTimelineListItem(el)) {
                reasons.push(_t("You can't remove the last item."));
            }
        },
        builder_options: [
            // TODO AGAU: alignment option sequence doesn't match master, must split template
            withSequence(TIMELINE, TimelineListOption),
            withSequence(SNIPPET_SPECIFIC_END, DotLinesColorOption),
            withSequence(TIMELINE_ALIGNMENT, TimelineListAlignmentOption),
            withSequence(SNIPPET_SPECIFIC, DotColorOption),
        ],
        dropzone_selector: {
            selector: ".s_timeline_list_row",
            dropNear: ".s_timeline_list_row",
        },
        is_movable_selector: { selector: ".s_timeline_list_row", direction: "vertical" },
    };

    isLastTimelineListItem(el) {
        const wrapperEl = el.closest(".s_timeline_list_wrapper > div");
        return wrapperEl && wrapperEl.childElementCount === 1;
    }
}

registry.category("website-plugins").add(TimelineListOptionPlugin.id, TimelineListOptionPlugin);

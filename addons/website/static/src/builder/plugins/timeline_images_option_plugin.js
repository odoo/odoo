import { BaseOptionComponent } from "@html_builder/core/utils";
import { after, SNIPPET_SPECIFIC, SNIPPET_SPECIFIC_END } from "@html_builder/utils/option_sequence";
import { WEBSITE_BACKGROUND_OPTIONS } from "@website/builder/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export const TIMELINE = after(WEBSITE_BACKGROUND_OPTIONS);

export class TimelineImagesOption extends BaseOptionComponent {
    static template = "website.TimelineImagesOption";
    static selector = ".s_timeline_images";
}

export class DotLinesColorOption extends BaseOptionComponent {
    static template = "website.DotLinesColorOption";
    static selector = ".s_timeline_images";
}

export class DotColorOption extends BaseOptionComponent {
    static template = "website.DotColorOption";
    static selector = ".s_timeline_images .s_timeline_images_row";
}

class TimelineImagesOptionPlugin extends Plugin {
    static id = "timelineImagesOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        remove_disabled_reason_providers: ({ el, reasons }) => {
            if (this.isLastTimelineImageItem(el)) {
                reasons.push(_t("You can't remove the last item."));
            }
        },
        builder_options: [
            withSequence(TIMELINE, TimelineImagesOption),
            withSequence(SNIPPET_SPECIFIC_END, DotLinesColorOption),
            withSequence(SNIPPET_SPECIFIC, DotColorOption),
        ],
        dropzone_selector: {
            selector: ".s_timeline_images_row",
            dropNear: ".s_timeline_images_row",
        },
        is_movable_selector: { selector: ".s_timeline_images_row", direction: "vertical" },
    };

    isLastTimelineImageItem(el) {
        const timelineEl = el.closest(".s_timeline_images");
        if (timelineEl) {
            // Check if it's the last row
            if (el.classList.contains("s_timeline_images_row")) {
                return timelineEl.querySelectorAll(".s_timeline_images_row").length === 1;
            }

            // Check if it's the last column
            if (el.matches(".s_timeline_images_content .row > div")) {
                return (
                    timelineEl.querySelectorAll(".s_timeline_images_content .row > div").length ===
                    1
                );
            }
        }
        return false;
    }
}

registry.category("website-plugins").add(TimelineImagesOptionPlugin.id, TimelineImagesOptionPlugin);

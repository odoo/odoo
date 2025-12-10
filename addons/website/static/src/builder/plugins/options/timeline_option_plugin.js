import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { localization } from "@web/core/l10n/localization";
import { registry } from "@web/core/registry";
import { after, before, SNIPPET_SPECIFIC_END } from "@html_builder/utils/option_sequence";
import { WEBSITE_BACKGROUND_OPTIONS } from "@website/builder/option_sequence";
import { BaseOptionComponent } from "@html_builder/core/utils";

export const TIMELINE = before(WEBSITE_BACKGROUND_OPTIONS);
export const DOT_LINES_COLOR = SNIPPET_SPECIFIC_END;
export const DOT_COLOR = after(DOT_LINES_COLOR);

function isTimelineCard(el) {
    return el.matches(".s_timeline_card");
}

export class TimelineOption extends BaseOptionComponent {
    static template = "website.TimelineOption";
    static selector = ".s_timeline";
}

export class DotLinesColorOption extends BaseOptionComponent {
    static template = "website.DotLinesColorOption";
    static selector = ".s_timeline";
}

export class DotColorOption extends BaseOptionComponent {
    static template = "website.DotColorOption";
    static selector = ".s_timeline .s_timeline_row";
}

class TimelineOptionPlugin extends Plugin {
    static id = "timelineOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: [
            withSequence(TIMELINE, TimelineOption),
            withSequence(DOT_LINES_COLOR, DotLinesColorOption),
            withSequence(DOT_COLOR, DotColorOption),
        ],
        dropzone_selector: {
            selector: ".s_timeline_row",
            dropNear: ".s_timeline_row",
        },
        has_overlay_options: { hasOption: (el) => isTimelineCard(el) },
        get_overlay_buttons: withSequence(0, {
            getButtons: this.getActiveOverlayButtons.bind(this),
        }),
        is_movable_selector: { selector: ".s_timeline_row", direction: "vertical" },
    };

    setup() {
        this.isEditableRTL = this.config.isEditableRTL;
        this.isBackendRTL = localization.direction === "rtl";
    }

    getActiveOverlayButtons(target) {
        if (!isTimelineCard(target)) {
            this.overlayTarget = null;
            return [];
        }

        this.overlayTarget = target;
        const timelineRowEl = this.overlayTarget.closest(".s_timeline_row");
        const firstContentEl = timelineRowEl.querySelector(".s_timeline_content");
        const hasPreviousCard = !firstContentEl.contains(this.overlayTarget);
        const reverseButtons = this.isEditableRTL !== this.isBackendRTL;
        const direction = hasPreviousCard !== reverseButtons ? "left" : "right";
        return [
            {
                class: `fa fa-fw fa-angle-${direction}`,
                title: hasPreviousCard !== this.isEditableRTL ? _t("Move left") : _t("Move right"),
                handler: this.moveTimelineCard.bind(this),
            },
        ];
    }

    moveTimelineCard() {
        const timelineRowEl = this.overlayTarget.closest(".s_timeline_row");
        const timelineCardEls = timelineRowEl.querySelectorAll(".s_timeline_card");
        const firstContentEl = timelineRowEl.querySelector(".s_timeline_content");
        timelineRowEl.append(firstContentEl);
        timelineCardEls.forEach((card) => card.classList.toggle("text-md-end"));
    }
}

registry.category("website-plugins").add(TimelineOptionPlugin.id, TimelineOptionPlugin);

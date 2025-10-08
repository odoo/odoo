import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { localization } from "@web/core/l10n/localization";
import { registry } from "@web/core/registry";
import { after, before, SNIPPET_SPECIFIC_END } from "@html_builder/utils/option_sequence";
import { WEBSITE_BACKGROUND_OPTIONS } from "@website/builder/option_sequence";

export const TIMELINE = before(WEBSITE_BACKGROUND_OPTIONS);
export const DOT_LINES_COLOR = SNIPPET_SPECIFIC_END;
export const DOT_COLOR = after(DOT_LINES_COLOR);

function isTimelineCard(el) {
    return el.matches(".s_timeline_card");
}
function isTimelineRow(el) {
    return el.matches(".s_timeline_row");
}

class TimelineOptionPlugin extends Plugin {
    static id = "timelineOption";
    static dependencies = ["history"];
    resources = {
        remove_disabled_reason_providers: ({ el, reasons }) => {
            if (this.isLastTimelineItem(el)) {
                reasons.push(_t("You cannot remove the last item."));
            }
        },
        builder_options: [
            withSequence(TIMELINE, {
                template: "website.TimelineOption",
                selector: ".s_timeline",
            }),
            withSequence(DOT_LINES_COLOR, {
                template: "website.DotLinesColorOption",
                selector: ".s_timeline",
            }),
            withSequence(DOT_COLOR, {
                template: "website.DotColorOption",
                selector: ".s_timeline .s_timeline_row",
            }),
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

    isLastTimelineItem(el) {
        const timeline = el.closest(".s_timeline");
        if (!timeline) return false;

        const timelineRows = timeline.querySelectorAll(".s_timeline_row");
        if (timelineRows.length !== 1) return false;

        if (isTimelineRow(el)) {
            return true;
        }
        if (isTimelineCard(el)) {
            const cards = timelineRows[0].querySelectorAll(".s_timeline_card");
            return cards.length === 1;
        }
        return false;
    }
}

registry.category("website-plugins").add(TimelineOptionPlugin.id, TimelineOptionPlugin);

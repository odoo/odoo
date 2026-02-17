import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { localization } from "@web/core/l10n/localization";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";

function isTimelineCard(el) {
    return el.matches(".s_timeline_card");
}

export class TimelineOptionPlugin extends Plugin {
    static id = "timelineOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
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

import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

function isTimelineCard(el) {
    return el.matches(".s_timeline_card");
}

class TimelineOptionPlugin extends Plugin {
    static id = "timelineOption";
    static dependencies = ["history"];
    resources = {
        builder_options: [
            withSequence(5, {
                template: "html_builder.TimelineOption",
                selector: ".s_timeline",
            }),
            withSequence(10, {
                template: "html_builder.DotLinesColorOption",
                selector: ".s_timeline",
            }),
            withSequence(5, {
                template: "html_builder.DotColorOption",
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
    };

    getActiveOverlayButtons(target) {
        if (!isTimelineCard(target)) {
            this.overlayTarget = null;
            return [];
        }

        this.overlayTarget = target;
        const timelineRowEl = this.overlayTarget.closest(".s_timeline_row");
        const firstContentEl = timelineRowEl.querySelector(".s_timeline_content");
        const hasPreviousCard = !firstContentEl.contains(this.overlayTarget);
        const direction = hasPreviousCard ? "left" : "right";
        return [
            {
                class: `fa fa-fw fa-angle-${direction}`,
                title: _t("Move %s", direction),
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

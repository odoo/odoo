import { isElement } from "@html_editor/utils/dom_info";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { BuilderAction } from "@html_builder/core/builder_action";
import { _t } from "@web/core/l10n/translation";
import { localization } from "@web/core/l10n/localization";
import { registry } from "@web/core/registry";
import { renderToElement } from "@web/core/utils/render";

function isTimelineCard(el) {
    return el.matches(".s_timeline_card");
}

export class TimelineOptionPlugin extends Plugin {
    static id = "timelineOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            AddMilestoneAction,
        },
        dropzone_selectors: {
            selector: ".s_timeline_row",
            dropNear: ".s_timeline_row",
        },
        has_overlay_options: { hasOption: (el) => isTimelineCard(el) },
        get_overlay_buttons: withSequence(0, {
            getButtons: this.getActiveOverlayButtons.bind(this),
        }),
        is_movable_selectors: { selector: ".s_timeline_row", direction: "vertical" },
        auto_unfold_container_providers: { selector: ".s_timeline_row", target: ".s_timeline" },
        remove_disabled_reason_providers: (el) => {
            if (this.isLastTimelineItem(el)) {
                return _t("You cannot remove the last item.");
            }
        },
        is_node_empty_predicates: (el) => {
            if (isElement(el) && el.matches(".s_timeline_row")) {
                return !el.querySelector(".s_timeline_card");
            }
        },
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
        // Check if it's the last row
        if (el.matches(".s_timeline_row:only-child")) {
            return true;
        }
        // Check if it's the last card in the last present row
        if (el.matches(".s_timeline_row:only-child .s_timeline_card")) {
            return el.closest(".s_timeline_row").querySelectorAll(".s_timeline_card").length === 1;
        }
        return false;
    }
}

export class AddMilestoneAction extends BuilderAction {
    static id = "addMilestone";
    static dependencies = ["builderOptions"];

    apply({ editingElement, value: position }) {
        const lastRowEl = [...editingElement.querySelectorAll(".s_timeline_row")].at(-1);
        // Clone to preserve the style of the dot and the line.
        const dotEl = lastRowEl.querySelector(".o_dot").cloneNode();
        const dotLineEl = lastRowEl.querySelector(".o_dot_line").cloneNode();

        const newRowEl = renderToElement("website.s_timeline_row_additional", { position });
        newRowEl.prepend(dotEl);
        newRowEl.prepend(dotLineEl);
        lastRowEl.after(newRowEl);
        this.dependencies.builderOptions.setNextTarget(newRowEl);
    }
}

registry.category("website-plugins").add(TimelineOptionPlugin.id, TimelineOptionPlugin);

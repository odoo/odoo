import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { localization } from "@web/core/l10n/localization";
import { registry } from "@web/core/registry";
import { after, SNIPPET_SPECIFIC, SNIPPET_SPECIFIC_END } from "@html_builder/utils/option_sequence";
import { WEBSITE_BACKGROUND_OPTIONS } from "@website/builder/option_sequence";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { BuilderAction } from "@html_builder/core/builder_action";
import { renderToElement } from "@web/core/utils/render";

export const TIMELINE = after(WEBSITE_BACKGROUND_OPTIONS);

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

export class AddMilestoneAction extends BuilderAction {
    static id = "addMilestone";
    static dependencies = ["selection", "builderOptions"];
    apply({ editingElement, value: position }) {
        const rowContainerEl = editingElement.querySelector(".s_timeline_row_container");
        // Clone dot Element to preserve same styling of the last element.
        const dotElements = rowContainerEl.querySelectorAll(".o_dot");
        const newDotEL = dotElements[dotElements.length - 1]?.cloneNode();
        // Clone line ELement to preserve same styling.
        const newDotLineEl = rowContainerEl.querySelector(".o_dot_line")?.cloneNode();
        const newRowEl = renderToElement("website.s_timeline_row_additional", {
            position,
        });

        newRowEl.prepend(newDotEL);
        newRowEl.prepend(newDotLineEl);
        rowContainerEl.append(newRowEl);
        this.dependencies.builderOptions.setNextTarget(newRowEl);
    }
}

class TimelineOptionPlugin extends Plugin {
    static id = "timelineOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: [
            withSequence(TIMELINE, TimelineOption),
            withSequence(SNIPPET_SPECIFIC_END, DotLinesColorOption),
            withSequence(SNIPPET_SPECIFIC, DotColorOption),
        ],
        builder_actions: {
            AddMilestoneAction,
        },
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
        this.upgradeSnippet();
    }

    // TODO: Remove this method when data-vxml is reintroduced.
    upgradeSnippet() {
        // This is for pages which already existed before the plugin was
        // created.
        const timelineEls = this.document.querySelectorAll(".s_timeline");
        timelineEls.forEach((timelineEl) => {
            timelineEl
                .querySelector(".o_container_small div")
                ?.classList.add("s_timeline_row_container");
        });
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

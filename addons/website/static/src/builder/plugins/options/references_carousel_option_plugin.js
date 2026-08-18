import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

const itemSelector = ".s_references_carousel_item";

export class ReferencesCarouselOptionPlugin extends Plugin {
    static id = "referencesCarouselOption";

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        mark_color_level_selector_params: [{ selector: itemSelector }],
        dropzone_selectors: {
            selector: itemSelector,
            dropNear: itemSelector,
            dropLockWithin: ".s_references_carousel",
        },
        is_movable_selectors: { selector: itemSelector, direction: "horizontal" },
        // A logo is duplicated or removed with its reference: on its own, it
        // would share or empty a cell.
        is_unremovable_selectors: `${itemSelector} img`,
        // The logos share the editable container of the title: keep text out
        // of the strip, `o_editable_media` keeps the logos replaceable.
        content_not_editable_selectors: [".s_references_carousel_marquee_wrapper"],
        auto_unfold_container_providers: { selector: `${itemSelector} img`, target: itemSelector },
        remove_disabled_reason_providers: (el) => {
            if (el.matches(`${itemSelector}:only-child`)) {
                return _t("You cannot remove the last item.");
            }
        },
        on_cloned_handlers: ({ cloneEl }) => {
            if (cloneEl.matches(itemSelector)) {
                // The logos scroll horizontally in edit mode: bring the new
                // one into view, or its selection overlay is drawn off-page.
                cloneEl.scrollIntoView({ block: "nearest", inline: "nearest" });
            }
        },
    };
}

registry
    .category("website-plugins")
    .add(ReferencesCarouselOptionPlugin.id, ReferencesCarouselOptionPlugin);

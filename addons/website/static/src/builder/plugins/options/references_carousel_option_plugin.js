import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { ReferencesCarouselHeaderMiddleButtons } from "./references_carousel_header_buttons";

const itemSelector = ".s_references_carousel_item";

export class ReferencesCarouselOptionPlugin extends Plugin {
    static id = "referencesCarouselOption";
    static dependencies = ["builderOptions"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_header_middle_buttons: {
            Component: ReferencesCarouselHeaderMiddleButtons,
            selector: itemSelector,
            props: {
                addItem: this.addItem.bind(this),
                removeItem: this.removeItem.bind(this),
            },
        },
        mark_color_level_selector_params: [{ selector: itemSelector }],
        dropzone_selectors: {
            selector: itemSelector,
            dropNear: itemSelector,
            // A reference only makes sense inside its own marquee.
            dropLockWithin: ".s_references_carousel",
        },
        is_movable_selectors: { selector: itemSelector, direction: "horizontal" },
        remove_disabled_reason_providers: (el) => {
            if (el.matches(`${itemSelector}:only-child`)) {
                return _t("You cannot remove the last item.");
            }
        },
    };

    addItem(itemEl) {
        const newItemEl = itemEl.cloneNode(true);
        itemEl.after(newItemEl);
        this.dependencies.builderOptions.setNextTarget(newItemEl);
    }

    removeItem(itemEl) {
        if (itemEl.matches(`${itemSelector}:only-child`)) {
            return;
        }
        const nextTargetEl = itemEl.previousElementSibling || itemEl.nextElementSibling;
        itemEl.remove();
        this.dependencies.builderOptions.setNextTarget(nextTargetEl);
    }
}

registry
    .category("website-plugins")
    .add(ReferencesCarouselOptionPlugin.id, ReferencesCarouselOptionPlugin);

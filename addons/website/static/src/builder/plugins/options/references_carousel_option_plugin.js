import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

const itemSelector = ".s_references_carousel_item";

/**
 * The logos scroll horizontally in edit mode: keep a new or moved reference in
 * view, or its selection overlay is drawn off-page.
 *
 * @param {HTMLElement} el
 */
function scrollIntoViewIfReference(el) {
    if (el.matches(itemSelector)) {
        el.scrollIntoView({ block: "nearest", inline: "nearest" });
    }
}

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
        is_valid_for_sibling_dropzone_predicates: (el) => {
            if (el.parentElement.matches(itemSelector)) {
                return false;
            }
        },
        // A logo is duplicated or removed with its reference: on its own, it
        // would share or empty a cell. `properties` also covers the keyboard.
        is_unremovable_selectors: `${itemSelector} img`,
        properties: { predicate: `${itemSelector} > *`, removable: "cascade" },
        // The logos share the editable container of the title: keep text out
        // of the strip, `o_editable_media` keeps the logos replaceable.
        content_not_editable_selectors: [".s_references_carousel_marquee_wrapper"],
        auto_unfold_container_providers: { selector: `${itemSelector} img`, target: itemSelector },
        // A logo is an image: "Logo Size" does not apply to icons, nor does a
        // strip of logos to videos or documents.
        replace_media_dialog_params_processors: (params) => {
            if (params.node?.nodeType === Node.ELEMENT_NODE && params.node.closest(itemSelector)) {
                params.visibleTabs = ["IMAGES"];
            }
            return params;
        },
        remove_disabled_reason_providers: (el) => {
            if (el.matches(`${itemSelector}:only-child`)) {
                return _t("You cannot remove the last item.");
            }
        },
        on_cloned_handlers: ({ cloneEl }) => scrollIntoViewIfReference(cloneEl),
        on_element_arrow_moved_handlers: ({ movedEl }) => scrollIntoViewIfReference(movedEl),
    };
}

registry
    .category("website-plugins")
    .add(ReferencesCarouselOptionPlugin.id, ReferencesCarouselOptionPlugin);

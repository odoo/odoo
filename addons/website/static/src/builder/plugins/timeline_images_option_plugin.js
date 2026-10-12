import { isElement } from "@html_editor/utils/dom_info";
import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class TimelineImagesOptionPlugin extends Plugin {
    static id = "timelineImagesOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        dropzone_selectors: {
            selector: ".s_timeline_images_row",
            dropNear: ".s_timeline_images_row",
        },
        is_movable_selectors: { selector: ".s_timeline_images_row", direction: "vertical" },
        remove_disabled_reason_providers: (el) => {
            if (
                el.matches(".s_timeline_images_row:only-child") ||
                el.matches(
                    ".s_timeline_images_row:only-child > .s_timeline_images_content > .row > div:only-child"
                )
            ) {
                return _t("You cannot remove the last item.");
            }
        },
        is_node_empty_predicates: (el) => {
            if (isElement(el) && el.matches(".s_timeline_images_row")) {
                return !el.querySelector(".s_timeline_images_content");
            }
        },
    };
}

registry.category("website-plugins").add(TimelineImagesOptionPlugin.id, TimelineImagesOptionPlugin);

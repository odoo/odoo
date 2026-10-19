import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class TimelineListOptionPlugin extends Plugin {
    static id = "timelineListOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        dropzone_selectors: {
            selector: ".s_timeline_list_row",
            dropNear: ".s_timeline_list_row",
        },
        is_movable_selectors: { selector: ".s_timeline_list_row", direction: "vertical" },
        remove_disabled_reason_providers: (el) => {
            if (el.matches(".s_timeline_list_row:only-child")) {
                return _t("You cannot remove the last item.");
            }
        },
    };
}

registry.category("website-plugins").add(TimelineListOptionPlugin.id, TimelineListOptionPlugin);

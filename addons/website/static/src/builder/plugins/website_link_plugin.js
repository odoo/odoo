import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

export class WebsiteLinkPlugin extends Plugin {
    static id = "websiteLinkPlugin";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        advanced_popover_options: [
            {
                id: "nofollow",
                label: "nofollow",
                description: _t("Tells search engines not to follow this link"),
                attribute: "rel",
                value: "nofollow",
                isMultiValueAttr: true,
            },
            {
                id: "noreferrer",
                label: "noreferrer",
                description: _t("Removes referrer information sent to the target site"),
                attribute: "rel",
                value: "noreferrer",
                isMultiValueAttr: true,
            },
            {
                id: "sponsored",
                label: "sponsored",
                description: _t("Indicates the link is sponsored or paid content"),
                attribute: "rel",
                value: "sponsored",
                isMultiValueAttr: true,
            },
            {
                id: "open_in_new_tab",
                label: "Open in new tab",
                description: _t("Opens the link in a new browser tab"),
                attribute: "target",
                value: "_blank",
            },
            {
                id: "noopener",
                label: "noopener",
                description: _t(
                    "Prevents the new page from accessing the original window (security)"
                ),
                attribute: "rel",
                value: "noopener",
                requires: "open_in_new_tab",
                isMultiValueAttr: true,
            },
        ],
    };
}

registry.category("website-plugins").add(WebsiteLinkPlugin.id, WebsiteLinkPlugin);
registry.category("translation-plugins").add(WebsiteLinkPlugin.id, WebsiteLinkPlugin);

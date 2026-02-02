import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { withSequence } from "@html_editor/utils/resource";
import { WebsiteLinkPopover } from "./website_link_popover/website_link_popover";

export class WebsiteLinkPlugin extends Plugin {
    static id = "websiteLinkPlugin";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        link_rel_attribute_options: [
            {
                label: "nofollow",
                description: _t("Tells search engines not to follow this link"),
            },
            {
                label: "noreferrer",
                description: _t("Removes referrer information sent to the target site"),
            },
            {
                label: "sponsored",
                description: _t("Indicaates the link is sponsored or paid content"),
            },
            {
                label: "noopener",
                description: _t(
                    "Prevents the new page from accessing the original window (security)"
                ),
            },
        ],
        link_popovers: [
            withSequence(20, {
                PopoverClass: WebsiteLinkPopover,
                isAvailable: () => true,
                getProps: (props) => props,
            }),
        ],
    };
}

registry.category("website-plugins").add(WebsiteLinkPlugin.id, WebsiteLinkPlugin);
registry.category("translation-plugins").add(WebsiteLinkPlugin.id, WebsiteLinkPlugin);

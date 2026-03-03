import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { MassMailingLinkPopover } from "../../components/mass_mailing_link_popover/mass_mailing_link_popover";
import { LinkPlugin } from "@html_editor/main/link/link_plugin";
import { _t } from "@web/core/l10n/translation";

export class MassMailingLinkPlugin extends LinkPlugin {
    resources = {
        ...this.resources,
        link_popovers: [
            withSequence(10, {
                PopoverClass: MassMailingLinkPopover,
                isAvailable: (linkEl) => !linkEl || !this.isLinkImmutable(linkEl),
                getProps: (props) => props,
            }),
        ],
        advanced_popover_options: [
            {
                id: "noreferrer",
                label: "noreferrer",
                description: _t("Removes referrer information sent to the target site"),
                attribute: "rel",
                value: "noreferrer",
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

    hasValidValue(attr, value) {
        if (attr == "data-no-tracking") {
            return true;
        }
        return super.hasValidValue(attr, value);
    }
}

registry.category("basic-editor-plugins").add(MassMailingLinkPlugin.id, MassMailingLinkPlugin);
registry.category("mass_mailing-plugins").add(MassMailingLinkPlugin.id, MassMailingLinkPlugin);

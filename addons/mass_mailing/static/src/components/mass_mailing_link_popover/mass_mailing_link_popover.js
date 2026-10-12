import { LinkPopover } from "@html_editor/main/link/link_popover";
import { _t } from "@web/core/l10n/translation";

/**
 * List of paths the URL of which will not have any effect when using the `notracking` option.
 *
 * @constant {string[]}
 */
const NON_TRACKABLE_URLS = ["/unsubscribe_from_list", "/view", "/cards"];

export class MassMailingLinkPopover extends LinkPopover {
    static template = "mass_mailing.MailingLinkPopover";

    setup() {
        super.setup();
        this.linkElement = this.props.linkElement;
        this.state.noTracking = {
            label: "Disable Link Tracking",
            description: _t("Send the original url instead of wrapping it into a tracking url."),
            isChecked: this.linkElement.dataset.noTracking !== undefined,
        };
    }

    toggleDisableLinkTracking() {
        if (this.state.noTracking.isChecked) {
            delete this.linkElement.dataset.noTracking;
        } else {
            this.linkElement.dataset.noTracking = "";
        }
        this.state.noTracking.isChecked = !this.state.noTracking.isChecked;
    }

    shouldDisplayNoTrackingOption() {
        return !NON_TRACKABLE_URLS.includes(this.state.url);
    }

    prepareLinkParams() {
        const params = super.prepareLinkParams();
        if (this.state.noTracking.isChecked) {
            params.attributes["data-no-tracking"] = "";
        }
        return params;
    }
}

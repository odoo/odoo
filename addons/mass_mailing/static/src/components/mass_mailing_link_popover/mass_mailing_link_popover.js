import { LinkPopover } from "@html_editor/main/link/link_popover";
import { _t } from "@web/core/l10n/translation";

/**
 * List of paths the URL of which will not have any effect when using the `notracking` option.
 *
 * @constant {string[]}
 */
export const NON_TRACKABLE_URLS = ["/unsubscribe_from_list", "/view", "/cards"];

export class MassMailingLinkPopover extends LinkPopover {
    static template = "mass_mailing.MailingLinkPopover";
    static props = {
        ...LinkPopover.props,
    };
    setup() {
        super.setup();
        this.linkElement = this.props.linkElement;
        this.notrackingStatus = this.linkElement.dataset.noTracking || "0";
        this.state.notracking = {
            label: "Disable Link Tracking",
            description: _t("Send the orignal url instead of wraping it into a tracking url"),
            isChecked: this.notrackingStatus == "1",
        };
    }

    toggleDisableLinkTracking() {
        this.notrackingStatus = this.notrackingStatus == "1" ? "0" : "1";
        this.state.notracking.isChecked = !this.state.notracking.isChecked;
    }

    shouldDisplayNoTrackingOption() {
        return !NON_TRACKABLE_URLS.includes(this.state.url);
    }

    onClickApply() {
        const relOptions = this.state.relAttributeOptions;
        const relValue = Object.keys(relOptions)
            .filter((key) => relOptions[key].isChecked)
            .join(" ");
        this.state.editing = false;
        this.applyDeducedUrl();
        this.props.onApply(
            this.state.url,
            this.state.label,
            this.classes,
            this.state.linkTarget,
            this.state.attachmentId,
            relValue,
            this.notrackingStatus
        );
    }
}

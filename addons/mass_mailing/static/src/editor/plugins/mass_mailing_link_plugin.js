import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { MassMailingLinkPopover } from "../../components/mass_mailing_link_popover/mass_mailing_link_popover";
import { LinkPlugin } from "@html_editor/main/link/link_plugin";

export class MassMailingLinkPlugin extends LinkPlugin {
    static id = "link";
    resources = {
        ...this.resources,
        link_popovers: [
            withSequence(10, {
                PopoverClass: MassMailingLinkPopover,
                isAvailable: (linkEl) => !linkEl || !this.isLinkImmutable(linkEl),
                getProps: (props) => props,
            }),
        ],
    };

    getProps(originalArgs) {
        const { linkElement, applyCallback } = originalArgs;
        const applyCallbackExtended = (...args) => {
            const [url, label, classes, linkTarget, attachmentId, relValue, notrackingVal] = args;
            applyCallback(url, label, classes, linkTarget, attachmentId, relValue);
            linkElement.setAttribute("data-no-tracking", notrackingVal);
        };
        return super.getProps({
            ...originalArgs,
            applyCallback: applyCallbackExtended,
        });
    }
}

registry.category("basic-editor-plugins").add(MassMailingLinkPlugin.id, MassMailingLinkPlugin);
registry.category("mass_mailing-plugins").add(MassMailingLinkPlugin.id, MassMailingLinkPlugin);

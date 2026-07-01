import { Component, t } from "@odoo/owl";
import { DiscussSidebarChannelActions } from "@mail/discuss/core/public_web/discuss_app/sidebar/channel_actions";
import { propComputed, useHover, UseHoverOverlay } from "@mail/utils/common/hooks";
import { useService } from "@web/core/utils/hooks";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { _t } from "@web/core/l10n/translation";
import { markEventHandled } from "@web/core/utils/misc";
import { Dropdown } from "@web/core/dropdown/dropdown";

export class DiscussSidebarSubchannel extends Component {
    static template = "mail.DiscussSidebarSubchannel";
    static components = { DiscussSidebarChannelActions, Dropdown, UseHoverOverlay };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.channel = propComputed("channel", t.instanceOf(this.store["discuss.channel"].Class));
        this.isFirst = propComputed("isFirst", t.boolean());
        this.hover = useHover(["root"], {
            onHover: () => {
                if (this.store.discuss.isSidebarCompact) {
                    this.floating.isOpen = true;
                }
            },
            onAway: () => {
                if (this.store.discuss.isSidebarCompact) {
                    this.floating.isOpen = false;
                }
            },
            stateObserver: () => [this.floating?.isOpen],
        });
        this.floating = useDropdownState();
        this.showingActions = useDropdownState();
    }

    get actionsTitle() {
        return _t("Thread Actions");
    }

    /**
     * @param {MouseEvent} ev
     * @param {Object} param1
     * @param {import("models").DiscussChannel} param1.channelAtRender
     */
    openChannel(ev, { channelAtRender }) {
        markEventHandled(ev, "sidebar.openChannel");
        channelAtRender.open();
    }
}

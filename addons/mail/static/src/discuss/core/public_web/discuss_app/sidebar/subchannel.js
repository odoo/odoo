import { Component } from "@odoo/owl";
import { DiscussSidebarChannelActions } from "@mail/discuss/core/public_web/discuss_app/sidebar/channel_actions";
import { useHover, UseHoverOverlay } from "@mail/utils/common/hooks";
import { useService } from "@web/core/utils/hooks";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { _t } from "@web/core/l10n/translation";
import { markEventHandled } from "@web/core/utils/misc";
import { Dropdown } from "@web/core/dropdown/dropdown";

export class DiscussSidebarSubchannel extends Component {
    static template = "mail.DiscussSidebarSubchannel";
    static props = ["thread", "isFirst?"];
    static components = { DiscussSidebarChannelActions, Dropdown, UseHoverOverlay };

    setup() {
        super.setup();
        this.store = useService("mail.store");
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

    get thread() {
        return this.props.thread;
    }

    /** @param {MouseEvent} ev */
    openThread(ev, thread) {
        markEventHandled(ev, "sidebar.openThread");
        thread.open();
    }
}

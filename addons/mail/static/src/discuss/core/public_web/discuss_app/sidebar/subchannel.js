import { Component, useRef } from "@odoo/owl";
import { ThreadPreview } from "@mail/core/common/thread_preview";
import { DiscussSidebarChannelActions } from "@mail/discuss/core/public_web/discuss_app/sidebar/channel_actions";
import { useHover, UseHoverOverlay } from "@mail/utils/common/hooks";
import { useChildRef, useService } from "@web/core/utils/hooks";
import { usePopover } from "@web/core/popover/popover_hook";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { _t } from "@web/core/l10n/translation";
import { markEventHandled } from "@web/core/utils/misc";
import { Dropdown } from "@web/core/dropdown/dropdown";

export class DiscussSidebarSubchannel extends Component {
    static template = "mail.DiscussSidebarSubchannel";
    static props = ["channel", "isFirst?"];
    static components = { DiscussSidebarChannelActions, Dropdown, UseHoverOverlay };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.rootRef = useRef("root");
        const popoverRef = useChildRef();
        this.popover = usePopover(ThreadPreview, {
            animation: false,
            position: "right-middle",
            popoverClass:
                "dropdown-menu bg-view border-0 p-0 overflow-visible o-rounded-bubble mx-1",
            ref: popoverRef,
        });
        this.env.bus.addEventListener("DiscussSidebar:preview-will-open", ({ detail }) => {
            if (detail === this) {
                return;
            }
            this.popover.close();
        });
        this.hover = useHover(["root", popoverRef], {
            onHover: () => {
                if (this.showingActions?.isOpen) {
                    this.popover.close();
                    return;
                }
                if (this.store.discuss.isSidebarCompact) {
                    this.floating.isOpen = true;
                    return;
                }
                this.env.bus.trigger("DiscussSidebar:preview-will-open", this);
                this.popover.open(this.rootRef.el, { channel: this.channel });
            },
            onAway: () => {
                if (this.store.discuss.isSidebarCompact) {
                    this.floating.isOpen = false;
                    return;
                }
                this.popover.close();
            },
            stateObserver: () => [this.floating?.isOpen, this.showingActions?.isOpen],
        });
        this.floating = useDropdownState();
        this.showingActions = useDropdownState();
    }

    get actionsTitle() {
        return _t("Thread Actions");
    }

    get channel() {
        return this.props.channel;
    }

    /** @param {MouseEvent} ev */
    openChannel(ev, channel) {
        markEventHandled(ev, "sidebar.openChannel");
        channel.open();
    }
}

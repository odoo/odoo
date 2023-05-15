/* @odoo-module */

import { CallSettings } from "@mail/discuss/core/call_settings";
import { ChannelInvitation } from "@mail/discuss/core/channel_invitation";
import { ChannelMemberList } from "@mail/discuss/core/channel_member_list";
import { Discuss } from "@mail/discuss_app/discuss";
import { createLocalId } from "@mail/utils/misc";
import { useRef, useState } from "@odoo/owl";
import { usePopover } from "@web/core/popover/popover_hook";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(Discuss, "discuss", {
    components: { ...Discuss.components, CallSettings, ChannelMemberList },
});

patch(Discuss.prototype, "discuss", {
    setup() {
        this._super();
        this.addUsersRef = useRef("addUsers");
        this.popover = usePopover(ChannelInvitation, {
            onClose: () => (this.state.isAddingUsers = false),
        });
        this.state.isAddingUsers = false;
        this.discussStore = useState(useService("discuss.store"));
    },
    toggleInviteForm() {
        if (this.popover.isOpen) {
            this.popover.close();
        } else {
            this.state.isAddingUsers = true;
            this.popover.open(this.addUsersRef.el, {
                hasSizeConstraints: true,
                thread: this.thread,
            });
        }
    },
    toggleMemberList() {
        this.state.activeMode =
            this.state.activeMode === this.MODES.MEMBER_LIST
                ? this.MODES.NONE
                : this.MODES.MEMBER_LIST;
    },
    toggleSettings() {
        this.state.activeMode =
            this.state.activeMode === this.MODES.SETTINGS ? this.MODES.NONE : this.MODES.SETTINGS;
    },
    getChannel() {
        return this.discussStore.channels[createLocalId("discuss.channel", this.thread?.id)];
    },
});

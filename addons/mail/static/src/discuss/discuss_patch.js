/* @odoo-module */

import { ChannelInvitation } from "@mail/discuss/channel_invitation";
import { Discuss } from "@mail/discuss_app/discuss";
import { useRef } from "@odoo/owl";
import { usePopover } from "@web/core/popover/popover_hook";
import { patch } from "@web/core/utils/patch";

patch(Discuss.prototype, "discuss", {
    setup() {
        this._super();
        this.addUsersRef = useRef("addUsers");
        this.popover = usePopover(ChannelInvitation, {
            onClose: () => (this.state.isAddingUsers = false),
        });
        this.state.isAddingUsers = false;
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
});

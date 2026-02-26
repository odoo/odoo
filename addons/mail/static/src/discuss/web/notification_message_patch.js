import { patch } from "@web/core/utils/patch";
import { NotificationMessage } from "@mail/core/common/notification_message";
import { usePopover } from "@web/core/popover/popover_hook";
import { useState } from "@odoo/owl";
import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";

patch(NotificationMessage.prototype, {
    setup() {
        super.setup(...arguments);
        this.avatarCard = usePopover(AvatarCardPopover, {
            arrow: false,
            onClose: () => (this.state.isAvatarCardOpen = false),
            popoverClass: "mx-2",
        });
        this.state = useState({
            isAvatarCardOpen: false,
        });
    },

    _handleClickOnLink(ev) {
        const model = ev.target.dataset.oeModel;
        const id = Number(ev.target.dataset.oeId);
        if (ev.target.tagName === "A" && model === "res.partner" && id) {
            if (!this.avatarCard.isOpen) {
                this.avatarCard.open(ev.currentTarget, {
                    id,
                    model,
                });
                this.state.isAvatarCardOpen = true;
            }
            return;
        }
        super._handleClickOnLink(ev);
    }
});

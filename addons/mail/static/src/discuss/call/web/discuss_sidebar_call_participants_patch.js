// @ts-check
/** @odoo-module native */
import { DiscussSidebarCallParticipants } from "@mail/discuss/call/public_web/discuss_sidebar_call_participants";
import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";
import { patch } from "@web/core/utils/patch";
import { usePopover } from "@web/ui/popover";
patch(DiscussSidebarCallParticipants.prototype, {
    setup() {
        super.setup();
        this.avatarCard = usePopover(AvatarCardPopover, {
            position: "right",
        });
    },
    /** @param {import("models").RtcSession} session */
    participantClass(session) {
        return {
            ...super.participantClass(session),
            "o-active cursor-pointer rounded-4": session.persona?.main_user_id,
        };
    },
    /**
     * @param {MouseEvent} ev
     * @param {import("models").RtcSession} session
     */
    onClickParticipant(ev, session) {
        if (!session.partner_id?.main_user_id) {
            return;
        }
        if (!this.avatarCard.isOpen) {
            this.avatarCard.open(ev.currentTarget, {
                id: session.partner_id.main_user_id.id,
            });
        }
    },
});
Object.assign(DiscussSidebarCallParticipants.components, { AvatarCardPopover });

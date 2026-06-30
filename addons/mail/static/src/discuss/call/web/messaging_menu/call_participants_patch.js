import { MessagingMenuCallParticipants } from "@mail/discuss/call/public_web/messaging_menu/call_participants";
import { AvatarCard } from "@mail/core/web/avatar_card/avatar_card";

import { usePopover } from "@web/core/popover/popover_hook";
import { patch } from "@web/core/utils/patch";

patch(MessagingMenuCallParticipants.prototype, {
    setup() {
        super.setup();
        this.avatarCard = usePopover(AvatarCard, { position: "right" });
    },
    /** @param {import("models").RtcSession} session */
    participantClass(session) {
        return {
            ...super.participantClass(session),
            "o-active cursor-pointer rounded-4": Boolean(session.persona?.main_user_id),
        };
    },
    /**
     * @param {MouseEvent} ev
     * @param {import("models").RtcSession} session
     */
    onClickParticipant(ev, session) {
        if (!session.persona?.main_user_id) {
            return;
        }
        if (!this.avatarCard.isOpen) {
            this.avatarCard.open(ev.currentTarget, {
                id: session.persona.main_user_id.id,
                model: "res.users",
            });
        }
    },
});
Object.assign(MessagingMenuCallParticipants.components, { AvatarCard });

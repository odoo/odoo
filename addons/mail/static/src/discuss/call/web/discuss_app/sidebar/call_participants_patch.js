import { DiscussSidebarCallParticipants } from "@mail/discuss/call/public_web/discuss_app/sidebar/call_participants";
import { AvatarCard } from "@mail/core/web/avatar_card/avatar_card";

import { usePopover } from "@web/core/popover/popover_hook";
import { patch } from "@web/core/utils/patch";

patch(DiscussSidebarCallParticipants.prototype, {
    setup() {
        super.setup();
        this.avatarCard = usePopover(AvatarCard, { position: "right" });
    },
    attClass(session) {
        return {
            ...super.attClass,
            "o-active cursor-pointer rounded-4": session.persona?.main_user_id,
        };
    },
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
Object.assign(DiscussSidebarCallParticipants.components, { AvatarCard });

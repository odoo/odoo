import { DiscussSidebarCallParticipants } from "@mail/discuss/call/public_web/discuss_app/sidebar/call_participants";
import { useAvatarCard } from "@mail/core/web/avatar_card/avatar_card";

import { patch } from "@web/core/utils/patch";

patch(DiscussSidebarCallParticipants.prototype, {
    setup() {
        super.setup();
        this.avatarCard = useAvatarCard({
            model: "res.users",
            popoverOptions: { position: "right" },
        });
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
        this.avatarCard.open(ev, session.persona.main_user_id);
    },
});

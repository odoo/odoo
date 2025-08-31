import { DiscussSidebarCallParticipants } from "@mail/discuss/call/public_web/discuss_sidebar_call_participants";
import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";

import { usePopover } from "@web/core/popover/popover_hook";
import { patch } from "@web/core/utils/patch";

patch(DiscussSidebarCallParticipants.prototype, {
    setup() {
        super.setup();
        this.avatarCard = usePopover(AvatarCardPopover, {
            position: "right",
        });
    },
    get attClass() {
        return {
            ...super.attClass,
            "o-active cursor-pointer rounded-4": this.session.persona.main_user_id,
        };
    },
    onClickParticipant(ev, session) {
        if (!session.persona.main_user_id) {
            return;
        }
        if (!this.avatarCard.isOpen) {
            this.avatarCard.open(ev.currentTarget, {
                id: session.persona.main_user_id.id,
            });
        }
    },
});
Object.assign(DiscussSidebarCallParticipants.components, { AvatarCardPopover });

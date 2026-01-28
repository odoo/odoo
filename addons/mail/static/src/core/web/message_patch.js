import { Message } from "@mail/core/common/message";
import { markEventHandled } from "@web/core/utils/misc";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { usePopover } from "@web/core/popover/popover_hook";
import { patch } from "@web/core/utils/patch";
import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";

patch(Message.prototype, {
    setup() {
        super.setup(...arguments);
        this.action = useService("action");
        this.avatarCard = usePopover(AvatarCardPopover);
    },
    get attClass() {
        return {
            ...super.attClass,
            "o-needaction-message o-rounded-bubble bg-view shadow-sm border pb-1 pt-sm-2":
                this.message.needaction && this.env.inChatter,
        };
    },
    get authorAvatarAttClass() {
        return {
            ...super.authorAvatarAttClass,
            "o_redirect cursor-pointer": this.hasAuthorClickable(),
        };
    },
    getAuthorAttClass() {
        return {
            ...super.getAuthorAttClass(),
            "cursor-pointer o-hover-text-underline": this.hasAuthorClickable(),
        };
    },
    getAuthorText() {
        return this.hasAuthorClickable() ? _t("Open card") : undefined;
    },
    getAvatarContainerAttClass() {
        return {
            ...super.getAvatarContainerAttClass(),
            "cursor-pointer": this.hasAuthorClickable(),
        };
    },
    hasAuthorClickable() {
        return this.message.author_id?.main_user_id;
    },
    onClickAuthor(ev) {
        if (this.hasAuthorClickable()) {
            markEventHandled(ev, "Message.ClickAuthor");
            const target = ev.currentTarget;
            if (!this.avatarCard.isOpen) {
                this.avatarCard.open(target, {
                    id: this.message.author_id.main_user_id.id,
                });
            }
        }
    },

    openRecord() {
        this.message.thread.open({ focus: true });
        this.message.thread.highlightMessage = this.message;
    },
});

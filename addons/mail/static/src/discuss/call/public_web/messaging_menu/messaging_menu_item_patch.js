import { MessagingMenuItem } from "@mail/core/public_web/messaging_menu/messaging_menu_item";
import { AvatarStack } from "@mail/discuss/core/common/avatar_stack";

import { computed } from "@odoo/owl";

import { patch } from "@web/core/utils/patch";

Object.assign(MessagingMenuItem.components, { AvatarStack });

patch(MessagingMenuItem.prototype, {
    setup() {
        super.setup(...arguments);
        this.callParticipants = computed(() =>
            (this.channel()?.rtc_session_ids ?? [])
                .map((session) => session.channel_member_id?.persona)
                .filter((persona) => persona)
        );
    },
});

/* @odoo-module */

import { ThreadService } from "@mail/core/common/thread_service";

import { patch } from "@web/core/utils/patch";
import { url } from "@web/core/utils/urls";

patch(ThreadService.prototype, {
    avatarUrl(persona, thread) {
        if (thread?.model === "discuss.channel" && persona.notEq(thread.operator)) {
            const route =
                persona.type === "partner"
                    ? `/im_livechat/cors/channel/${thread.id}/partner/${persona.id}/avatar_128`
                    : `/im_livechat/cors/channel/${thread.id}/guest/${persona.id}/avatar_128`;
            return url(route, {
                guest_token: this.env.services["im_livechat.livechat"].guestToken,
            });
        }
        return super.avatarUrl(...arguments);
    },
});

import { fields } from "@mail/model/export";
import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";
import { url } from "@web/core/utils/urls";

patch(Thread.prototype, {
    setup() {
        super.setup();
        this.livechat_end_dt = fields.Datetime();
        this.livechatVisitorMember = fields.One("discuss.channel.member", {
            compute() {
                if (this.channel?.channel_type !== "livechat") {
                    return;
                }
                return [...this.channel.channel_member_ids]
                    .sort((a, b) => a.id - b.id)
                    .find((member) => member.livechat_member_type === "visitor");
            },
        });
    },
    get composerHidden() {
        return this.channel?.channel_type === "livechat" && this.livechat_end_dt;
    },

    get transcriptUrl() {
        return url(`/im_livechat/download_transcript/${this.id}`);
    },

    /**
     * @override
     * @param {import("models").Persona} persona
     */
    getPersonaName(persona) {
        if (this.channel?.channel_type === "livechat" && persona?.user_livechat_username) {
            return persona.user_livechat_username;
        }
        return super.getPersonaName(persona);
    },
});

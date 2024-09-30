import { fields } from "@mail/model/export";
import { Thread } from "@mail/core/common/thread_model";
import { convertBrToLineBreak } from "@mail/utils/common/format";

import { patch } from "@web/core/utils/patch";
import { url } from "@web/core/utils/urls";

patch(Thread.prototype, {
    setup() {
        super.setup();
        this.country_id = fields.One("res.country");
        this.livechat_end_dt = fields.Datetime();
        this.livechat_note = fields.Html();
        /** @type {string|undefined} */
        this.livechatNoteText = fields.Attr(undefined, {
            compute() {
                if (this.livechat_note !== undefined) {
                    return convertBrToLineBreak(this.livechat_note || "");
                }
                return this.livechatNoteText;
            },
        });
        /** @type {"no_answer"|"no_agent"|"no_failure"|"escalated"|undefined} */
        this.livechat_outcome = undefined;
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

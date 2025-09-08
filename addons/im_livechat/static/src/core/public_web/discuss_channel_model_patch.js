import { DiscussChannel } from "@mail/discuss/core/common/discuss_channel_model";

import { patch } from "@web/core/utils/patch";

patch(DiscussChannel.prototype, {
    get correspondents() {
        if (!super.correspondents) {
            return [];
        }
        return super.correspondents.filter(
            (correspondent) => correspondent.livechat_member_type !== "bot"
        );
    },
    computeCorrespondent() {
        const correspondent = super.computeCorrespondent();
        if (this.channel_type === "livechat" && !correspondent) {
            return this.thread.livechatVisitorMember;
        }
        return correspondent;
    },
    get showCorrespondentCountry() {
        if (this.channel_type === "livechat") {
            return (
                this.livechat_operator_id?.eq(this.store.self) && Boolean(this.correspondentCountry)
            );
        }
        return super.showCorrespondentCountry;
    },
});

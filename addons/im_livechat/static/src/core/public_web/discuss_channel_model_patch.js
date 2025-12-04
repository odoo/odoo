import { DiscussChannel } from "@mail/discuss/core/common/discuss_channel_model";
import { fields } from "@mail/model/misc";

import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";

const discussChannelPatch = {
    setup() {
        super.setup(...arguments);
        this.appAsLivechats = fields.One("DiscussApp", {
            compute() {
                return this.channel_type === "livechat" ? this.store.discuss : null;
            },
        });
        this.livechat_expertise_ids = fields.Many("im_livechat.expertise");
        /** @type {"in_progress"|"waiting"|"need_help"|undefined} */
        this.livechat_status = fields.Attr(undefined, {
            onUpdate() {
                if (this.livechat_status === "need_help") {
                    this.wasLookingForHelp = true;
                    this.unpinOnThreadSwitch = false;
                    return;
                }
                if (this.wasLookingForHelp) {
                    this.wasLookingForHelp = false;
                    // Still the active thread; keep it pinned after leaving "need help" status.
                    // The agent may interact with the thread, keeping it pinned, or it will be
                    // unpinned on the next thread switch to avoid bloating the sidebar.
                    this.unpinOnThreadSwitch = this.eq(this.store.discuss?.thread?.channel);
                }
            },
        });
        this.shadowedBySelf = 0;
        this.unpinOnThreadSwitch = false;
    },
    _computeIsDisplayInSidebar() {
        return this.livechat_status === "need_help" || super._computeIsDisplayInSidebar();
    },
    get canLeave() {
        return (
            super.canLeave &&
            (!this.store.discuss.livechatLookingForHelpCategory ||
                this.store.discuss.livechatLookingForHelpCategory.notEq(this.discussAppCategory) ||
                this.self_member_id)
        );
    },
    get livechatStatusLabel() {
        if (this.livechat_end_dt) {
            return _t("Conversation has ended");
        }
        const status = this.livechat_status;
        if (status === "waiting") {
            return _t("Waiting for customer");
        } else if (status === "need_help") {
            return _t("Looking for help");
        }
        return _t("In progress");
    },
    get matchesSelfExpertise() {
        return (
            this.store.self_user &&
            this.livechat_expertise_ids.some((expertise) =>
                expertise.in(this.store.self_user.livechat_expertise_ids)
            )
        );
    },
    get shouldSubscribeToBusChannel() {
        return super.shouldSubscribeToBusChannel || Boolean(this.shadowedBySelf);
    },
    /** @param {"in_progress"|"waiting"|"need_help"} status */
    updateLivechatStatus(status) {
        if (this.livechat_status === status) {
            return;
        }
        rpc("/im_livechat/session/update_status", { channel_id: this.id, livechat_status: status });
    },
    get allowedToLeaveChannelTypes() {
        return [...super.allowedToLeaveChannelTypes, "livechat"];
    },
};
patch(DiscussChannel.prototype, discussChannelPatch);

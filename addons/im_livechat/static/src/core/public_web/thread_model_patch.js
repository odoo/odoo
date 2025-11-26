import { fields } from "@mail/model/export";
import { Thread } from "@mail/core/common/thread_model";
import { _t } from "@web/core/l10n/translation";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    setup() {
        super.setup(...arguments);
        this.country_id = fields.One("res.country");
<<<<<<< 0e855a58c53a56387a17464a3ccd5d0c827791fe
||||||| 952add278ea4debb6215ca8363f446df84b9f9bc
        this.livechat_channel_id = fields.One("im_livechat.channel", { inverse: "threads" });
        this.livechat_expertise_ids = fields.Many("im_livechat.expertise");
        let wasLookingForHelp = false;
        /** @type {"in_progress"|"waiting"|"need_help"|undefined} */
        this.livechat_status = fields.Attr(undefined, {
            onUpdate() {
                if (this.livechat_status === "need_help") {
                    wasLookingForHelp = true;
                    this.unpinOnThreadSwitch = false;
                    return;
                }
                if (wasLookingForHelp) {
                    wasLookingForHelp = false;
                    // Still the active thread; keep it pinned after leaving "need help" status.
                    // The agent may interact with the thread, keeping it pinned, or it will be
                    // unpinned on the next thread switch to avoid bloating the sidebar.
                    this.unpinOnThreadSwitch = this.eq(this.store.discuss?.thread);
                }
            },
        });
        this.shadowedBySelf = 0;
    },
    get canLeave() {
        const lookingForHelpCategory = this.store.discuss.livechatLookingForHelpCategory;
        return (
            super.canLeave &&
            (!lookingForHelpCategory ||
                lookingForHelpCategory.notEq(this.discussAppCategory) ||
                this.self_member_id)
        );
=======
        this.livechat_channel_id = fields.One("im_livechat.channel", { inverse: "threads" });
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
                    this.unpinOnThreadSwitch = this.eq(this.store.discuss?.thread);
                }
            },
        });
        this.shadowedBySelf = 0;
    },
    get canLeave() {
        const lookingForHelpCategory = this.store.discuss.livechatLookingForHelpCategory;
        return (
            super.canLeave &&
            (!lookingForHelpCategory ||
                lookingForHelpCategory.notEq(this.discussAppCategory) ||
                this.self_member_id)
        );
>>>>>>> 0250bf52126d554ede7eadbd85df84379563f9b6
    },
    _computeDiscussAppCategory() {
        if (this.channel?.channel_type !== "livechat") {
            return super._computeDiscussAppCategory();
        }
        return (
            this.channel.livechat_channel_id?.appCategory ??
            this.channel.appAsLivechats?.defaultLivechatCategory
        );
    },
    get allowedToLeaveChannelTypes() {
        return [...super.allowedToLeaveChannelTypes, "livechat"];
    },
    get correspondents() {
        return super.correspondents.filter(
            (correspondent) => correspondent.livechat_member_type !== "bot"
        );
    },

    computeCorrespondent() {
        const correspondent = super.computeCorrespondent();
        if (this.channel?.channel_type === "livechat" && !correspondent) {
            return this.livechatVisitorMember;
        }
        return correspondent;
    },

    get inChathubOnNewMessage() {
        return this.channel?.channel_type === "livechat" || super.inChathubOnNewMessage;
    },

    /**
     * @override
     * @param {boolean} pushState
     */
    setAsDiscussThread(pushState) {
        super.setAsDiscussThread(pushState);
        if (this.store.env.services.ui.isSmall && this.channel?.channel_type === "livechat") {
            this.store.discuss.activeTab = "livechat";
        }
    },
    async leaveChannel() {
        if (
            this.channel?.channel_type === "livechat" &&
            this.channel?.channel_member_ids.length <= 2 &&
            !this.livechat_end_dt
        ) {
            await this.askLeaveConfirmation(
                _t("Leaving will end the live chat. Do you want to proceed?")
            );
        }
        super.leaveChannel(...arguments);
    },
});

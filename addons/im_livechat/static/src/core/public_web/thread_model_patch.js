import { fields } from "@mail/model/export";
import { Thread } from "@mail/core/common/thread_model";
import { _t } from "@web/core/l10n/translation";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    setup() {
        super.setup(...arguments);
        this.country_id = fields.One("res.country");
<<<<<<< 74f09c9148b80fbd5202582ef90a0ced629afd03
||||||| 2217d5220640531828eb5b2ae7a9d41ba9c97e78
        this.livechat_channel_id = fields.One("im_livechat.channel", { inverse: "threads" });
        this.livechat_expertise_ids = fields.Many("im_livechat.expertise");
        /** @type {"in_progress"|"waiting"|"need_help"|undefined} */
        this.livechat_status = fields.Attr(undefined, {
            onUpdate() {
                if (this.livechat_status === "need_help") {
                    this.isLocallyPinned = true;
                    this.wasLookingForHelp = true;
                    this.unpinOnThreadSwitch = false;
                    return;
                }
                if (this.wasLookingForHelp) {
                    this.isLocallyPinned = this.eq(this.store.discuss?.thread);
                    // Still the active thread; keep it pinned after leaving "need help" status.
                    // The agent may interact with the thread, keeping it pinned, or it will be
                    // unpinned on the next thread switch to avoid bloating the sidebar.
                    this.unpinOnThreadSwitch = this.isLocallyPinned;
                    this.wasLookingForHelp = false;
                }
            },
        });
        this.shadowedBySelf = 0;
        this.wasLookingForHelp = false;
    },
    get canLeave() {
        return (
            super.canLeave &&
            (this.store.discuss.livechatLookingForHelpCategory.notEq(this.discussAppCategory) ||
                this.self_member_id)
        );
=======
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
>>>>>>> 4f65087f28f2ed781c78a11b2fb8c4e68d62a379
    },
    _computeDiscussAppCategory() {
        if (this.channel?.channel_type !== "livechat") {
            return super._computeDiscussAppCategory();
        }
<<<<<<< 74f09c9148b80fbd5202582ef90a0ced629afd03
||||||| 2217d5220640531828eb5b2ae7a9d41ba9c97e78
        if (this.livechat_status === "need_help" && this.store.has_access_livechat) {
            return this.store.discuss.livechatLookingForHelpCategory;
        }
=======
        if (
            this.livechat_status === "need_help" &&
            this.store.discuss.livechatLookingForHelpCategory
        ) {
            return this.store.discuss.livechatLookingForHelpCategory;
        }
>>>>>>> 4f65087f28f2ed781c78a11b2fb8c4e68d62a379
        return (
            this.channel.livechat_channel_id?.appCategory ??
            this.channel.appAsLivechats?.defaultLivechatCategory
        );
    },
    get hasMemberList() {
        return this.channel?.channel_type === "livechat" || super.hasMemberList;
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

<<<<<<< 74f09c9148b80fbd5202582ef90a0ced629afd03
||||||| 2217d5220640531828eb5b2ae7a9d41ba9c97e78
    get displayName() {
        if (
            this.channel_type !== "livechat" ||
            !this.correspondent ||
            this.self_member_id?.custom_channel_name
        ) {
            return super.displayName;
        }
        if (!this.correspondent.persona.is_public && this.correspondent.persona.country) {
            return `${this.correspondent.name} (${this.correspondent.persona.country.name})`;
        }
        if (this.country_id) {
            return `${this.correspondent.name} (${this.country_id.name})`;
        }
        return this.correspondent.name;
    },

    get avatarUrl() {
        if (this.channel_type === "livechat" && this.correspondent) {
            return this.correspondent.avatarUrl;
        }
        return super.avatarUrl;
    },

=======
    _computeDisplayInSidebar() {
        return this.livechat_status === "need_help" || super._computeDisplayInSidebar();
    },

    get displayName() {
        if (
            this.channel_type !== "livechat" ||
            !this.correspondent ||
            this.self_member_id?.custom_channel_name
        ) {
            return super.displayName;
        }
        if (!this.correspondent.persona.is_public && this.correspondent.persona.country) {
            return `${this.correspondent.name} (${this.correspondent.persona.country.name})`;
        }
        if (this.country_id) {
            return `${this.correspondent.name} (${this.country_id.name})`;
        }
        return this.correspondent.name;
    },

    get avatarUrl() {
        if (this.channel_type === "livechat" && this.correspondent) {
            return this.correspondent.avatarUrl;
        }
        return super.avatarUrl;
    },

>>>>>>> 4f65087f28f2ed781c78a11b2fb8c4e68d62a379
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

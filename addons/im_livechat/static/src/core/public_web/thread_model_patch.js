import { fields } from "@mail/model/export";
import { Thread } from "@mail/core/common/thread_model";
import { _t } from "@web/core/l10n/translation";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    setup() {
        super.setup(...arguments);
        this.country_id = fields.One("res.country");
<<<<<<< db80e85e2b89b55dd78ab180ba14663d817c3f4b
||||||| c758b93a57cd98ab76c26c03bd0097f2eef50961
        this.livechat_channel_id = fields.One("im_livechat.channel", { inverse: "threads" });
        this.livechat_expertise_ids = fields.Many("im_livechat.expertise");
        this.wasLookingForHelp = false;
        /** @type {"in_progress"|"waiting"|"need_help"|undefined} */
        this.livechat_status = fields.Attr(undefined, {
            onUpdate() {
                if (this.livechat_status === "need_help") {
                    this.isLocallyPinned = true;
                    this.wasLookingForHelp = true;
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
        this.shadowedBySelf = false;
        this.wasLookingForHelp = false;
    },
    get canLeave() {
        return (
            super.canLeave &&
            (this.store.discuss.livechatLookingForHelpCategory.notEq(this.discussAppCategory) ||
                this.self_member_id)
        );
>>>>>>> b7f3f178138da3d91ff14f5acaf5724c51932ca9
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

    get displayName() {
        if (
            this.channel?.channel_type !== "livechat" ||
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

    get inChathubOnNewMessage() {
        return this.channel?.channel_type === "livechat" || super.inChathubOnNewMessage;
    },

<<<<<<< db80e85e2b89b55dd78ab180ba14663d817c3f4b
||||||| c758b93a57cd98ab76c26c03bd0097f2eef50961
    get inChathubOnNewMessage() {
        return this.channel_type === "livechat" || super.inChathubOnNewMessage;
    },
    get matchesSelfExpertise() {
        return (
            this.store.self_partner?.main_user_id &&
            this.livechat_expertise_ids.some((expertise) =>
                expertise.in(this.store.self_partner.main_user_id.livechat_expertise_ids)
            )
        );
    },
=======
    get inChathubOnNewMessage() {
        if (this.channel_type === "livechat") {
            return Boolean(this.self_member_id);
        }
        return super.inChathubOnNewMessage;
    },
    get notifyWhenOutOfFocus() {
        if (this.channel_type === "livechat") {
            return (
                this.self_member_id || this.shadowedBySelf || this.eq(this.store.discuss?.thread)
            );
        }
        return super.notifyWhenOutOfFocus;
    },
    get matchesSelfExpertise() {
        return (
            this.store.self_partner?.main_user_id &&
            this.livechat_expertise_ids.some((expertise) =>
                expertise.in(this.store.self_partner.main_user_id.livechat_expertise_ids)
            )
        );
    },
>>>>>>> b7f3f178138da3d91ff14f5acaf5724c51932ca9
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

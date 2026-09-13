/** @odoo-module native */
import { fields } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";
import { _t } from "@web/core/translation";
import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    setup() {
        super.setup(...arguments);
        this.appAsLivechats = fields.One("DiscussApp", {
            compute() {
                return this.isLivechat ? this.store.discuss : null;
            },
        });
        this.country_id = fields.One("res.country");
        this.livechat_channel_id = fields.One("im_livechat.channel", {
            inverse: "threads",
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
                    this.unpinOnThreadSwitch = this.eq(this.store.discuss?.thread);
                }
            },
        });
        this.shadowedBySelf = 0;
    },
    get canLeave() {
        const lookingForHelpCategory =
            this.store.discuss.livechatLookingForHelpCategory;
        return (
            super.canLeave &&
            (!lookingForHelpCategory ||
                lookingForHelpCategory.notEq(this.discussAppCategory) ||
                this.self_member_id)
        );
    },
    _computeDiscussAppCategory() {
        if (!this.isLivechat) {
            return super._computeDiscussAppCategory();
        }
        if (
            this.livechat_status === "need_help" &&
            this.store.discuss.livechatLookingForHelpCategory
        ) {
            return this.store.discuss.livechatLookingForHelpCategory;
        }
        return (
            this.livechat_channel_id?.appCategory ??
            this.appAsLivechats?.defaultLivechatCategory
        );
    },
    get hasMemberList() {
        return this.isLivechat || super.hasMemberList;
    },
    get allowedToLeaveChannelTypes() {
        return [...super.allowedToLeaveChannelTypes, "livechat"];
    },
    get correspondents() {
        return super.correspondents.filter(
            (correspondent) => correspondent.livechat_member_type !== "bot",
        );
    },

    computeCorrespondent() {
        const correspondent = super.computeCorrespondent();
        if (this.isLivechat && !correspondent) {
            return this.livechatVisitorMember;
        }
        return correspondent;
    },

    _computeDisplayInSidebar() {
        return this.livechat_status === "need_help" || super._computeDisplayInSidebar();
    },

    get displayName() {
        if (
            !this.isLivechat ||
            !this.correspondent ||
            this.self_member_id?.custom_channel_name
        ) {
            return super.displayName;
        }
        if (
            !this.correspondent.persona.is_public &&
            this.correspondent.persona.country
        ) {
            return `${this.correspondent.name} (${this.correspondent.persona.country.name})`;
        }
        if (this.country_id) {
            return `${this.correspondent.name} (${this.country_id.name})`;
        }
        return this.correspondent.name;
    },

    get avatarUrl() {
        if (this.isLivechat && this.correspondent) {
            return this.correspondent.avatarUrl;
        }
        return super.avatarUrl;
    },

    get inChathubOnNewMessage() {
        if (this.isLivechat) {
            return Boolean(this.self_member_id);
        }
        return super.inChathubOnNewMessage;
    },
    get notifyWhenOutOfFocus() {
        if (this.isLivechat) {
            return (
                this.self_member_id ||
                this.shadowedBySelf ||
                this.eq(this.store.discuss?.thread)
            );
        }
        return super.notifyWhenOutOfFocus;
    },
    get matchesSelfExpertise() {
        return (
            this.store.selfUser &&
            this.livechat_expertise_ids.some((expertise) =>
                expertise.in(
                    this.store.self_partner.main_user_id.livechat_expertise_ids,
                ),
            )
        );
    },
    /**
     * @override
     * @param {boolean} pushState
     */
    setAsDiscussThread(pushState) {
        super.setAsDiscussThread(pushState);
        if (this.store.env.services.ui.isSmall && this.isLivechat) {
            this.store.discuss.activeTab = "livechat";
        }
    },
    get shouldSubscribeToBusChannel() {
        return super.shouldSubscribeToBusChannel || Boolean(this.shadowedBySelf);
    },
    async leaveChannel({ force = false } = {}) {
        if (
            this.isLivechat &&
            this.channel_member_ids.length <= 2 &&
            this.self_member_id &&
            !this.livechat_end_dt &&
            !force
        ) {
            const confirmed = await this.askLeaveConfirmation(
                _t("Leaving will end the live chat. Do you want to proceed?"),
            );
            if (!confirmed) {
                return false;
            }
        }
        return super.leaveChannel(...arguments);
    },
});

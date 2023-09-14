/* @odoo-module */

import { Chatter } from "@mail/chatter/web_portal/chatter";
import { Activity } from "@mail/core/web/activity";
import { SuggestedRecipientsList } from "@mail/core/web/suggested_recipient_list";
import { RecipientList } from "@mail/core/web/recipient_list";
import { FollowerList } from "@mail/core/web/follower_list";

import { patch } from "@web/core/utils/patch";
import { useState, markup } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { usePopover } from "@web/core/popover/popover_hook";
import { escapeHTML } from "@web/core/utils/strings";
import { useHover } from "@mail/utils/common/hooks";
import { _t } from "@web/core/l10n/translation";

Chatter.props.push("hasActivities?", "hasFollowers?", "hasParentReloadOnFollowersUpdate?");

Chatter.components = {
    ...Chatter.components,
    Activity,
    SuggestedRecipientsList,
    FollowerList,
};

Chatter.defaultProps = {
    ...Chatter.defaultProps,
    hasActivities: true,
    hasFollowers: true,
    hasParentReloadOnFollowersUpdate: false,
};

patch(Chatter.prototype, {
    setup() {
        super.setup(...arguments);
        this.activityService = useState(useService("mail.activity"));
        this.state.showActivities = true;
        this.recipientsPopover = usePopover(RecipientList);
        this.unfollowHover = useHover("unfollow");
    },

    get requestList() {
        return ["followers", "attachments", "suggestedRecipients"];
    },

    /**
     * @returns {import("@mail/core/web/activity_model").Activity[]}
     */
    get activities() {
        return this.state.thread.activities;
    },

    get followerButtonLabel() {
        return _t("Show Followers");
    },

    get followingText() {
        return _t("Following");
    },

    get unfollowText() {
        return _t("Unfollow");
    },

    /**
     * @returns {string}
     */
    get toRecipientsText() {
        const recipients = [...this.state.thread.recipients].slice(0, 5).map(({ partner }) => {
            const text = partner.email ? partner.emailWithoutDomain : partner.name;
            return `<span class="text-muted" title="${escapeHTML(partner.email)}">${escapeHTML(
                text
            )}</span>`;
        });
        const formatter = new Intl.ListFormat(
            this.store.env.services["user"].lang?.replace("_", "-"),
            { type: "unit" }
        );
        if (this.state.thread.recipients.size > 5) {
            recipients.push("…");
        }
        return markup(formatter.format(recipients));
    },

    /**
     * @param {number} threadId
     * @param {['activities'|'followers'|'attachments'|'messages'|'suggestedRecipients']} requestList
     */
    load(
        threadId = this.props.threadId,
        requestList = ["followers", "attachments", "messages", "suggestedRecipients"]
    ) {
        if (this.props.hasActivities && !requestList.includes("activities")) {
            requestList.push("activities");
        }
        super.load(...arguments);
    },

    async _follow(threadModel, threadId) {
        await this.orm.call(threadModel, "message_subscribe", [[threadId]], {
            partner_ids: [this.store.self.id],
        });
        this.onFollowerChanged();
    },

    async onClickFollow() {
        if (this.props.threadId) {
            this._follow(this.props.threadModel, this.props.threadId);
        } else {
            this.onNextUpdate = (nextProps) => {
                if (nextProps.threadId) {
                    this._follow(nextProps.threadModel, nextProps.threadId);
                } else {
                    return true;
                }
            };
            await this.props.saveRecord?.();
        }
    },

    async onClickUnfollow() {
        await this.threadService.removeFollower(this.state.thread.selfFollower);
        this.onFollowerChanged();
    },

    onFollowerChanged() {
        document.body.click(); // hack to close dropdown
        this.reloadParentView();
        this.load(this.props.threadId, ["followers", "suggestedRecipients"]);
    },

    onAddFollowers() {
        this.load(this.state.thread.id, ["followers", "suggestedRecipients"]);
        if (this.props.hasParentReloadOnFollowersUpdate) {
            this.reloadParentView();
        }
    },

    toggleActivities() {
        this.state.showActivities = !this.state.showActivities;
    },

    async scheduleActivity() {
        const schedule = async (threadId) => {
            await this.activityService.schedule(this.props.threadModel, threadId);
            this.load(this.props.threadId, ["activities", "messages"]);
        };
        if (this.props.threadId) {
            schedule(this.props.threadId);
        } else {
            this.onNextUpdate = (nextProps) => {
                if (nextProps.threadId) {
                    schedule(nextProps.threadId);
                } else {
                    return true;
                }
            };
            this.props.saveRecord?.();
        }
    },

    onClickRecipientList(ev) {
        if (this.recipientsPopover.isOpen) {
            return this.recipientsPopover.close();
        }
        this.recipientsPopover.open(ev.target, { thread: this.state.thread });
    },
});

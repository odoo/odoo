import { Chatter } from "@mail/chatter/web_portal/chatter";
import { Activity } from "@mail/core/web/activity";
import { SuggestedRecipientsList } from "@mail/core/web/suggested_recipient_list";
import { RecipientList } from "@mail/core/web/recipient_list";
import { FollowerList } from "@mail/core/web/follower_list";
import { useHover } from "@mail/utils/common/hooks";

import { useState, markup } from "@odoo/owl";
import { escape } from "@web/core/utils/strings";
import { formatList } from "@web/core/l10n/utils";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";

Chatter.components = {
    ...Chatter.components,
    Activity,
    SuggestedRecipientsList,
    FollowerList,
};

Chatter.props.push("has_activities?", "hasParentReloadOnFollowersUpdate?");

Object.assign(Chatter.defaultProps, {
    has_activities: true,
    hasParentReloadOnFollowersUpdate: false,
});

patch(Chatter.prototype, {
    setup() {
        super.setup(...arguments);
        this.activityService = useState(useService("mail.activity"));
        this.recipientsPopover = usePopover(RecipientList);
        Object.assign(this.state, { showActivities: true });
        this.unfollowHover = useHover("unfollow");
        this.followerListDropdown = useDropdownState();
    },

    /**
     * @returns {import("models").Activity[]}
     */
    get activities() {
        return this.state.thread?.activities ?? [];
    },

    get afterPostRequestList() {
        return [...super.afterPostRequestList, "followers", "suggestedRecipients"];
    },

    get followerButtonLabel() {
        return _t("Show Followers");
    },

    get followingText() {
        return _t("Following");
    },

    get requestList() {
        return [...super.requestList, "followers", "attachments", "suggestedRecipients"];
    },

    /**
     * @returns {string}
     */
    get toRecipientsText() {
        if (this.state.thread?.recipients.length === 0) {
            return _t("No recipient");
        }
        const recipients = [...(this.state.thread?.recipients ?? [])]
            .slice(0, 5)
            .map(({ partner }) => {
                const text = partner.email ? partner.emailWithoutDomain : partner.name;
                return `<span class="text-muted" title="${escape(
                    partner.email || _t("no email address")
                )}">${escape(text)}</span>`;
            });
        if (this.state.thread && this.state.thread.recipients.length > 5) {
            recipients.push(
                escape(
                    _t("%(recipientCount)s more", {
                        recipientCount: this.state.thread.recipients.length - 5,
                    })
                )
            );
        }
        return markup(formatList(recipients));
    },

    get unfollowText() {
        return _t("Unfollow");
    },

    async _follow(thread) {
        await this.orm.call(thread.model, "message_subscribe", [[thread.id]], {
            partner_ids: [this.store.self.id],
        });
        this.onFollowerChanged(thread);
    },

    onActivityChanged(thread) {
        this.load(thread, [...this.requestList, "messages"]);
    },

    onAddFollowers() {
        this.load(this.state.thread, ["followers", "suggestedRecipients"]);
        if (this.props.hasParentReloadOnFollowersUpdate) {
            this.reloadParentView();
        }
    },

    async onClickFollow() {
        if (this.state.thread.id) {
            this._follow(this.state.thread);
        } else {
            this.onThreadCreated = this._follow;
            await this.props.saveRecord?.();
        }
    },

    onClickRecipientList(ev) {
        if (this.recipientsPopover.isOpen) {
            return this.recipientsPopover.close();
        }
        this.recipientsPopover.open(ev.target, { thread: this.state.thread });
    },

    async onClickUnfollow() {
        const thread = this.state.thread;
        await this.threadService.removeFollower(thread.selfFollower);
        this.onFollowerChanged(thread);
    },

    onFollowerChanged(thread) {
        document.body.click(); // hack to close dropdown
        this.reloadParentView();
        this.load(thread, ["followers", "suggestedRecipients"]);
    },

    onSuggestedRecipientAdded(thread) {
        this.load(thread, ["suggestedRecipients"]);
    },

    async scheduleActivity() {
        this.closeSearch();
        const schedule = async (thread) => {
            await this.activityService.schedule(thread.model, [thread.id]);
            this.load(thread, ["activities", "messages"]);
        };
        if (this.state.thread.id) {
            schedule(this.state.thread);
        } else {
            this.onThreadCreated = schedule;
            this.props.saveRecord?.();
        }
    },

    toggleActivities() {
        this.state.showActivities = !this.state.showActivities;
    },
});

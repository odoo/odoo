/** @odoo-module **/

import { Thread } from "../thread/thread";
import { useMessaging } from "@mail/new/messaging_hook";
import { useDropzone } from "@mail/new/utils/dropzone/dropzone_hook";
import { Composer } from "@mail/new/common/components/composer";
import { ActivityList } from "@mail/new/chatter/components/activity_list";
import { Component, useState, onWillUpdateProps, useChildSubEnv, useRef } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useService } from "@web/core/utils/hooks";
import { useHover } from "../utils";

export class Chatter extends Component {
    setup() {
        this.action = useService("action");
        this.activity = useService("mail.activity");
        this.messaging = useMessaging();
        this.orm = useService("orm");
        this.rpc = useService("rpc");
        this.state = useState({
            activities: [],
            attachments: [],
            composing: false, // false, 'message' or 'note'
            followers: [],
        });
        this.unfollowHover = useHover("unfollow");

        this.load();
        useChildSubEnv({
            inChatter: true,
            chatter: {
                reload: this.load.bind(this),
            },
        });
        useDropzone(useRef("root"));

        onWillUpdateProps((nextProps) => {
            if (nextProps.resId !== this.props.resId) {
                this.load(nextProps.resId);
                if (nextProps.resId === false) {
                    this.state.composing = false;
                }
            }
        });
    }

    get followerButtonLabel() {
        return this.env._t("Show Followers");
    }

    get followingText() {
        return this.env._t("Following");
    }

    get isDisabled() {
        return !this.props.resId;
        // TODO should depend on access rights on document
    }

    get isFollower() {
        return Boolean(
            this.state.followers.find((f) => f.partner_id === this.messaging.state.user.partnerId)
        );
    }

    load(resId = this.props.resId, requestList = ["followers", "attachments", "messages"]) {
        const { resModel } = this.props;
        const thread = this.messaging.getChatterThread(resModel, resId);
        this.thread = thread;
        if (!resId) {
            // todo: reset activities/attachments/followers
            return;
        }
        if (this.props.hasActivity && !requestList.includes("activities")) {
            requestList.push("activities");
        }
        this.messaging.fetchChatterData(resId, resModel, requestList).then((result) => {
            this.thread.hasWriteAccess = result.hasWriteAccess;
            if ("activities" in result) {
                this.state.activities = result.activities;
            }
            if ("attachments" in result) {
                this.state.attachments = result.attachments;
            }
            if ("followers" in result) {
                this.state.followers = result.followers;
            }
        });
    }

    onClickAddFollowers() {
        document.body.click(); // hack to close dropdown
        const action = {
            type: "ir.actions.act_window",
            res_model: "mail.wizard.invite",
            view_mode: "form",
            views: [[false, "form"]],
            name: this.env._t("Invite Follower"),
            target: "new",
            context: {
                default_res_model: this.props.resModel,
                default_res_id: this.props.resId,
            },
        };
        this.env.services.action.doAction(action, {
            onClose: () => {
                this.load(this.props.resId, ["followers", "suggestedRecipients"]);
                // TODO reload parent view if applicable (hasParentReloadOnFollowersUpdate)
            },
        });
    }

    async onClickFollow() {
        await this.orm.call(this.props.resModel, "message_subscribe", [[this.props.resId]], {
            partner_ids: [this.messaging.state.user.partnerId],
        });
        this.load(this.props.resId, ["followers", "suggestedRecipients"]);
    }

    async onClickUnfollow() {
        await this.orm.call(this.props.resModel, "message_unsubscribe", [[this.props.resId]], {
            partner_ids: [this.messaging.state.user.partnerId],
        });
        this.load(this.props.resId, ["followers", "suggestedRecipients"]);
    }

    toggleComposer(mode = false) {
        if (this.state.composing === mode) {
            this.state.composing = false;
        } else {
            this.state.composing = mode;
        }
    }

    async scheduleActivity() {
        await this.activity.scheduleActivity(this.props.resModel, this.props.resId);
        this.load(this.props.resId, ["activities"]);
    }

    get unfollowText() {
        return this.env._t("Unfollow");
    }
}

Object.assign(Chatter, {
    components: { Dropdown, Thread, Composer, ActivityList },
    props: ["hasActivity", "resId", "resModel", "displayName?"],
    template: "mail.chatter",
});

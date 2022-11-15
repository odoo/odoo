/** @odoo-module **/

import { Thread } from "../thread/thread";
import { useMessaging } from "../messaging_hook";
import { useDropzone } from "@mail/new/dropzone/dropzone_hook";
import { Composer } from "../composer/composer";
import { ActivityList } from "../activity/activity_list";
import { Component, useState, onWillUpdateProps, useChildSubEnv, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class Chatter extends Component {
    setup() {
        this.messaging = useMessaging();
        this.activity = useService("mail.activity");
        this.rpc = useService("rpc");
        this.action = useService("action");
        this.state = useState({
            composing: false, // false, 'message' or 'note
            activities: [],
            attachments: [],
            followers: [],
            isFollower: false,
        });

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
            if ("activities" in result) {
                this.state.activities = result.activities;
            }
            if ("attachments" in result) {
                this.state.attachments = result.attachments;
            }
            if ("followers" in result) {
                this.state.followers = result.followers;
                const partnerId = this.messaging.user.partnerId;
                this.state.isFollower = !!result.followers.find((f) => f.partner_id === partnerId);
            }
        });
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
}

Object.assign(Chatter, {
    components: { Thread, Composer, ActivityList },
    props: ["hasActivity", "resId", "resModel", "displayName?"],
    template: "mail.chatter",
});

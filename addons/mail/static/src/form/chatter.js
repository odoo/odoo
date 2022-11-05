/** @odoo-module */

import { Thread } from "../thread/thread";
import { useMessaging } from "../messaging_hook";
import { Composer } from "../composer/composer";
import { ActivityList } from "../activity/activity_list";
import { Component, useState, onWillUpdateProps, useChildSubEnv } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class Chatter extends Component {
    static template = "mail.chatter";
    static components = { Thread, Composer, ActivityList };
    static props = ["resId", "resModel"];

    setup() {
        this.messaging = useMessaging();
        this.rpc = useService("rpc");
        this.action = useService("action");
        this.state = useState({
            mode: "message", // message or note
            hasComposer: false,
            metadata: null,
        });

        this.load();
        useChildSubEnv({ inChatter: true });

        onWillUpdateProps((nextProps) => {
            if (nextProps.resId !== this.props.resId) {
                this.load(nextProps.resId);
            }
        });
    }
    load(resId = this.props.resId) {
        const thread = this.messaging.getChatterThread(this.props.resModel, resId);
        this.rpc("/mail/thread/data", {
            request_list: ["activities", "followers", "attachments", "messages"],
            thread_id: resId,
            thread_model: this.props.resModel,
        }).then((result) => {
            if (this.thread.id === thread.id) {
                this.state.metadata = result;
            }
        });
        this.thread = thread;
    }

    toggleComposer() {
        this.state.hasComposer = !this.state.hasComposer;
    }

    scheduleActivity() {
        const context = {
            default_res_id: this.props.resId,
            default_res_model: this.props.resModel,
        };
        this.action.doAction(
            {
                type: "ir.actions.act_window",
                name: this.env._t("Schedule Activity"),
                res_model: "mail.activity",
                view_mode: "form",
                views: [[false, "form"]],
                target: "new",
                context,
                res_id: false,
            },
            {
                onClose: () => {
                    // to force a reload for this thread
                    this.load();
                },
            }
        );
    }
}

/* @odoo-module */

import { useMessaging } from "@mail/core/common/messaging_hook";

import { Component, onMounted, useExternalListener, useRef } from "@odoo/owl";

import { fetchNewMessages } from "../common/thread_service";
import { getThread } from "./thread_service_patch";
import { markActivityAsDone, markActivityAsDoneAndScheduleNext } from "./activity_service";

export class ActivityMarkAsDone extends Component {
    static template = "mail.ActivityMarkAsDone";
    static props = ["activity", "close?", "hasHeader?", "onClickDoneAndScheduleNext?", "reload?"];
    static defaultProps = {
        hasHeader: false,
    };

    get isSuggested() {
        return this.props.activity.chaining_type === "suggest";
    }

    setup() {
        this.messaging = useMessaging();
        this.textArea = useRef("textarea");
        onMounted(() => {
            this.textArea.el.focus();
        });
        useExternalListener(window, "keydown", this.onKeydown);
    }

    onKeydown(ev) {
        if (ev.key === "Escape" && this.props.close) {
            this.props.close();
        }
    }

    async onClickDone() {
        const { res_id: resId, res_model: resModel } = this.props.activity;
        const thread = getThread(resModel, resId);
        await markActivityAsDone(this.props.activity);
        if (this.props.reload) {
            this.props.reload(this.props.activity.res_id, ["activities"]);
        }
        await fetchNewMessages(thread);
    }

    async onClickDoneAndScheduleNext() {
        const { res_id: resId, res_model: resModel } = this.props.activity;
        const thread = getThread(resModel, resId);
        if (this.props.onClickDoneAndScheduleNext) {
            this.props.onClickDoneAndScheduleNext();
        }
        if (this.props.close) {
            this.props.close();
        }
        const action = await markActivityAsDoneAndScheduleNext(this.props.activity);
        fetchNewMessages(thread);
        if (this.props.reload) {
            this.props.reload(this.props.activity.res_id, ["activities", "attachments"]);
        }
        if (!action) {
            return;
        }
        await new Promise((resolve) => {
            this.env.services.action.doAction(action, {
                onClose: resolve,
            });
        });
        if (this.props.reload) {
            this.props.reload(this.props.activity.res_id, ["activities"]);
        }
    }
}

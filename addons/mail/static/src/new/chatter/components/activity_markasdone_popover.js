/** @odoo-module **/

import { useMessaging } from "@mail/new/messaging_hook";

import { Component, onMounted, useExternalListener, useRef } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

export class ActivityMarkAsDone extends Component {
    get isSuggested() {
        return this.props.activity.chaining_type === "suggest";
    }

    setup() {
        this.messaging = useMessaging();
        this.textArea = useRef("textarea");
        this.activityService = useService("mail.activity");
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
        const thread = this.messaging.getChatterThread(resModel, resId);
        await this.env.services["mail.activity"].markAsDone(this.props.activity.id);
        if (this.props.reload) {
            this.props.reload(this.props.activity.res_id, ["activities"]);
        }
        await this.messaging.fetchThreadMessagesNew(thread.id);
    }

    async onClickDoneAndScheduleNext() {
        const { res_id: resId, res_model: resModel } = this.props.activity;
        const thread = this.messaging.getChatterThread(resModel, resId);
        if (this.props.onClickDoneAndScheduleNext) {
            this.props.onClickDoneAndScheduleNext();
        }
        if (this.props.close) {
            this.props.close();
        }
        await this.env.services["mail.activity"].markAsDoneAndScheduleNext(
            this.props.activity,
            thread
        );
        if (this.props.reload) {
            this.props.reload(this.props.activity.res_id, ["activities"]);
        }
    }
}

Object.assign(ActivityMarkAsDone, {
    template: "mail.activity_mark_as_done",
    props: ["activity", "close?", "onClickDoneAndScheduleNext?", "reload?"],
    defaultProps: {
        hasHeader: false,
    },
});

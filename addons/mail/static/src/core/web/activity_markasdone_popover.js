import { useRef } from "@web/owl2/utils";
import { Component, onMounted, props, signal, t, useListener } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class ActivityMarkAsDone extends Component {
    static template = "mail.ActivityMarkAsDone";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.props = props({
            activity: t.instanceOf(this.store["mail.activity"].Class),
            close: t.function([t.instanceOf(MouseEvent)]).optional(),
            hasHeader: t.boolean().optional(false),
            onActivityChanged: t.function([t.instanceOf(this.store["mail.thread"].Class)]),
            onClickDone: t.function([]).optional(),
            onClickDoneAndScheduleNext: t.function([]).optional(),
        });
        this.textArea = useRef("textarea");
        this.disableDoneButton = signal(false);
        onMounted(() => {
            this.textArea.el.focus();
        });
        useListener(window, "keydown", (ev) => this.onKeydown(ev));
    }

    onKeydown(ev) {
        if (ev.key === "Escape" && this.props.close) {
            this.props.close();
        }
    }

    async onClickDone() {
        if (this.disableDoneButton()) {
            return;
        }
        const { res_id, res_model } = this.props.activity;
        const thread = this.env.services["mail.store"]["mail.thread"].insert({
            model: res_model,
            id: res_id,
        });
        this.disableDoneButton.set(true);
        try {
            if (this.props.onClickDone) {
                this.props.onClickDone();
            }
            await this.props.activity.markAsDone();
            this.props.onActivityChanged(thread);
            await thread.fetchNewMessages();
        } finally {
            this.disableDoneButton.set(false);
        }
    }

    async onClickDoneAndScheduleNext() {
        const { res_id, res_model } = this.props.activity;
        const thread = this.env.services["mail.store"]["mail.thread"].insert({
            model: res_model,
            id: res_id,
        });
        if (this.props.onClickDoneAndScheduleNext) {
            this.props.onClickDoneAndScheduleNext();
        }
        if (this.props.close) {
            this.props.close();
        }
        const action = await this.props.activity.markAsDoneAndScheduleNext();
        thread.fetchNewMessages();
        this.props.onActivityChanged(thread);
        if (!action) {
            return;
        }
        await new Promise((resolve) => {
            this.env.services.action.doAction(action, {
                onClose: resolve,
            });
        });
        this.props.onActivityChanged(thread);
    }
}

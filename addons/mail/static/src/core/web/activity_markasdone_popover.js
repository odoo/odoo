import { Component, onMounted, signal, t, useListener, useProps } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

export class ActivityMarkAsDone extends Component {
    static template = "mail.ActivityMarkAsDone";

    textArea = signal.ref();

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.props = useProps({
            activity: t.signal(t.instanceOf(this.store["mail.activity"])),
            close: t
                .function([t.instanceOf(MouseEvent)])
                .optional()
                .static(),
            hasHeader: t.boolean().optional(false).static(),
            onActivityChanged: t.function([t.instanceOf(this.store["mail.thread"])]).static(),
            onClickDone: t.function([]).optional().static(),
            onClickDoneAndScheduleNext: t.function([]).optional().static(),
        });
        this.disableDoneButton = signal(false);
        onMounted(() => {
            this.textArea()?.focus();
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
        const { res_id, res_model } = this.props.activity();
        const thread = this.env.services["mail.store"]["mail.thread"].insert({
            model: res_model,
            id: res_id,
        });
        this.disableDoneButton.set(true);
        try {
            if (this.props.onClickDone) {
                this.props.onClickDone();
            }
            await this.props.activity().markAsDone();
            this.props.onActivityChanged(thread);
            await thread.fetchNewMessages();
        } finally {
            this.disableDoneButton.set(false);
        }
    }

    async onClickDoneAndScheduleNext() {
        const { res_id, res_model } = this.props.activity();
        const thread = this.env.services["mail.store"]["mail.thread"].insert({
            model: res_model,
            id: res_id,
        });
        this.props.onClickDoneAndScheduleNext?.();
        this.props.close?.();
        const action = await this.props.activity().markAsDoneAndScheduleNext();
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

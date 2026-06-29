import { useRef } from "@web/owl2/utils";
import { Component, onMounted, props, signal, t, useListener } from "@odoo/owl";

import { propSignal } from "@mail/utils/common/hooks";
import { useService } from "@web/core/utils/hooks";

export class ActivityMarkAsDone extends Component {
    static template = "mail.ActivityMarkAsDone";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.activity = propSignal("activity", t.instanceOf(this.store["mail.activity"].Class));
        this.close = props.static("close", t.function([t.instanceOf(MouseEvent)]).optional());
        this.hasHeader = props.static("hasHeader", t.boolean().optional(false));
        this.onActivityChanged = props.static(
            "onActivityChanged",
            t.function([t.instanceOf(this.store["mail.thread"].Class)])
        );
        this.onClickDoneProp = props.static("onClickDone", t.function([]).optional());
        this.onClickDoneAndScheduleNextProp = props.static(
            "onClickDoneAndScheduleNext",
            t.function([]).optional()
        );
        this.textArea = useRef("textarea");
        this.disableDoneButton = signal(false);
        onMounted(() => {
            this.textArea.el.focus();
        });
        useListener(window, "keydown", (ev) => this.onKeydown(ev));
    }

    onKeydown(ev) {
        if (ev.key === "Escape" && this.close) {
            this.close();
        }
    }

    async onClickDone() {
        if (this.disableDoneButton()) {
            return;
        }
        const { res_id, res_model } = this.activity();
        const thread = this.env.services["mail.store"]["mail.thread"].insert({
            model: res_model,
            id: res_id,
        });
        this.disableDoneButton.set(true);
        try {
            if (this.onClickDoneProp) {
                this.onClickDoneProp();
            }
            await this.activity().markAsDone();
            this.onActivityChanged(thread);
            await thread.fetchNewMessages();
        } finally {
            this.disableDoneButton.set(false);
        }
    }

    async onClickDoneAndScheduleNext() {
        const { res_id, res_model } = this.activity();
        const thread = this.env.services["mail.store"]["mail.thread"].insert({
            model: res_model,
            id: res_id,
        });
        this.onClickDoneAndScheduleNextProp?.();
        this.close?.();
        const action = await this.activity().markAsDoneAndScheduleNext();
        thread.fetchNewMessages();
        this.onActivityChanged(thread);
        if (!action) {
            return;
        }
        await new Promise((resolve) => {
            this.env.services.action.doAction(action, {
                onClose: resolve,
            });
        });
        this.onActivityChanged(thread);
    }
}

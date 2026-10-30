import { Component, onMounted, signal, t, useListener, useProps } from "@odoo/owl";

import { PopoverCard } from "@mail/core/common/popover_card/popover_card";
import { useService } from "@web/core/utils/hooks";

export class ActivityMarkAsDone extends Component {
    static template = "mail.ActivityMarkAsDone";
    static components = { PopoverCard };

    textArea = signal.ref();

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.props = useProps({
            activity: t.signal(t.instanceOf(this.store["mail.activity"])),
        });
        this.close = useProps.static("close", t.function([t.instanceOf(MouseEvent)]).optional());
        this.hasHeader = useProps.static("hasHeader", t.boolean().optional(false));
        this.onActivityChanged = useProps.static(
            "onActivityChanged",
            t.function([t.instanceOf(this.store["mail.thread"])])
        );
        this.onClickDoneProp = useProps.static("onClickDone", t.function([]).optional());
        this.onClickDoneAndScheduleNextProp = useProps.static(
            "onClickDoneAndScheduleNext",
            t.function([]).optional()
        );
        this.disableDoneButton = signal(false);
        onMounted(() => {
            this.textArea()?.focus();
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
        const { res_id, res_model } = this.props.activity();
        const thread = this.env.services["mail.store"]["mail.thread"].insert({
            model: res_model,
            id: res_id,
        });
        this.disableDoneButton.set(true);
        try {
            if (this.onClickDoneProp) {
                this.onClickDoneProp();
            }
            await this.props.activity().markAsDone();
            this.onActivityChanged(thread);
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
        this.onClickDoneAndScheduleNextProp?.();
        this.close?.();
        const action = await this.props.activity().markAsDoneAndScheduleNext();
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

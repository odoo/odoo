import { Component, onMounted, signal, t, useListener, useProps } from "@odoo/owl";

import { onActivityChangedType } from "@mail/core/web/activity_types";
import { propSignal } from "@mail/utils/common/hooks";
import { useService } from "@web/core/utils/hooks";

export class ActivityMarkAsDone extends Component {
    static template = "mail.ActivityMarkAsDone";

    textArea = signal.ref();

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.activity = propSignal("activity", t.instanceOf(this.store["mail.activity"]));
        this.close = useProps.static("close", t.function([t.instanceOf(MouseEvent)]).optional());
        this.hasHeader = useProps.static("hasHeader", t.boolean().optional(false));
        this.onActivityChanged = useProps.static(
            "onActivityChanged",
            onActivityChangedType(this.store)
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

    /**
     * @param {MouseEvent} ev
     * @param {{ activityAtRender: import("models").Activity }} param1
     */
    async onClickDone(ev, { activityAtRender }) {
        if (this.disableDoneButton()) {
            return;
        }
        const thread = activityAtRender.thread;
        this.disableDoneButton.set(true);
        try {
            if (this.onClickDoneProp) {
                this.onClickDoneProp();
            }
            await activityAtRender.markAsDone();
            this.onActivityChanged({ thread });
            await thread?.fetchNewMessages();
        } finally {
            this.disableDoneButton.set(false);
        }
    }

    /**
     * @param {MouseEvent} ev
     * @param {{ activityAtRender: import("models").Activity }} param1
     */
    async onClickDoneAndScheduleNext(ev, { activityAtRender }) {
        const thread = activityAtRender.thread;
        this.onClickDoneAndScheduleNextProp?.();
        this.close?.();
        const action = await activityAtRender.markAsDoneAndScheduleNext();
        thread?.fetchNewMessages();
        this.onActivityChanged({ thread });
        if (!action) {
            return;
        }
        await new Promise((resolve) => {
            this.env.services.action.doAction(action, {
                onClose: resolve,
            });
        });
        this.onActivityChanged({ thread });
    }
}

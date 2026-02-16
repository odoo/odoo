import { useExternalListener } from "@web/owl2/utils";
import { Component, onMounted, useRef, useState } from "@odoo/owl";

export class ActivityMarkAsDone extends Component {
    static template = "mail.ActivityMarkAsDone";
    static props = [
        "activity",
        "close?",
        "hasHeader?",
        "onClickDoneAndScheduleNext?",
        "onActivityChanged",
    ];
    static defaultProps = {
        hasHeader: false,
    };

    setup() {
        super.setup();
        this.textArea = useRef("textarea");
        this.state = useState({ disableDoneButton: false });
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
        if (this.state.disableDoneButton) {
            return;
        }
        const { res_id, res_model } = this.props.activity;
        const thread = this.env.services["mail.store"]["mail.thread"].insert({
            model: res_model,
            id: res_id,
        });
        this.state.disableDoneButton = true;
        try {
            await this.props.activity.markAsDone();
            this.props.onActivityChanged(thread);
            await thread.fetchNewMessages();
        } finally {
            this.state.disableDoneButton = false;
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

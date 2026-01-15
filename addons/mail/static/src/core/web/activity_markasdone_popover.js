import { Component, onMounted, useExternalListener, useRef } from "@odoo/owl";

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

    get isSuggested() {
        return this.props.activity.chaining_type === "suggest";
    }

    setup() {
        super.setup();
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
        const { res_id, res_model } = this.props.activity;
        const thread = this.env.services["mail.store"].Thread.insert({
            model: res_model,
            id: res_id,
        });
        await this.props.activity.markAsDone();
        this.props.onActivityChanged(thread);
        await thread.fetchNewMessages();
    }

    async onClickDoneAndScheduleNext() {
        const { res_id, res_model } = this.props.activity;
        const thread = this.env.services["mail.store"].Thread.insert({
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

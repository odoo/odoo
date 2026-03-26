import { CreatePollOptionDialog } from "@mail/core/common/create_poll_option_dialog";

import { Component, props, proxy, types } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { EmojiPicker } from "@web/core/emoji_picker/emoji_picker";
import { rpc } from "@web/core/network/rpc";
import { useAutofocus, useService } from "@web/core/utils/hooks";

export class CreatePollDialog extends Component {
    static template = "mail.CreatePollDialog";
    static components = { Dialog, EmojiPicker, CreatePollOptionDialog };

    setup() {
        super.setup(...arguments);
        this.store = useService("mail.store");
        this.props = props({
            close: types.function([types.instanceOf(MouseEvent)]),
            thread: types.instanceOf(this.store["mail.thread"].Class),
        });
        useAutofocus({ refName: "question" });
        this.state = proxy({
            allowMultipleOptions: false,
            duration: "10",
            options: [{ label: "" }, { label: "" }],
            question: "",
            submitted: false,
        });
    }

    onClickAddOption() {
        this.state.options.push({ label: "" });
    }

    onClickRemoveOption(index) {
        this.state.options.splice(index, 1);
    }

    async onClickSubmit() {
        this.state.submitted = true;
        if (this.optionsMissing || this.questionMissing) {
            return;
        }
        await rpc("/mail/poll/create", {
            allow_multiple_options: this.state.allowMultipleOptions,
            options: this.state.options
                .map(({ emoji, label }) => ({ emoji, label: label.trim() }))
                .filter(({ label }) => label),
            duration: parseInt(this.state.duration),
            question: this.state.question,
            thread_id: this.props.thread.id,
            thread_model: this.props.thread.model,
        });
        this.props.close();
    }

    get optionsMissing() {
        return (
            this.state.submitted &&
            this.state.options.filter(({ label }) => Boolean(label.trim())).length < 2
        );
    }

    get questionMissing() {
        return this.state.submitted && !this.state.question?.trim();
    }
}

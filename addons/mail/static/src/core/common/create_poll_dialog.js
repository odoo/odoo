import { CreatePollOptionDialog } from "@mail/core/common/create_poll_option_dialog";

import { Component, useState } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { EmojiPicker } from "@web/core/emoji_picker/emoji_picker";
import { rpc } from "@web/core/network/rpc";
import { useAutofocus, useService } from "@web/core/utils/hooks";

export class CreatePollDialog extends Component {
    static template = "mail.CreatePollDialog";
    static components = { Dialog, EmojiPicker, CreatePollOptionDialog };
    static props = ["close?", "thread?"];

    setup() {
        useAutofocus({ refName: "question" });
        this.state = useState({
            allowMultipleOptions: false,
            duration: "10",
            options: [{ label: "" }, { label: "" }],
            question: "",
            submitted: false,
        });
        this.orm = useService("orm");
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
            option_labels: this.state.options.map(({ label }) => label).filter(Boolean),
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

    get canAddOption() {
        return this.state.options.every(({ label }) => Boolean(label));
    }
}

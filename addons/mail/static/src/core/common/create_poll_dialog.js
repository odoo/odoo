import { CreatePollOptionDialog } from "@mail/core/common/create_poll_option_dialog";

import { Component, proxy, signal, types, useProps } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { EmojiPicker } from "@web/core/emoji_picker/emoji_picker";
import { rpc } from "@web/core/network/rpc";
import { uniqueId } from "@web/core/utils/functions";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { useSortable } from "@web/core/utils/sortable_owl";

export class CreatePollDialog extends Component {
    static template = "mail.CreatePollDialog";
    static components = { Dialog, EmojiPicker, CreatePollOptionDialog };

    optionsRef = signal.ref();
    questionRef = signal.ref();

    setup() {
        super.setup(...arguments);
        this.store = useService("mail.store");
        this.props = useProps({
            close: types.function([types.instanceOf(MouseEvent)]),
            thread: types.instanceOf(this.store["mail.thread"]),
        });
        useAutofocus({ ref: this.questionRef, mobile: true });
        this.state = proxy({
            allowMultipleOptions: false,
            duration: "10",
            options: [this.makeOption(), this.makeOption()],
            question: "",
            submitted: false,
        });
        useSortable({
            ref: this.optionsRef,
            elements: ".o-mail-CreatePollOptionDialog",
            handle: ".o-mail-CreatePollOptionDialog-handle",
            cursor: "grabbing",
            onDrop: ({ element, previous }) =>
                this.moveOption(element.dataset.optionId, previous?.dataset.optionId),
        });
    }

    makeOption(values = {}) {
        return { id: uniqueId("option_"), label: "", ...values };
    }

    /**
     * @param {string} optionId
     * @param {string} [previousOptionId] id of the option it is dropped after,
     *  undefined when dropped first
     */
    moveOption(optionId, previousOptionId) {
        const options = this.state.options;
        const [option] = options.splice(
            options.findIndex(({ id }) => id === optionId),
            1
        );
        // insert right after the previous option (index -1 when dropped first)
        options.splice(options.findIndex(({ id }) => id === previousOptionId) + 1, 0, option);
    }

    onClickAddOption() {
        this.state.options.push(this.makeOption({ isUserAdded: true }));
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

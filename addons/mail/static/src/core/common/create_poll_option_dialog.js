import { useSelection } from "@mail/utils/common/hooks";

import { Component, onMounted, signal } from "@odoo/owl";

import { useEmojiPicker } from "@web/core/emoji_picker/emoji_picker";
import { useService } from "@web/core/utils/hooks";
import { isEventHandled } from "@web/core/utils/misc";

export class CreatePollOptionDialog extends Component {
    static template = "mail.CreatePollOptionDialog";
    static props = ["model", "onClickRemove", "deletable"];

    setup() {
        this.pickerRef = signal();
        this.rootRef = signal();
        this.ui = useService("ui");
        this.selection = useSelection({
            ref: this.rootRef,
            model: this.props.model,
            preserveOnClickAwayPredicate: async (ev) => {
                await new Promise(setTimeout);
                return (
                    isEventHandled(ev, "emoji.selectEmoji") || this.pickerRef()?.contains(ev.target)
                );
            },
        });
        onMounted(() => this.rootRef()?.focus());
        useEmojiPicker(this.pickerRef, {
            onSelect: (str) => {
                const label = this.props.model.label;
                const firstPart = label.slice(0, this.props.model.start);
                const secondPart = label.slice(this.props.model.end, label.length);
                this.props.model.label = firstPart + str + secondPart;
                this.selection.moveCursor((firstPart + str).length);
                if (!this.ui.isSmall) {
                    this.pickerRef().focus();
                }
            },
        });
    }
}

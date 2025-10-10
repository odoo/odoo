import { useSelection } from "@mail/utils/common/hooks";

import { Component, onMounted, useRef } from "@odoo/owl";

import { useEmojiPicker } from "@web/core/emoji_picker/emoji_picker";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { isEventHandled } from "@web/core/utils/misc";

export class CreatePollOptionDialog extends Component {
    static template = "mail.CreatePollOptionDialog";
    static props = ["model", "onClickRemove", "deletable"];

    setup() {
        this.ref = useRef("root");
        this.pickerRef = useRef("picker");
        this.ui = useService("ui");
        this.selection = useSelection({
            refName: "root",
            model: this.props.model,
            preserveOnClickAwayPredicate: async (ev) => {
                // Let event be handled by bubbling handlers first.
                await new Promise(setTimeout);
                return (
                    !ev.isTrusted ||
                    isEventHandled(ev, "emoji.selectEmoji") ||
                    this.pickerRef.el?.contains(ev.target)
                );
            },
        });
        useAutofocus({ refName: "root" });
        useEmojiPicker(this.pickerRef, {
            onSelect: (str) => {
                const label = this.props.model.label;
                const firstPart = label.slice(0, this.props.model.start);
                const secondPart = label.slice(this.props.model.end, label.length);
                this.props.model.label = firstPart + str + secondPart;
                this.selection.moveCursor((firstPart + str).length);
                if (!this.ui.isSmall) {
                    this.ref.el.focus();
                }
            },
        });
        onMounted(() => this.props.registerRef?.(this.ref));
    }
}

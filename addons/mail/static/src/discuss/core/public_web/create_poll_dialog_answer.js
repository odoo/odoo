import { useSelection } from "@mail/utils/common/hooks";
import { Component, onMounted, useRef } from "@odoo/owl";
import { useEmojiPicker } from "@web/core/emoji_picker/emoji_picker";
import { useService } from "@web/core/utils/hooks";

export class CreatePollDialogAnswer extends Component {
    static template = "mail.CreatePollDialogAnswer";
    static props = ["registerRef?, model", "onClickRemove", "allowRemoval"];

    setup() {
        this.ref = useRef("root");
        this.pickerRef = useRef("picker");
        this.ui = useService("ui");
        this.selection = useSelection({ refName: "root", model: this.props.model });
        useEmojiPicker(this.pickerRef, {
            onSelect: (str) => {
                const text = this.props.model.text;
                const firstPart = text.slice(0, this.props.model.start);
                const secondPart = text.slice(this.props.model.end, text.length);
                this.props.model.text = firstPart + str + secondPart;
                this.selection.moveCursor((firstPart + str).length);
                if (!this.ui.isSmall) {
                    this.ref.el.focus();
                }
            },
        });
        onMounted(() => this.props.registerRef?.(this.ref));
    }
}

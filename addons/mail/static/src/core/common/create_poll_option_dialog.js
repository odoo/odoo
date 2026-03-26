import { useRef } from "@web/owl2/utils";
import { useSelection } from "@mail/utils/common/hooks";

import { Component, props, t } from "@odoo/owl";

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useEmojiPicker } from "@web/core/emoji_picker/emoji_picker";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { isEventHandled } from "@web/core/utils/misc";

export class CreatePollOptionDialog extends Component {
    static components = { Dropdown, DropdownItem };
    static template = "mail.CreatePollOptionDialog";

    setup() {
        this.props = props({
            deletable: t.boolean(),
            model: t.object({
                direction: t.selection(["forward", "backward", "none"]).optional(),
                end: t.number().optional(),
                label: t.string(),
                start: t.number().optional(),
            }),
            onClickRemove: t.function([t.instanceOf(MouseEvent)]),
        });
        this.pickerRef = useRef("picker");
        this.rootRef = useAutofocus({ refName: "root" });
        this.ui = useService("ui");
        useSelection({
            refName: "root",
            model: this.props.model,
            preserveOnClickAwayPredicate: async (ev) => {
                await new Promise(setTimeout);
                return (
                    isEventHandled(ev, "emoji.selectEmoji") ||
                    this.pickerRef.el?.contains(ev.target)
                );
            },
        });
        this.emojiPicker = useEmojiPicker(undefined, {
            onSelect: (emoji) => {
                this.props.model.emoji = emoji;
                if (!this.ui.isSmall) {
                    this.rootRef.el?.focus();
                }
            },
        });
    }

    get emojiPickerAnchor() {
        return this.ui.isSmall ? undefined : this.pickerRef;
    }

    onClickEmojiDropdownButton(ev) {
        if (this.emojiPicker.isOpen) {
            ev.stopPropagation();
            this.emojiPicker.close();
        }
    }

    onClickRemoveEmoji() {
        this.props.model.emoji = "";
    }

    openEmojiPicker() {
        this.emojiPicker.open(this.emojiPickerAnchor);
    }

    toggleEmojiPicker() {
        this.emojiPicker.toggle(this.emojiPickerAnchor);
    }
}

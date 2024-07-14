/* @odoo-module */

import { EmojiPicker } from "@web/core/emoji_picker/emoji_picker";

import { patch } from "@web/core/utils/patch";

EmojiPicker.props.push("hasRemoveFeature?");

patch(EmojiPicker.prototype, {
    removeEmoji() {
        this.props.onSelect(false);
        this.gridRef.el.scrollTop = 0;
        this.props.close?.();
        this.props.onClose?.();
    },
});

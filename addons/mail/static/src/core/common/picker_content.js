/* @odoo-module */

import { Component } from "@odoo/owl";
import { markEventHandled } from "@web/core/utils/misc";
import { EmojiPicker } from "@web/core/emoji_picker/emoji_picker";

/**
 * PickerContent is the content displayed in the popover/Picker.
 * It is used to display the emoji picker/gif picker (if it is enabled).
 */
export class PickerContent extends Component {
    static components = { EmojiPicker };
    static props = ["PICKERS", "close", "pickers", "state", "storeScroll"];
    static template = "mail.PickerContent";

    onClick(ev) {
        markEventHandled(ev, "PickerContent.onClick");
    }
}

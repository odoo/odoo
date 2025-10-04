/* @odoo-module */

import { Composer } from "@mail/core/common/composer";
import { markEventHandled } from "@web/core/utils/misc";

import { useRef, useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

/** @type {Composer} */
const composerPatch = {
    setup() {
        this.gifPickerService = useState(useService("discuss.gifPicker"));
        this.gifButton = useRef("gif-button");
        super.setup();
        this.ui = useState(useService("ui"));
    },
    get pickerSettings() {
        const setting = super.pickerSettings;
        if (this.hasGifPicker) {
            setting.pickers.gif = (gif) => this.sendGifMessage(gif);
            if (this.hasGifPickerButton) {
                setting.buttons.push(this.gifButton);
            }
        }
        return setting;
    },
    get hasGifPicker() {
        return (
            (this.gifPickerService.hasGifPickerFeature || this.store.user?.isAdmin) &&
            !this.env.inChatter &&
            !this.props.composer.message
        );
    },
    get hasGifPickerButton() {
        return this.hasGifPicker && !this.ui.isSmall && !this.env.inChatWindow;
    },
    onClickAddGif(ev) {
        markEventHandled(ev, "Composer.onClickAddGif");
    },
    async sendGifMessage(gif) {
        await this._sendMessage(gif.url, {
            parentId: this.props.messageToReplyTo?.message?.id,
        });
    },
};
patch(Composer.prototype, composerPatch);

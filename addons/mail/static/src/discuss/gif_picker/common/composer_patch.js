/* @odoo-module */

import { GifPicker, useGifPicker } from "@mail/discuss/gif_picker/common/gif_picker";
import { Composer } from "@mail/core/common/composer";
import { onExternalClick } from "@mail/utils/common/hooks";
import { isEventHandled, markEventHandled } from "@web/core/utils/misc";

import { useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

Object.assign(Composer.components, { GifPicker });
/** @type {Composer} */
const composerPatch = {
    setup() {
        super.setup();
        Object.assign(this.KEYBOARD, { GIF: "Gif" });
        onExternalClick("gif-picker", () => (this.state.keyboard = this.KEYBOARD.NONE));
        this.ui = useState(useService("ui"));
        this.gifPickerService = useState(useService("discuss.gifPicker"));
        this.gifPicker = useGifPicker("gif-button", {
            onSelected: this.sendGifMessage.bind(this),
        });
    },
    /**
     * @param {Event} ev
     * @returns {boolean}
     */
    isEventHandledByPicker(ev) {
        return (
            super.isEventHandledByPicker(ev) ||
            isEventHandled(ev, "Composer.onClickAddGif") ||
            isEventHandled(ev, "GifPicker.onClick")
        );
    },
    onClickAddGif(ev) {
        markEventHandled(ev, "Composer.onClickAddGif");
        if (!this.ui.isSmall) {
            this.gifPicker.toggle();
        } else {
            if (this.state.keyboard !== this.KEYBOARD.GIF) {
                this.state.keyboard = this.KEYBOARD.GIF;
            } else {
                this.state.keyboard = this.KEYBOARD.NONE;
            }
        }
    },
    async sendGifMessage(gif) {
        await this._sendMessage(gif.url, {
            parentId: this.props.messageToReplyTo?.message?.id,
        });
    },
};
patch(Composer.prototype, composerPatch);

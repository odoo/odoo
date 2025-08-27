import { Composer } from "@mail/core/common/composer";
import { markEventHandled } from "@web/core/utils/misc";

import { markup, useRef } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

/** @type {Composer} */
const composerPatch = {
    setup() {
        this.gifButton = useRef("gif-button");
        super.setup();
        this.ui = useService("ui");
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
            (this.store.hasGifPickerFeature || this.store.self.main_user_id?.is_admin) &&
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
        const href = encodeURI(gif.url);
        await this._sendMessage(
            markup`<a href="${href}" target="_blank" rel="noreferrer noopener">${gif.url}</a>`,
            {
                parentId: this.props.composer.replyToMessage?.id,
            }
        );
    },
};
patch(Composer.prototype, composerPatch);

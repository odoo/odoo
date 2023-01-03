/** @odoo-module **/
import { useRef, onMounted, onWillUnmount } from "@odoo/owl";

/*
 * Common code for EmojisTextField and EmojisCharField
 */
export const EmojisFieldCommon = {
    /**
     * Create an emoji textfield view to enable opening an emoji popover
     */
    _setupOverride() {
        this.triggerButton = useRef("emojisButton");
        onWillUnmount(() => this.emojiTextField && this.emojiTextField.delete());
        onMounted(async () => {
            const messaging = await this.env.services.messaging.get();
            this.emojiTextField = await messaging.models["EmojiTextFieldView"].insert({
                buttonEmojisRef: this.triggerButton,
                textInputRef: this.targetEditElement,
                inputModifiedCallback: this._emojiAdded ? this._emojiAdded.bind(this) : null,
            });
        });
    },
};

/** @odoo-module **/

import {
    EmojisTextField,
    emojisTextField,
} from "@mail/views/fields/emojis_text_field/emojis_text_field";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

/**
 * SmsWidget is a widget to display a textarea (the body) and a text representing
 * the number of SMS and the number of characters. This text is computed every
 * time the user changes the body.
 */
export class SmsWidget extends EmojisTextField {
    setup() {
        super.setup();
        this._emojiAdded = () => this.props.record.update({ [this.props.name]: this.targetEditElement.el.value });
        this.notification = useService('notification');
    }

    get encoding() {
        return this._extractEncoding(this.props.record.data[this.props.name] || '');
    }
    get nbrChar() {
        const content = this.props.record.data[this.props.name] || '';
        return content.length + (content.match(/\n/g) || []).length;
    }
    get nbrSMS() {
        return this._countSMS(this.nbrChar, this.encoding);
    }

    //--------------------------------------------------------------------------
    // Private: SMS
    //--------------------------------------------------------------------------

    /**
     * Count the number of SMS of the content
     * @private
     * @returns {integer} Number of SMS
     */
    _countSMS(nbrChar, encoding) {
        if (nbrChar === 0) {
            return 0;
        }
        if (encoding === 'UNICODE') {
            if (nbrChar <= 70) {
                return 1;
            }
            return Math.ceil(nbrChar / 67);
        }
        if (nbrChar <= 160) {
            return 1;
        }
        return Math.ceil(nbrChar / 153);
    }

    /**
     * Extract the encoding depending on the characters in the content
     * @private
     * @param {String} content Content of the SMS
     * @returns {String} Encoding of the content (GSM7 or UNICODE)
     */
    _extractEncoding(content) {
        if (String(content).match(RegExp("^[@£$¥èéùìòÇ\\nØø\\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\\\"#¤%&'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà]*$"))) {
            return 'GSM7';
        }
        return 'UNICODE';
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    async onBlur() {
        var content = this.props.record.data[this.props.name] || '';
        if( !content.trim().length && content.length > 0) {
            this.notification.add(
                this.env._t("Your SMS Text Message must include at least one non-whitespace character"),
                { type: 'danger' },
            )
            await this.props.record.update({ [this.props.name]: content.trim() });
        }
    }

    /**
     * @override
     * @private
     */
    async onInput(ev) {
        super.onInput(...arguments);
        await this.props.record.update({ [this.props.name]: this.targetEditElement.el.value });
    }
}
SmsWidget.template = 'sms.SmsWidget';

export const smsWidget = {
    ...emojisTextField,
    component: SmsWidget,
    additionalClasses: [
        ...(emojisTextField.additionalClasses || []),
        "o_field_text",
        "o_field_text_emojis",
    ],
};

registry.category("fields").add("sms_widget", smsWidget);

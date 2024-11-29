import { _t } from "@web/core/l10n/translation";
import {
    EmojisTextField,
    emojisTextField,
} from "@mail/views/web/fields/emojis_text_field/emojis_text_field";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

/**
 * SmsWidget is a widget to display a textarea (the body) and a text representing
 * the number of SMS and the number of characters. This text is computed every
 * time the user changes the body.
 */
export class SmsWidget extends EmojisTextField {
    static template = "sms.SmsWidget";
    setup() {
        super.setup();
        this._emojiAdded = () => this.props.record.update({ [this.props.name]: this.targetEditElement.el.value });
        this.notification = useService('notification');
    }

    get encoding() {
        return this._extractEncoding(this.props.record.data[this.props.name] || '');
    }
    get nbrChar() {
        const content = this._getValueForSmsCounts(this.props.record.data[this.props.name] || "");
        return content.length + (content.match(/\n/g) || []).length;
    }
    get nbrCharExplanation() {
        return "";
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

    /**
     * Implement if more characters are going to be sent then those appearing in
     * value, if that value is processed before being sent.
     * E.g., links are converted to trackers in mass_mailing_sms.
     *
     * Note: goes with an explanation in nbrCharExplanation
     *
     * @param {String} value content to be parsed for counting extra characters
     * @return string length-corrected value placeholder for the post-processed
     * state
     */
    _getValueForSmsCounts(value) {
        return value;
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    async onBlur() {
        await super.onBlur();
        var content = this.props.record.data[this.props.name] || '';
        if( !content.trim().length && content.length > 0) {
            this.notification.add(
                _t("Your SMS Text Message must include at least one non-whitespace character"),
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

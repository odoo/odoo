import { _t } from "@web/core/l10n/translation";
import {
    EmojisTextField,
    emojisTextField,
} from "@mail/views/web/fields/emojis_text_field/emojis_text_field";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { Component, useState } from "@odoo/owl";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { debounce } from "@web/core/utils/timing";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

/**
 * Count the number of SMS of the content
 * @returns {integer} Number of SMS
 */
function countSMS(nbrChar, encoding) {
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
 * @param {String} content Content of the SMS
 * @returns {String} Encoding of the content (GSM7 or UNICODE)
 */
function extractEncoding(content) {
    if (String(content).match(RegExp("^[@£$¥èéùìòÇ\\nØø\\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\\\"#¤%&'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà]*$"))) {
        return 'GSM7';
    }
    return 'UNICODE';
}


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
        return extractEncoding(this.props.record.data[this.props.name] || '');
    }
    get nbrChar() {
        const content = this._getValueForSmsCounts(this.props.record.data[this.props.name] || "");
        return content.length + (content.match(/\n/g) || []).length;
    }
    get nbrCharExplanation() {
        return "";
    }
    get nbrSMS() {
        return countSMS(this.nbrChar, this.encoding);
    }

    //--------------------------------------------------------------------------
    // Private: SMS
    //--------------------------------------------------------------------------

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
    onInput(ev) {
        super.onInput(...arguments);
        const value = ev.target.value;
        this.debouncedUpdate(value);
    }

    debouncedUpdate = debounce((value) => {
            this.props.record.model.updateRecord(this.props.record, {
                [this.props.name]: value
            });
        }, 300);
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


export class SmsCharCounter extends Component {
    static template = "sms.SmsCharCounter";
    static props = {
        ...standardWidgetProps,
    };

    setup() {
        this.state = useState({
            nbrChar: 0,
            nbrSMS: 0,
            encoding: "GSM7",
            maxChar: 160
        });
        useRecordObserver((record) => {
            const bodyValue = record.data.body || "";
            const nbrChar = bodyValue.length + (bodyValue.match(/\n/g) || []).length;
            const encoding = extractEncoding(bodyValue);
            const nbrSMS = countSMS(nbrChar, encoding);
            
            this.state.nbrChar = nbrChar;
            this.state.nbrSMS = nbrSMS;
            this.state.encoding = encoding;
            this.state.maxChar = encoding === "UNICODE" ? 70 : 160;
        });
    }

    get nbrChar() {
        return this.state.nbrChar;
    }

    get nbrSMS() {
        return this.state.nbrSMS;
    }

    get encoding() {
        return this.state.encoding;
    }

    get maxChar() {
        return this.state.maxChar;
    }

}

export const smsCharCounter = {
    component: SmsCharCounter,
};

registry.category("view_widgets").add("sms_char_counter", {
    component: SmsCharCounter,
});

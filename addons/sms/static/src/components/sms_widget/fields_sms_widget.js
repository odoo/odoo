import { Component, onMounted, onWillUnmount, proxy } from "@odoo/owl";

import {
    EmojisTextField,
    emojisTextField,
} from "@mail/views/web/fields/emojis_text_field/emojis_text_field";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

// SMS allows up to 140 bytes (1120 bits) per message payload.
// GSM-7 uses 7 bits per character: 1120 / 7 = 160 chars.
// Concatenated GSM-7 uses 6 bytes for the UDH header, leaving 134 bytes (1072 bits): 1072 / 7 = 153 chars per segment.
const GSM7_MAX_CHAR = 160;
const GSM7_CONCATENATED_MAX_CHAR = 153;

// UCS-2 uses 16 bits (2 bytes) per character: 140 / 2 = 70 chars.
// Concatenated UCS-2 uses 6 bytes for the UDH header, leaving 134 bytes: floor(134 / 2) = 67 chars per segment.
const UCS2_MAX_CHAR = 70;
const UCS2_CONCATENATED_MAX_CHAR = 67;

/**
 * Count the number of SMS of the content
 * @param {integer} nbrChar Number of characters
 * @param {String} encoding Encoding of the content (GSM7 or UNICODE)
 * @returns {integer} Number of SMS
 */
function countSMS(nbrChar, encoding) {
    if (nbrChar === 0) return 0;
    if (encoding === 'UNICODE') {
        return nbrChar <= UCS2_MAX_CHAR ? 1 : Math.ceil(nbrChar / UCS2_CONCATENATED_MAX_CHAR);
    }
    return nbrChar <= GSM7_MAX_CHAR ? 1 : Math.ceil(nbrChar / GSM7_CONCATENATED_MAX_CHAR);
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
 * SmsWidget is a widget to display a textarea (the body) and handle SMS input.
 */
export class SmsWidget extends EmojisTextField {
    static template = "sms.SmsWidget";
    setup() {
        super.setup();
        this._emojiAdded = () => this.props.record.update({ [this.props.name]: this.targetEditElement.el.value });
        this.notification = useService('notification');
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


export class SmsCharCounter extends Component {
    static template = "sms.SmsCharCounter";
    static props = {
        ...standardWidgetProps,
    };

    setup() {
        this.state = proxy({ value: "" });

        onMounted(() => {
            const textarea = document.querySelector(".o_field_widget[name='body'] textarea, .o_field_widget[name='body'] input");
            if (textarea) {
                this._onInputHandler = (ev) => {
                    this.state.value = ev.target.value;
                };
                textarea.addEventListener("input", this._onInputHandler);
                this.state.value = textarea.value || "";
            }
        });

        onWillUnmount(() => {
            const textarea = document.querySelector(".o_field_widget[name='body'] textarea, .o_field_widget[name='body'] input");
            if (textarea && this._onInputHandler) {
                textarea.removeEventListener("input", this._onInputHandler);
            }
        });
    }

    get nbrChar() {
        const val = this.state.value;
        return val.length + (val.match(/\n/g) || []).length;
    }

    get nbrCharExplanation() {
        return "";
    }

    get encoding() {
        return extractEncoding(this.state.value);
    }

    get nbrSMS() {
        return countSMS(this.nbrChar, this.encoding);
    }

    get maxChar() {
        return this.encoding === "UNICODE" ? UCS2_MAX_CHAR : GSM7_MAX_CHAR;
    }
}

registry.category("view_widgets").add("sms_char_counter", {
    component: SmsCharCounter,
});

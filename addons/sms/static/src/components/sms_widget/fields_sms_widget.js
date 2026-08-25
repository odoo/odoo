import {
    EmojisTextField,
    emojisTextField,
} from "@mail/views/web/fields/emojis_text_field/emojis_text_field";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";


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

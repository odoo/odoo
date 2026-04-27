/** @odoo-module **/
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { CharField } from "@web/views/fields/char/char_field";
import { FloatField } from "@web/views/fields/float/float_field";
import { IntegerField } from "@web/views/fields/integer/integer_field";
import { MonetaryField } from "@web/views/fields/monetary/monetary_field";
import { BooleanField } from "@web/views/fields/boolean/boolean_field";
import { DateTimeField } from '@web/views/fields/datetime/datetime_field';
import { RadioField } from "@web/views/fields/radio/radio_field";


export class DialogMessagesRenderer extends X2ManyField {
    static template = "dialog_messages_renderer_template";
    static props = {
        ...X2ManyField.props,
        context: { type: Object, optional: true },
    }
    static components = {
        CharField,
        RadioField,
        DateTimeField,
        FloatField,
        IntegerField,
        MonetaryField,
        BooleanField,
    };
}

export const dialogMessageField = {
    ...x2ManyField,
    component: DialogMessagesRenderer,
    displayName: _t("Dialog Message"),
};


registry.category("fields").add("dialog_message", dialogMessageField);

/* @odoo-module */

import { EmojisFieldCommon } from "@mail/views/web/fields/emojis_field_common/emojis_field_common";

import { useRef } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { CharField, charField } from "@web/views/fields/char/char_field";

/**
 * Extension of the FieldChar that will add emojis support
 */
export class EmojisCharField extends EmojisFieldCommon(CharField) {
    setup() {
        super.setup();
        this.targetEditElement = useRef("input");
        this._setupOverride();
    }

    get shouldTrim() {
        return false;
    }
}

EmojisCharField.template = "mail.EmojisCharField";
EmojisCharField.components = { ...CharField.components };

export const emojisCharField = {
    ...charField,
    component: EmojisCharField,
    additionalClasses: [...(charField.additionalClasses || []), "o_field_text"],
};

registry.category("fields").add("char_emojis", emojisCharField);

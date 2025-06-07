import { EmojisFieldCommon } from "@mail/views/web/fields/emojis_field_common/emojis_field_common";

import { registry } from "@web/core/registry";
import { TextField, textField } from "@web/views/fields/text/text_field";

/**
 * Extension of the FieldText that will add emojis support
 */
export class EmojisTextField extends EmojisFieldCommon(TextField) {
    static template = "mail.EmojisTextField";
    static components = { ...TextField.components };
    setup() {
        super.setup();
        this.targetEditElement = this.textareaRef;
        this._setupOverride();
    }
}

export const emojisTextField = {
    ...textField,
    component: EmojisTextField,
    additionalClasses: [...(textField.additionalClasses || []), "o_field_text"],
};

registry.category("fields").add("text_emojis", emojisTextField);

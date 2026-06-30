import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { booleanField, BooleanField } from "@web/views/fields/boolean/boolean_field";

export class BooleanPhoneField extends BooleanField {
    static template = "im_livechat.BooleanPhoneField";
}

registry.category("fields").add("boolean_phone", {
    ...booleanField,
    component: BooleanPhoneField,
    displayName: _t("In call"),
});

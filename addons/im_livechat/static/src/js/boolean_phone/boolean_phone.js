import {registry} from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { booleanField, BooleanField } from "../../../../../web/static/src/views/fields/boolean/boolean_field";

export class BooleanPhoneField extends BooleanField {
    static template = "im_livechat.BooleanPhoneField";
    static props = {
        ...BooleanField.props,
    };
}

export const booleanPhoneField = {
    ...booleanField,
    component: BooleanPhoneField,
    displayName: _t("Boolean Phone"),
};

registry.category("fields").add("boolean_phone", booleanPhoneField);

// @ts-check

/** @module @web/fields/relational/many2one_avatar/many2one_avatar_field - Many2one field variant that displays the related record avatar */

import { registry } from "@web/core/registry";
import {
    buildM2OFieldDescription,
    extractM2OFieldProps,
    Many2OneField,
} from "@web/fields/relational/many2one/many2one_field";

export class Many2OneAvatarField extends Many2OneField {
    static template = "web.Many2OneAvatarField";
}

export const many2OneAvatarField = {
    ...buildM2OFieldDescription(Many2OneAvatarField),
    extractProps(staticInfo, dynamicInfo) {
        return {
            ...extractM2OFieldProps(staticInfo, dynamicInfo),
            canOpen:
                "no_open" in staticInfo.options
                    ? !staticInfo.options.no_open
                    : staticInfo.viewType === "form",
        };
    },
};

registry.category("fields").add("many2one_avatar", many2OneAvatarField);

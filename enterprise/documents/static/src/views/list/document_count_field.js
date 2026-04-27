/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { IntegerField } from "@web/views/fields/integer/integer_field";

export class DocumentCountIntegerField extends IntegerField {
    get formattedValue() {
        if (!this.value) {
            return "";
        } else if (this.value == 1) {
            return _t("1 document", this.value);
        }
        return _t("%s documents", this.value);
    }
}

const documentCountIntegerField = {
    component: DocumentCountIntegerField,
    displayName: _t("DocumentCountIntegerField"),
    supportedTypes: ["integer"],
};

registry.category("fields").add("document_count", documentCountIntegerField);

/** @odoo-module **/
import { registry } from "@web/core/registry";
import { buildM2OFieldDescription, Many2OneField } from "@web/views/fields/many2one/many2one_field";


export class Many2OneNoSaveField extends Many2OneField {
    get m2oProps() {
        const props = super.m2oProps;
        return {
            ...props,
            willOpenRecordInDialog: () => true,
        };
    }
}

export const many2OneNoSave = {
    ...buildM2OFieldDescription(Many2OneNoSaveField),
};

registry.category("fields").add("many2one_no_save", many2OneNoSave);

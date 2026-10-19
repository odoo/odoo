/** @odoo-module **/
import { registry } from "@web/core/registry";
import { aceField, AceField } from "@web/views/fields/ace/ace_field";
import { IrUiViewCodeEditor } from "@web/core/ir_ui_view_code_editor/code_editor";

export class IrUiViewAceField extends AceField {
    static template = "web.IrUIViewAceField";
    static components = { IrUiViewCodeEditor };

    get invalidLocators() {
        const { resId, resModel } = this.props.record;
        if (resModel === "ir.ui.view" && resId) {
            return this.props.record.data.invalid_locators || undefined;
        }
        return undefined; // as if the props was unset
    }
}

export const irUiViewAceField = {
    ...aceField,
    component: IrUiViewAceField,
    additionalClasses: ["o_field_ace"],
};

registry.category("fields").add("code_ir_ui_view", irUiViewAceField);

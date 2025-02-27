/** @odoo-module **/
import { registry } from "@web/core/registry";
import { aceField, AceField } from "@web/views/fields/ace/ace_field";
import { IrUiViewCodeEditor } from "@web/core/ir_ui_view_code_editor/code_editor";

export class IrUiViewAceField extends AceField {
    static template = "web.IrUIViewAceField";
    static components = { IrUiViewCodeEditor };
}

export const irUiViewAceField = {
    ...aceField,
    component: IrUiViewAceField,
    additionalClasses: ["o_field_ace"],
};

registry.category("fields").add("code_ir_ui_view", irUiViewAceField);

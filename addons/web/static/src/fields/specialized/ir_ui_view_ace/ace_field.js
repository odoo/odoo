// @ts-check

/** @module @web/fields/specialized/ir_ui_view_ace/ace_field - Code editor field variant for ir.ui.view XML arch editing */

/** @odoo-module **/
import { IrUiViewCodeEditor } from "@web/components/ir_ui_view_code_editor/code_editor";
import { registry } from "@web/core/registry";
import { AceField, aceField } from "@web/fields/specialized/ace/ace_field";

// @ts-expect-error OWL static props typing
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

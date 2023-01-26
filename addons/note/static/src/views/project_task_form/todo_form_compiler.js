/** @odoo-module **/
import { FormCompiler } from "@web/views/form/form_compiler";

export class TodoFormCompiler extends FormCompiler {
    /**
     * override to add a class to the main container of the form
     * This class is used to display a to-do form without margin
     */
    compileSheet(el, params) {
        const result = super.compileSheet(el,params);
        result.className = result.className + "  o_todo_form_sheet_bg";
        return result;
    }
}

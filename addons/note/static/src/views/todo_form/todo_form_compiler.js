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

    compileField(el, params) {
        // In todo form view, we declare name as required.
        // We can't declare it as invisible too, because required won't be taken into account properly.
        // So we override the compileField method in order not to render it.
        if (el.getAttribute("name") == "name") {
            return;
        }
        return super.compileField(el, params);
    }
}

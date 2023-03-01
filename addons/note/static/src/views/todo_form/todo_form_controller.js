/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { Field } from "@web/views/fields/field";
const { useState } = owl;

/**
 *  The FormController is overrided to be able to manage the edition of the name of a to-do directly
 *  in the breadcrumb as well as the mark as done button next to it.
 */

export class TodoFormController extends FormController {
    setup() {
        super.setup();
        this.isDone = false;
        this.todoState = useState({
            isDone: this.isDone,
        });
    }

    /**
     * @private
     * @param {InputEvent} ev
     */
    async _onDoneToggled(ev) {
        this.saveButtonClicked();
        this.isDone = !this.isDone;
        //TODO: + orm call to update model state field
    }

    /**
     * @private
     * @param {InputEvent} ev
     */
    _actualizeDoneState(ev) {
        this.todoState.isDone = this.isDone;
    }
}

TodoFormController.template = 'note.TodoFormView';
TodoFormController.components = {
    ...FormController.components,
    Field,
};

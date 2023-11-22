/** @odoo-module */

import { useState, onRendered, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { StateSelectionField, stateSelectionField } from "@web/views/fields/state_selection/state_selection_field";

export class TodoDoneCheckmark extends StateSelectionField {
    static template = "project_todo.TodoDoneCheckmark";
    static props = {
        ...stateSelectionField.component.props,
        viewType: { type: String },
    };
    setup() {
        super.setup();
        this.stateDone = useState({
            isDone: false, //This state determines the appearance of the done checkmark and should only be actualized when the mouse leaves it (and atfer the form is loaded)
            notReloadState: false, //used to avoid a change of the checkmark when re-rendering the form
        });
        onMounted(() => {
            const fieldValue = this.props.record.data[this.props.name]
            this.notDoneState = fieldValue == '1_done' ? '01_in_progress' : fieldValue;
        });
        onRendered(() => {
            if (!this.stateDone.notReloadState) {
                this.stateDone.isDone = this.props.record.data[this.props.name] == '1_done';
            }
        });
    }

    /**
     * @private
     * @param {InputEvent} ev
     */
    actualizeDoneState(ev) {
        this.stateDone.notReloadState = false;
    }

    /**
     * @private
     * @param {InputEvent} ev
     */
    freezeDoneState(ev) {
        this.stateDone.notReloadState = true;
    }

    /**
     * @private
     * @param {InputEvent} ev
     */
    async onDoneToggled(ev) {
        const value = this.props.record.data[this.props.name] != '1_done' ? '1_done' : this.notDoneState;
        if (['kanban', 'list'].includes(this.props.viewType)) {
            await super.updateRecord(value);
        }
        else {
            await this.props.record.update({
                [this.props.name]: value,
            });
        }
    }
}

export const todoDoneCheckmark = {
    ...stateSelectionField,
    component: TodoDoneCheckmark,
    extractProps: (fieldInfo, dynamicInfo) => {
        const props = stateSelectionField.extractProps(fieldInfo, dynamicInfo);
        props.viewType = fieldInfo.viewType;
        return props;
    },
}

registry.category("fields").add("todo_done_checkmark", todoDoneCheckmark);

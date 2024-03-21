/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Component, reactive, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";


export class RecurrenceUpdateSelect extends Component {
    static template = "calendar.RecurrenceUpdateSelect";
    static props = {
        ...standardFieldProps,
    };
    setup() {
        this.reactiveRecord = reactive(this.props.record, () => {this.updatePossibleValues()})
        this.state = useState({})
        this.updatePossibleValues()
    }

    updatePossibleValues(){
        this.state.possibleValues = {
            self_only: {
                checked: true,
                label: _t("This event"),
            },
            future_events: {
                checked: false,
                label: _t("This and following events"),
            }
        }
        if (this.reactiveRecord.data['show_all_events']){
            this.state.possibleValues.all_events = {
                checked: false,
                label: _t("All events"),
            }
        }
    }

    get selected() {
        return Object.entries(this.state.possibleValues).find((state) => state[1].checked)[0];
    }

    set selected(val) {
        this.state.possibleValues[this.selected].checked = false;
        this.state.possibleValues[val].checked = true;
        this.updateRecord(this.selected)
    }
    async updateRecord(value) {
        await this.props.record.update({ [this.props.name]: value });
    }
}

export const recurrenceUpdateSelect = {
    component: RecurrenceUpdateSelect,
    displayName: _t("Recurrence Update Type"),
    supportedTypes: ["selection"],
}

registry.category("fields").add("recurrence_update_select", recurrenceUpdateSelect);

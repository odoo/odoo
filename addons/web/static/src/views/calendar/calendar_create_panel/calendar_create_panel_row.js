/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";

/**
 * Subcomponent to render a single field row. Depending on field type,
 * we display a different widget. We specifically handle "many2one" with AutoComplete.
 */
export class FieldRow extends Component {
    static template = "web.CalendarSuperQuickPanelFieldRow";
    static components = { AutoComplete };
    static props = {
        fieldName: String,
        fieldInfo: Object,
        value: { type: [String, Number, Boolean], optional: true },
        onChange: Function, // callback for updated value
        // We also pass in an 'orm' and 'env' or other services if needed to load name_search
        orm: Object,
        model: Object
    };

    setup() {
        this.state = useState({
            // If you want to store local stuff, do it here
        });
    }

    // For many2one: define an AutoComplete source
    get autoCompleteProps() {
        return {
            placeholder: this.fieldInfo.string || this.fieldInfo.name,
            autoSelect: true,
            resetOnSelect: true,
            value: this.props.value || "",
            onSelect: (option) => {
                if (option.action) {
                    option.action();
                } else {
                    // user picked an existing record
                    this.triggerChange(option.value);
                }
            },
            sources: [
                {
                    placeholder: "Loading...",
                    options: (request) => this.loadM2ORecords(this, request),
                    optionTemplate: "web.CalendarSuperQuickPanelAutoCompleteOption",
                },
            ],
        };
    }

    async loadM2ORecords(field, request) {
        // This is analogous to the name_search approach in CalendarFilterPanel
        // 1) identify the model from field attrs
        console.log(this.props.orm);
        console.log(field);
        const relation = this.props.model.fields[field.props.fieldName].relation;
        if (!relation) {
            return [{ label: "No relation", unselectable: true }];
        }
        // 2) build domain
        const domain = []; // adapt as needed
        // 3) call name_search
        const records = await this.props.model.orm.call(relation, "name_search", [], {
            name: request,
            operator: "ilike",
            args: domain,
            limit: 8,
            context: {}, // pass context if needed
        });
        // 4) build the options
        const options = records.map((res) => ({
            value: res[0], // ID
            label: res[1], // Name
            model: relation,
        }));
        if (records.length === 0) {
            options.push({
                label: "No records",
                classList: "o_m2o_no_result",
                unselectable: true,
            });
        }
        return options;
    }

    triggerChange(newVal) {
        // call parent callback
        this.props.onChange(this.props.fieldName, newVal);
    }

    onValueChange(ev) {
        let newVal;
        if (ev.target.type === "checkbox") {
            newVal = ev.target.checked;
        } else if (ev.target.type === "number") {
            newVal = ev.target.value ? parseFloat(ev.target.value) : 0;
        } else {
            newVal = ev.target.value;
        }
        this.triggerChange(newVal);
    }

    get fieldInfo() {
        return this.props.fieldInfo;
    }
}
/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { uuid } from "../../utils";

import { Component, useState, useRef, useEffect } from "@odoo/owl";

export class PropertyDefinitionSelection extends Component {
    setup() {
        this.notification = useService("notification");

        // when we create a new option, it's added in the state
        // when we have finished to edit it (blur / enter) we propagate
        // the new value in the props
        this.state = useState({ newOption: null });

        this.propertyDefinitionSelectionRef = useRef("propertyDefinitionSelection");
        this.addButtonRef = useRef("addButton");

        useEffect(() => {
            // automatically give the focus to the new option if it is empty
            const inputs = this.propertyDefinitionSelectionRef.el.querySelectorAll(
                ".o_field_property_selection_option input"
            );
            if (inputs && inputs.length && !inputs[inputs.length - 1].value) {
                inputs[inputs.length - 1].focus();
            }
        });
    }

    /* --------------------------------------------------------
     * Public methods / Getters
     * -------------------------------------------------------- */

    /**
     * Return the current available options.
     *
     * Make a deep copy to not change original object to be able to restore
     * the old props if we discard the editing of the forma view.
     *
     * @returns {array}
     */
    get options() {
        return JSON.parse(JSON.stringify(this.props.options || []));
    }

    /**
     * Options visible by the UI, include the newly created option if needed.
     *
     * @returns {array}
     */
    get optionsVisible() {
        const options = this.options || [];
        return this.state.newOption ? [...options, this.state.newOption] : options;
    }

    /* --------------------------------------------------------
     * Event handlers
     * -------------------------------------------------------- */

    /**
     * Add a new empty selection option.
     */
    onOptionCreate() {
        this.state.newOption = [uuid(), ""];
    }

    /**
     * We changed an option label.
     *
     * @param {event} event
     * @param {integer} optionIndex
     */
    onOptionChange(event, optionIndex) {
        const target = event.target;
        const newLabel = target.value;

        if (this.options[optionIndex] && this.options[optionIndex][1] === newLabel) {
            // do not update the props if we are already up to date
            // e.g. we pressed enter already and lost focus
            return;
        }

        const options = this.optionsVisible;

        if (!newLabel || !newLabel.length) {
            // if the label is empty, remove the option
            options.splice(optionIndex, 1);
        } else {
            options[optionIndex][1] = newLabel;
        }

        const nonEmptyOptions = options.filter((option) => option[1] && option[1].length);
        this.props.onOptionsChange(nonEmptyOptions);

        if (this.state.newOption && this.state.newOption[1] && this.state.newOption[1].length) {
            // the new option has been propagated in the props
            this.state.newOption = null;
        }
    }

    /**
     * Loose focus on an option, should cancel the newly
     * created option if we didn't write on it.
     *
     * @param {event} event
     * @param {integer} optionIndex
     */
    onOptionBlur(event, optionIndex) {
        if (event.target.value && event.target.value.length) {
            // losing the focus on an non-empty option should have no effect
            return;
        }

        if (event.relatedTarget === this.addButtonRef.el) {
            // lost the focus because we click on the add button
            // if the value is empty, just ignore and cancel the event
            event.stopPropagation();
            event.preventDefault();
        } else if (optionIndex >= this.options.length) {
            // we remove the focus from the new empty option, remove it
            this.state.newOption = null;
        }
    }

    /**
     * We pressed Enter on an option, add it if it's not
     * empty and automatically create a new one.
     *
     * Navigate using the up / down arrows.
     *
     * @param {event} event
     * @param {integer} optionIndex
     */
    onOptionKeyDown(event, optionIndex) {
        if (event.key === "Enter") {
            const newLabel = event.target.value;

            if (!newLabel || !newLabel.length) {
                // press enter on an empty option, just ignore it, nothing to save
                event.stopPropagation();
                event.preventDefault();
                return;
            }

            this.onOptionChange(event, optionIndex);
            this.onOptionCreate();
        } else if (["ArrowUp", "ArrowDown"].includes(event.key)) {
            event.stopPropagation();
            event.preventDefault();

            if (event.key === "ArrowUp" && optionIndex > 0) {
                const previousInput = event.target
                    .closest(".o_field_property_selection_option")
                    .previousElementSibling.querySelector("input");
                previousInput.focus();
            } else if (event.key === "ArrowDown" && optionIndex < this.optionsVisible.length - 1) {
                const nextInput = event.target
                    .closest(".o_field_property_selection_option")
                    .nextElementSibling.querySelector("input");
                nextInput.focus();
            }
        }
    }

    /**
     * Change the default selection option.
     *
     * @param {integer} optionIndex
     */
    onOptionSetDefault(optionIndex) {
        if (!this.props.canChangeDefinition) {
            return;
        }
        const newValue = this.optionsVisible[optionIndex][0];
        this.props.onDefaultOptionChange(newValue !== this.props.default ? newValue : false);
    }

    /**
     * Ask to remove the selection option.
     *
     * @param {integer} optionIndex
     */
    onOptionDelete(optionIndex) {
        const options = this.optionsVisible;
        options.splice(optionIndex, 1);
        this.props.onOptionsChange(options);
    }
}

PropertyDefinitionSelection.template = "web.PropertyDefinitionSelection";

PropertyDefinitionSelection.props = {
    default: { type: String, optional: true },
    options: {},
    readonly: { type: Boolean, optional: true },
    canChangeDefinition: { type: Boolean, optional: true },
    onOptionsChange: { type: Function, optional: true }, // we add / remove / rename an option
    onDefaultOptionChange: { type: Function, optional: true }, // we select a default value
};

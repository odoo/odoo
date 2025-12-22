import { useService } from "@web/core/utils/hooks";
import { uuid } from "../../utils";

import { Component, useState, useRef, useEffect } from "@odoo/owl";
import { useSortable } from "@web/core/utils/sortable_owl";

export class PropertyDefinitionSelection extends Component {
    static template = "web.PropertyDefinitionSelection";
    static props = {
        default: { type: String, optional: true },
        options: {},
        readonly: { type: Boolean, optional: true },
        canChangeDefinition: { type: Boolean, optional: true },
        onOptionsChange: { type: Function, optional: true }, // we add / remove / rename an option
        onDefaultOptionChange: { type: Function, optional: true }, // we select a default value
    };

    setup() {
        this.notification = useService("notification");

        // when we create a new option, it's added in the state
        // when we have finished to edit it (blur / enter) we propagate
        // the new value in the props
        this.state = useState({
            newOption: null,
        });

        this.propertyDefinitionSelectionRef = useRef("propertyDefinitionSelection");
        this.addButtonRef = useRef("addButton");

        useEffect(() => {
            // automatically give the focus to the new option if it is empty
            if (!this.state.newOption) {
                return;
            }
            const inputs = this.propertyDefinitionSelectionRef.el.querySelectorAll(
                ".o_field_property_selection_option input"
            );
            if (inputs && inputs.length && !inputs[this.state.newOption.index].value) {
                inputs[this.state.newOption.index].focus();
            }
        });

        useSortable({
            enable: () => this.props.canChangeDefinition && !this.props.readonly,
            ref: this.propertyDefinitionSelectionRef,
            handle: ".o_field_property_selection_drag",
            elements: ".o_field_property_selection_option",
            cursor: "grabbing",
            onDrop: async ({ element, previous }) => {
                const movedOption = element.getAttribute("option-name");
                const destinationOption = previous && previous.getAttribute("option-name");
                await this.onOptionMoveTo(movedOption, destinationOption);
            },
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
        const newOption = this.state.newOption;
        if (newOption) {
            options.splice(newOption.index, 0, [newOption.name, ""]);
        }
        return options;
    }

    /* --------------------------------------------------------
     * Event handlers
     * -------------------------------------------------------- */

    /**
     * Add a new empty selection option.
     */
    onOptionCreate(index) {
        this.state.newOption = {
            index: index,
            name: uuid(),
        };
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

        if (this.state.newOption) {
            // the new option has been propagated in the props
            this.state.newOption = null;
        }
    }

    /**
     * Loose focus on an option, should cancel the newly
     * created option if we didn't write on it.
     *
     * The attribute `_ignoreBlur` can be set if we don't want to remove
     * the option if it's empty (and it will re-gain the focus at the
     * next `useEffect` call).
     *
     * @param {event} event
     * @param {integer} optionIndex
     */
    onOptionBlur(event, optionIndex) {
        if (event.target.value && event.target.value.length) {
            // losing the focus on an non-empty option should have no effect
            return;
        } else if (this._ignoreBlur) {
            this._ignoreBlur = false;
            return;
        }

        if (event.relatedTarget === this.addButtonRef.el) {
            // lost the focus because we click on the add button
            // if the value is empty, just ignore and cancel the event
            event.stopPropagation();
            event.preventDefault();
        } else if (optionIndex === this.state.newOption?.index) {
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
            this.onOptionCreate(optionIndex + 1);
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

    /**
     * Move an option after an other one.
     *
     * @param {string} from, the option to move
     * @param {string} to, the target option
     *      (null if we move the option at the first index)
     */
    onOptionMoveTo(movedOption, destinationOption) {
        this._ignoreBlur = true;

        let options = this.optionsVisible;
        // if destinationOption is null, destinationOptionIndex will be -1 which is intended
        let destinationOptionIndex = options.findIndex((option) => option[0] == destinationOption);
        const movedOptionIndex = options.findIndex((option) => option[0] == movedOption);
        if (destinationOptionIndex < movedOptionIndex) {
            // the first splice operation won't change the index (and we except it to decrease it)
            // for example if we have [A, B, C], and we move C such that it becomes [A, C, B]
            // destinationOption is A and the destination index is 0, but we need the index to be 1
            // (if the destination is after the moved option, the first splice will fix it for us)
            destinationOptionIndex++;
        }

        const activeEl = document.activeElement;
        if (
            activeEl &&
            this.propertyDefinitionSelectionRef.el.contains(activeEl) &&
            activeEl.tagName === "INPUT"
        ) {
            const optionName = activeEl
                .closest(".o_field_property_selection_option")
                .getAttribute("option-name");
            const editedOptionIndex = options.findIndex((option) => option[0] === optionName);
            // we might be editing the value and drag and drop something else just after
            options[editedOptionIndex][1] = activeEl.value;
        }

        options.splice(destinationOptionIndex, 0, options.splice(movedOptionIndex, 1)[0]);

        if (this.state.newOption) {
            const newOptionIndex = options.findIndex(
                (option) => option[0] === this.state.newOption.name
            );
            if (!options[newOptionIndex][1]?.length) {
                // if there's an empty option, fix it's index in the state
                // and do not propagate it in the props
                this.state.newOption = {
                    ...this.state.newOption,
                    index: newOptionIndex,
                };
                options = options.filter((option) => option[0] !== this.state.newOption.name);
            } else {
                this.state.newOption = null;
            }
        }

        this.props.onOptionsChange(options);
    }
}

/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { PropertyValue } from "./property_value";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { DomainSelector } from "@web/core/domain_selector/domain_selector";
import { Domain } from "@web/core/domain";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { ModelSelector } from "@web/core/model_selector/model_selector";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { useService, useOwnedDialogs } from "@web/core/utils/hooks";
import { PropertyDefinitionSelection } from "./property_definition_selection";
import { PropertyTags } from "./property_tags";
import { sprintf } from "@web/core/utils/strings";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
import { uuid } from "../../utils";

import { Component, useState, onWillUpdateProps, useEffect, useRef } from "@odoo/owl";

export class PropertyDefinition extends Component {
    setup() {
        this.orm = useService("orm");

        this.propertyDefinitionRef = useRef("propertyDefinition");
        this.addDialog = useOwnedDialogs();

        const defaultDefinition = {
            name: false,
            string: "",
            type: "char",
            default: "",
        };
        const propertyDefinition = {
            ...defaultDefinition,
            ...this.props.propertyDefinition,
        };

        this.state = useState({
            propertyDefinition: propertyDefinition,
            typeLabel: this._typeLabel(propertyDefinition.type),
            resModel: "",
            resModelDescription: "",
            matchingRecordsCount: undefined,
            propertyIndex: this.props.propertyIndex,
        });

        this._syncStateWithProps(propertyDefinition);

        this._domInputIdPrefix = uuid();

        // update the state and fetch needed information
        onWillUpdateProps((newProps) => this._syncStateWithProps(newProps.value));

        useEffect((event) => {
            // focus the property label, when we open the property definition
            if (this.labelFocused) {
                // focus it only once
                return;
            }
            this.labelFocused = true;
            const labelInput = this.propertyDefinitionRef.el.querySelectorAll("input")[0];
            if (labelInput) {
                if (this.props.isNewlyCreated) {
                    labelInput.select();
                } else {
                    labelInput.focus();
                }
            }
        });
    }

    /* --------------------------------------------------------
     * Public methods / Getters
     * -------------------------------------------------------- */

    /**
     * Return the list of property types with their labels.
     *
     * @returns {array}
     */
    get availablePropertyTypes() {
        return [
            ["char", _lt("Text")],
            ["boolean", _lt("Checkbox")],
            ["integer", _lt("Integer")],
            ["float", _lt("Decimal")],
            ["date", _lt("Date")],
            ["datetime", _lt("Date & Time")],
            ["selection", _lt("Selection")],
            ["tags", _lt("Tags")],
            ["many2one", _lt("Many2one")],
            ["many2many", _lt("Many2many")],
        ];
    }

    /**
     * Return True if the current properties is the first one in the list.
     */
    get isFirst() {
        return this.state.propertyIndex === 0;
    }

    /**
     * Return True if the current properties is the last one in the list.
     */
    get isLast() {
        return this.state.propertyIndex === this.props.propertiesSize - 1;
    }

    /**
     * Return the list of tag values, that will be selected by the PropertyTags
     * component (all existing tags because we are editing the definition).
     *
     * @returns {array}
     */
    get propertyTagValues() {
        return (this.state.propertyDefinition.tags || []).map((tag) => tag[0]);
    }

    /**
     * Return an unique ID to be used in the DOM.
     *
     * @returns {string}
     */
    getUniqueDomID(suffix) {
        return `property_definition_${this._domInputIdPrefix}_${suffix}`;
    }

    /* --------------------------------------------------------
     * Event handlers
     * -------------------------------------------------------- */

    /**
     * We changed the string of the property.
     *
     * @param {event} event
     */
    onPropertyLabelChange(event) {
        const newString = event.target.value;
        const propertyDefinition = {
            ...this.state.propertyDefinition,
            string: newString,
        };
        this.props.onChange(propertyDefinition);
        this.state.propertyDefinition = propertyDefinition;
    }

    /**
     * Pressed enter on the property label close the definition.
     *
     * @param {event} event
     */
    onPropertyLabelKeypress(event) {
        if (event.key !== 'Enter') {
            return;
        }
        this.props.close();
    }

    /**
     * We changed the default value of the property.
     *
     * @param {object} newDefault
     */
    onDefaultChange(newDefault) {
        const propertyDefinition = {
            ...this.state.propertyDefinition,
            default: newDefault,
        };
        this.props.onChange(propertyDefinition);
        this.state.propertyDefinition = propertyDefinition;
    }

    /**
     * We selected a new property type.
     *
     * @param {string} newType
     */
    onPropertyTypeChange(newType) {
        const propertyDefinition = {
            ...this.state.propertyDefinition,
            type: newType,
        };
        if (["integer", "float"].includes(newType)) {
            propertyDefinition.value = 0;
            propertyDefinition.default = 0;
        } else {
            propertyDefinition.value = false;
            propertyDefinition.default = false;
        }

        delete propertyDefinition.comodel;

        this.props.onChange(propertyDefinition);
        this.state.propertyDefinition = propertyDefinition;
        this.state.resModel = '';
        this.state.resModelDescription = '';
        this.state.typeLabel = this._typeLabel(newType);
    }

    /**
     * The model of the relational property (many2one / many2many) has been changed.
     *
     * @param {string} newModel
     */
    async onModelChange(newModel) {
        const { label, technical } = newModel;

        // if we change the model, we should reset the default value and the domain
        const modelChanged = technical !== this.state.resModel;

        this.state.resModel = technical;
        this.state.resModelDescription = label;

        const propertyDefinition = {
            ...this.state.propertyDefinition,
            comodel: technical,
            default: modelChanged ? false : this.state.propertyDefinition.default,
            value: modelChanged ? false : this.state.propertyDefinition.value,
            domain: modelChanged ? false : this.state.propertyDefinition.domain,
        };
        this.props.onChange(propertyDefinition);
        this.state.propertyDefinition = propertyDefinition;
        await this._updateMatchingRecordsCount();
    }

    /**
     * The domain of the relational property has been changed.
     *
     * @param {string} newDomain
     */
    async onDomainChange(newDomain) {
        const propertyDefinition = {
            ...this.state.propertyDefinition,
            domain: newDomain,
            default: false,
        };
        this.props.onChange(propertyDefinition);
        this.state.propertyDefinition = propertyDefinition;
        await this._updateMatchingRecordsCount();
    }

    /**
     * Open the list view of the records matching the current domain.
     */
    onButtonDomainClick() {
        this.addDialog(SelectCreateDialog, {
            title: this.env._t("Selected records"),
            noCreate: true,
            multiSelect: false,
            resModel: this.state.propertyDefinition.comodel,
            domain: new Domain(this.state.propertyDefinition.domain || "[]").toList(),
            context: this.props.context || {},
        });
    }

    /**
     * Move the current property up or down.
     *
     * @param {string} direction, either 'up' or 'down'
     */
    onPropertyMove(direction) {
        if (direction === 'up') {
            this.state.propertyIndex--;
        } else {
            this.state.propertyIndex++;
        }
        this.props.onPropertyMove(direction);
    }

    /**
     * We renamed / created / removed a selection option.
     *
     * @param {array} newOptions
     */
    onSelectionOptionChange(newOptions) {
        const propertyDefinition = {
            ...this.state.propertyDefinition,
            selection: newOptions,
        };
        this.props.onChange(propertyDefinition);
        this.state.propertyDefinition = propertyDefinition;
    }

    /**
     * We renamed / created / removed tags.
     *
     * @param {array} newTags
     */
    onTagsChange(newTags) {
        const propertyDefinition = {
            ...this.state.propertyDefinition,
            tags: newTags,
        };
        this.props.onChange(propertyDefinition);
        this.state.propertyDefinition = propertyDefinition;
    }

    /**
     * We activate / deactivate the property in the kanban view.
     *
     * @param {boolean} newValue
     */
    onViewInKanbanChange(newValue) {
        const propertyDefinition = {
            ...this.state.propertyDefinition,
            view_in_kanban: newValue,
        };
        this.props.onChange(propertyDefinition);
        this.state.propertyDefinition = propertyDefinition;
    }

    /* --------------------------------------------------------
     * Private methods
     * -------------------------------------------------------- */

    /**
     * The property value changed (e.g. we discard a form view editing).
     * Re-update the state with the new props.
     *
     * @param {object} propertyDefinition
     */
    async _syncStateWithProps(propertyDefinition) {
        const newModel = propertyDefinition.comodel;
        const currentModel = this.state.resModel;

        this.state.propertyDefinition = propertyDefinition;
        this.state.resModel = propertyDefinition.comodel;
        this.state.typeLabel = this._typeLabel(propertyDefinition.type);
        this.state.resModel = newModel;

        if (newModel && newModel !== currentModel) {
            // retrieve the model id and the model description from it's name
            // "res.partner" => (5, "Contact")
            try {
                const result = await this.orm.call("ir.model", "display_name_for", [[newModel]]);
                if (!result || !result.length) {
                    return;
                }
                this.state.resModelDescription = result[0].display_name;
            } catch (_) {
                // can not read the ir.model
                this.state.resModelDescription = sprintf(
                    _lt('You do not have access to the model "%s".'),
                    newModel
                );
            }

            await this._updateMatchingRecordsCount();
        } else if (!newModel) {
            this.state.resModelDescription = "";
        }
    }

    /**
     * Update the number of records that match the current domain.
     */
    async _updateMatchingRecordsCount() {
        if (this.state.resModel && this.state.resModel.length) {
            const domainList = new Domain(this.state.propertyDefinition.domain || "[]").toList();

            const result = await this.orm.call(
                this.state.propertyDefinition.comodel,
                "search_count",
                [domainList]
            );

            this.state.matchingRecordsCount = result;
        } else {
            this.state.matchingRecordsCount = undefined;
        }
    }

    /**
     * Return the property label corresponding to the property type.
     *
     * @param {string} propertyType
     * @returns {string}
     */
    _typeLabel(propertyType) {
        const allTypes = this.availablePropertyTypes;
        return allTypes.find((type) => type[0] === propertyType)[1];
    }
}

PropertyDefinition.template = "web.PropertyDefinition";
PropertyDefinition.components = {
    CheckBox,
    DomainSelector,
    Dropdown,
    DropdownItem,
    PropertyValue,
    Many2XAutocomplete,
    ModelSelector,
    PropertyDefinitionSelection,
    PropertyTags,
};
PropertyDefinition.props = {
    readonly: { type: Boolean, optional: true },
    canChangeDefinition: { type: Boolean, optional: true },
    checkDefinitionWriteAccess: { type: Function, optional: true },
    propertyDefinition: { optional: true },
    hideKanbanOption: { type: Boolean, optional: true },
    context: { type: Object },
    isNewlyCreated: { type: Boolean, optional: true },
    // index and number of properties, to hide the move arrows when needed
    propertyIndex: { type: Number },
    propertiesSize: { type: Number },
    // events
    onChange: { type: Function, optional: true },
    onDelete: { type: Function, optional: true },
    onPropertyMove: { type: Function, optional: true },
    // prop needed by the popover service
    close: { type: Function, optional: true },
};

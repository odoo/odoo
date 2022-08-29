/** @odoo-module **/

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { DateTimePicker, DatePicker } from "@web/core/datepicker/datepicker";
import { Domain } from "@web/core/domain";
import {
    Many2XAutocomplete,
    useOpenMany2XRecord,
} from "@web/views/fields/relational_utils";
import { useService } from "@web/core/utils/hooks";
import { TagsList } from "@web/views/fields/many2many_tags/tags_list";
import { m2oTupleFromData } from "@web/views/fields/many2one/many2one_field";
import { PropertyTags } from "./property_tags";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import {
    formatFloat,
    formatInteger,
    formatMany2one,
} from "@web/views/fields/formatters";
import { formatDate, formatDateTime } from "@web/core/l10n/dates";

const { Component } = owl;
const { DateTime } = luxon;

// Formats to stringify the date / datetime in the JSON.
// It's important to have the year first, then the day,
// etc... in UTC, to be able to search on them.
const DEFAULT_SERVER_DATETIME_FORMAT = "yyyy-LL-dd HH:mm:ss";
const DEFAULT_SERVER_DATE_FORMAT = "yyyy-LL-dd";

/**
 * Represent one property value.
 * Supports many types and instantiates the appropriate component for it.
 * - Text
 * - Integer
 * - Boolean
 * - Selection
 * - Datetime & Date
 * - Many2one
 * - Many2many
 * - Tags
 * - ...
 */
export class PropertyValue extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.openMany2X = useOpenMany2XRecord({
            resModel: this.props.model,
            activeActions: {
                canCreate: false,
                canCreateEdit: false,
                canWrite: true,
            },
            isToMany: false,
            onRecordSaved: async (record) => {
                if (!record) {
                    return;
                }
                // maybe the record display name has changed
                await record.load();
                const recordData = m2oTupleFromData(record.data);
                await this.onValueChange([
                    { id: recordData[0], name: recordData[1] },
                ]);
            },
            fieldString: this.props.string,
        });
    }

    /* --------------------------------------------------------
     * Public methods / Getters
     * -------------------------------------------------------- */

    /**
     * Return the value of the current property,
     * that will be used by the sub-components.
     *
     * @returns {object}
     */
    get propertyValue() {
        const value = this.props.value;

        if (this.props.type === "float") {
            // force to show at least 1 digit, even for integers
            return value;
        } else if (this.props.type === "datetime") {
            if (typeof value === "string") {
                // convert the datetime from the UTC format to the current timezone
                const datetimeValue = DateTime.fromFormat(
                    value + " +00:00",
                    DEFAULT_SERVER_DATETIME_FORMAT + " Z"
                );
                return datetimeValue.invalid ? false : datetimeValue;
            }
            return value instanceof DateTime ? value : false;
        } else if (this.props.type === "date") {
            if (typeof value === "string") {
                const datetimeValue = DateTime.fromFormat(
                    value + " +00:00",
                    DEFAULT_SERVER_DATE_FORMAT + " Z"
                );
                return datetimeValue.invalid ? false : datetimeValue;
            }
            return value instanceof DateTime ? value : false;
        } else if (this.props.type === "boolean") {
            return !!value;
        } else if (this.props.type === "selection") {
            const options = this.props.selection || [];
            const option = options.find((option) => option[0] === value);
            return option && option.length === 2 && option[0] ? option[0] : "";
        } else if (this.props.type === "many2one") {
            return !value || value.length !== 2 || !value[0] ? false : value;
        } else if (this.props.type === "many2many") {
            if (!value || !value.length) {
                return [];
            }

            // Convert to TagList component format
            return value.map((many2manyValue) => {
                return {
                    id: many2manyValue[0],
                    text: many2manyValue[1],
                    onClick: async () =>
                        await this._openRecord(
                            this.props.comodel,
                            many2manyValue[0]
                        ),
                    onDelete:
                        !this.props.readonly &&
                        (() => this.onMany2manyDelete(many2manyValue[0])),
                    colorIndex: 0,
                };
            });
        } else if (this.props.type === "tags") {
            return value || [];
        }

        return value;
    }

    /**
     * Return the model domain (related to many2one and many2many properties).
     *
     * @returns {array}
     */
    get propertyDomain() {
        if (!this.props.domain || !this.props.domain.length) {
            return [];
        }
        return new Domain(this.props.domain).toList();
    }

    /**
     * Formatted value displayed in readonly mode.
     *
     * @returns {string}
     */
    get displayValue() {
        const value = this.propertyValue;

        if (this.props.type === "many2one" && value && value.length === 2) {
            return formatMany2one(value);
        } else if (!value) {
            return false;
        } else if (this.props.type === "datetime" && value) {
            return formatDateTime(value);
        } else if (this.props.type === "date" && value) {
            return formatDate(value);
        } else if (this.props.type === "selection") {
            return this.props.selection.find(
                (option) => option[0] === value
            )[1];
        } else if (this.props.type === "float") {
            return formatFloat(value);
        } else if (this.props.type === "integer") {
            return formatInteger(value);
        }
        return value.toString();
    }

    /* --------------------------------------------------------
     * Event handlers
     * -------------------------------------------------------- */

    /**
     * Parse the value received by the sub-components and trigger an onChange event.
     *
     * @param {object} newValue
     */
    async onValueChange(newValue) {
        if (this.props.type === "datetime") {
            if (typeof newValue === "string") {
                newValue = DateTime.fromISO(newValue);
            }
            newValue = newValue
                .toUTC()
                .toFormat(DEFAULT_SERVER_DATETIME_FORMAT);
        } else if (this.props.type === "date") {
            if (typeof newValue === "string") {
                newValue = DateTime.fromISO(newValue);
            }
            newValue = newValue.toFormat(DEFAULT_SERVER_DATE_FORMAT);
        } else if (this.props.type === "integer") {
            newValue = parseInt(newValue) || 0;
        } else if (this.props.type === "float") {
            newValue = parseFloat(newValue) || 0;
        } else if (["many2one", "many2many"].includes(this.props.type)) {
            // {id: 5, name: 'Demo'} => [5, 'Demo']
            newValue =
                newValue && newValue.length && newValue[0].id
                    ? [newValue[0].id, newValue[0].name]
                    : false;

            if (newValue && newValue[0] && newValue[1] === undefined) {
                // The "Search More" option in the Many2XAutocomplete component
                // only return the record ID, and not the name. But we need to name
                // in the component props to be able to display it.
                // Make a RPC call to resolve the display name of the record.
                newValue = await this._nameGet(newValue[0]);
            }

            if (this.props.type === "many2many" && newValue) {
                // add the record in the current many2many list
                const currentValue = this.props.value || [];
                const recordId = newValue[0];
                const exists = currentValue.find((rec) => rec[0] === recordId);
                if (exists) {
                    return;
                }
                newValue = [...currentValue, newValue];
            }
        }

        // trigger the onchange event to notify the parent component
        this.props.onChange(newValue);
    }

    /**
     * Open the form view of the current record.
     *
     * @param {event} event
     */
    async onMany2oneClick(event) {
        if (this.props.readonly) {
            event.stopPropagation();
            await this._openRecord(this.props.comodel, this.propertyValue[0]);
        }
    }

    /**
     * Open the current many2one record form view in a modal.
     */
    onExternalLinkClick() {
        return this.openMany2X({
            resId: this.propertyValue[0],
            forceModel: this.props.comodel,
            context: this.context,
        });
    }

    /**
     * Removed a record from the many2many list.
     *
     * @param {integer} many2manyId
     */
    onMany2manyDelete(many2manyId) {
        // deep copy
        const currentValue = JSON.parse(JSON.stringify(this.props.value || []));
        const newValue = currentValue.filter(
            (value) => value[0] !== many2manyId
        );
        this.props.onChange(newValue);
    }

    /**
     * Ask to create a record from a relational property.
     *
     * @param {string} name
     * @param {object} params
     */
    async onQuickCreate(name, params = {}) {
        if (params.triggeredOnBlur) {
            this.onValueChange(false);
            return;
        }
        const result = await this.orm.call(
            this.props.comodel,
            "name_create",
            [name],
            { context: this.props.context }
        );
        this.onValueChange([{ id: result[0], name: result[1] }]);
    }

    /* --------------------------------------------------------
     * Private methods
     * -------------------------------------------------------- */

    /**
     * Open the form view of the given record id / model.
     *
     * @param {string} recordModel
     * @param {integer} recordId
     */
    async _openRecord(recordModel, recordId) {
        const action = await this.orm.call(
            recordModel,
            "get_formview_action",
            [[recordId]],
            { context: this.props.context }
        );

        this.action.doAction(action);
    }

    /**
     * Get the display name of the given record.
     * Model is taken from the current selected model.
     *
     * @param {string} recordId
     * @returns {array} [record id, record name]
     */
    async _nameGet(recordId) {
        const result = await this.orm.call(
            this.props.comodel,
            "name_get",
            [[recordId]],
            { context: this.props.context }
        );
        return result[0];
    }
}

PropertyValue.template = "web.PropertyValue";

PropertyValue.components = {
    Dropdown,
    DropdownItem,
    CheckBox,
    DateTimePicker,
    DatePicker,
    Many2XAutocomplete,
    TagsList,
    AutoComplete,
    PropertyTags,
};

PropertyValue.props = {
    type: { type: String, optional: true },
    comodel: { type: String, optional: true },
    domain: { type: String, optional: true },
    string: { type: String, optional: true },
    value: { optional: true },
    context: { type: Object },
    readonly: { type: Boolean, optional: true },
    canChangeDefinition: { type: Boolean, optional: true },
    selection: { type: Array, optional: true },
    tags: { type: Array, optional: true },
    onChange: { type: Function, optional: true },
    onTagsChange: { type: Function, optional: true },
};

import { Component, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Property } from "@web_studio/client_action/view_editor/property/property";
import {
    fieldsToChoices,
    getWowlFieldWidgets,
} from "@web_studio/client_action/view_editor/editors/utils";
import {
    FIELD_TYPE_ATTRIBUTES,
    COMPUTED_DISPLAY_OPTIONS,
} from "@web_studio/client_action/view_editor/interactive_editor/properties/type_widget_properties/type_specific_and_computed_properties";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

export class TypeWidgetProperties extends Component {
    static template =
        "web_studio.ViewEditor.InteractiveEditorProperties.Field.TypeWidgetProperties";
    static components = { Property };
    static props = {
        node: { type: Object },
        onChangeAttribute: { type: Function },
    };

    setup() {
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.attributes = useState({
            field: [],
            selection: [],
            boolean: [],
            domain: [],
            number: [],
            string: [],
            digits: [],
        });

        onWillStart(async () => {
            await this.computeAttributesList(this.props);
        });

        onWillUpdateProps(async (nextProps) => {
            await this.computeAttributesList(nextProps);
        });
    }

    async computeAttributesList(props) {
        this.attributesForCurrentTypeAndWidget = this.getAttributesForCurrentTypeAndWidget(props);
        await this.groupAttributesPerType(props);
    }

    async groupAttributesPerType(props) {
        this.attributes.field = await this.getAttributesOfTypeField(props);
        this.attributes.selection = this.getWidgetAttributes("selection", props);
        this.attributes.boolean = this.getWidgetAttributes("boolean", props);
        this.attributes.domain = this.getWidgetAttributes("domain", props);
        this.attributes.number = this.getWidgetAttributes("number", props);
        this.attributes.string = this.getWidgetAttributes("string", props);
        this.attributes.digits = this.getWidgetAttributes("digits", props);
    }

    async getAttributesOfTypeField(props) {
        const fieldAttributes = this.getWidgetAttributes("field", props);
        if (fieldAttributes.length) {
            const fields = Object.entries(this.env.viewEditorModel.fields).map(([key, value]) => {
                return {
                    ...value,
                    name: value.name || key,
                };
            });
            // for each attribute looking for a field, compute the choices to display in the SelectMenu
            await Promise.all(
                fieldAttributes.map(async (attribute) => {
                    const choices = await this.getFieldChoices(attribute, fields);
                    if (
                        this.props.node.field?.type === "monetary" &&
                        attribute.name === "currency_field"
                    ) {
                        attribute.isRequired = true;
                    }
                    attribute.choices = choices;
                    this.getOptionObj(attribute.name).choices = choices;
                })
            );
            return fieldAttributes;
        }
        return [];
    }

    getSupportedOptionsAndAttributes(props) {
        const widgetName = this.isField
            ? props.node.attrs?.widget || props.node.field?.type
            : props.node.attrs.name;
        const itemsRegistry = registry.category(this.isField ? "fields" : "view_widgets").content;
        const widgetDescription =
            itemsRegistry[this.env.viewEditorModel.viewType + "." + widgetName] ||
            itemsRegistry[widgetName];
        return [
            // tag the attributes as the edition changes the attribute value instead of a value from the option attribute.
            ...(widgetDescription?.[1].supportedAttributes || []).map((e) => ({
                ...e,
                isAttribute: true,
            })),
            ...(widgetDescription?.[1].supportedOptions || []),
        ];
    }

    /**
     * @returns the list of available widgets for the current node
     */
    get widgetChoices() {
        const widgets = getWowlFieldWidgets(
            this.props.node.field.type,
            this.props.node.attrs.widget,
            [],
            this.env.debug
        );
        return {
            choices: widgets.map(([value, label]) => {
                label = label ? label : "";
                return {
                    label: `${label} (${value})`.trim(),
                    value,
                };
            }),
        };
    }

    /**
     * @returns the list of attributes available depending the type of field,
     * as well the current widget selected. For a widget node, there is no
     * concept of type, we simply read what supported options and attributes
     * are on the node
     */
    _getAttributesForCurrentTypeAndWidget(props) {
        if (!props.node.field) {
            // node is a widget, and there is no 'type' on such elements
            return JSON.parse(JSON.stringify(this.getSupportedOptionsAndAttributes(props)));
        }

        this.isField = true;

        const fieldType = props.node.field.type;
        const { viewType } = this.env.viewEditorModel;

        const fieldCommonViewsProperties = FIELD_TYPE_ATTRIBUTES[fieldType]?.common || [];
        const fieldSpecificViewProperties = FIELD_TYPE_ATTRIBUTES[fieldType]?.[viewType] || [];

        return [
            ...fieldCommonViewsProperties.map((e) => ({ ...e, isAttribute: true })),
            ...fieldSpecificViewProperties.map((e) => ({ ...e, isAttribute: true })),
            // create a deep copy of the options description to avoid modifying the original objects
            ...JSON.parse(JSON.stringify(this.getSupportedOptionsAndAttributes(props))),
        ];
    }

    getAttributesForCurrentTypeAndWidget(props) {
        const _attributes = this._getAttributesForCurrentTypeAndWidget(props);
        _attributes.forEach((property) => {
            if (COMPUTED_DISPLAY_OPTIONS[property.name]) {
                const dependentOption = COMPUTED_DISPLAY_OPTIONS[property.name];
                const superOption = _attributes.find((o) => o.name === dependentOption.superOption);
                property.isSubOption = true;
                if (!superOption.subOptions) {
                    superOption.subOptions = [];
                }
                if (!superOption.subOptions.includes(property.name)) {
                    // only add the subOption if not already present
                    superOption.subOptions.push(property.name);
                }
            }
        });
        return _attributes;
    }

    getOptionObj(optionName) {
        return this.attributesForCurrentTypeAndWidget.find((o) => o.name === optionName);
    }

    isAttributeReadonly(attribute) {
        if ("isReadonly" in attribute) {
            return attribute.isReadonly;
        }
        if (this.props.node.field?.type === "monetary" && attribute.name === "currency_field") {
            return !this.props.node.field.manual;
        }
    }

    /**
     * @param {string} type of the attribute (eg. "string", "boolean" )
     * @returns only the given type of attributes for the current field node
     */
    getWidgetAttributes(type, props) {
        return this.attributesForCurrentTypeAndWidget
            .filter((attribute) => attribute.type === type)
            .map((attribute) => {
                if (attribute.isAttribute) {
                    return this.getPropertyFromAttributes(attribute, props);
                }
                return this.getPropertyFromOptions(attribute, props);
            })
            .filter((attribute) => attribute !== undefined);
    }

    async getFieldChoices(attribute, fields) {
        let availableFields = fields;
        // Specific code to filter available fields to display is handled here as supportedOptions
        // is a generic description and don't allow to describe the full spec of an option
        if (attribute.name === "fold_field") {
            if (this.env.viewEditorModel.activeNode.field.type === "selection") {
                // fold_field is only relevant with relational status with its own model
                attribute.isInvisible = true;
                return [];
            }
            const fields = await this.orm.call(
                this.env.viewEditorModel.activeNode.field.relation,
                "fields_get"
            );
            availableFields = Object.values(fields);
        } else if (attribute.name === "currency_field") {
            availableFields = availableFields.filter((f) => f.relation === "res.currency");
        }
        return fieldsToChoices(
            availableFields,
            attribute.availableTypes,
            (f) => f.name !== this.env.viewEditorModel.activeNode.attrs.name
        );
    }

    /**
     * Compute the property and its value from one or more attributes on the node
     */
    getPropertyFromAttributes(property, props) {
        let value;
        value = props.node.attrs[property.name];
        if (property.getValue) {
            const attrs = props.node.attrs || {};
            const field = props.node.field || {};
            value = property.getValue({ attrs, field });
        }
        if (value === undefined && property.default) {
            value = property.default;
        }
        return {
            ...property,
            value,
        };
    }

    /**
     * Compute the property and its value from the `options` attribute on the node
     */
    getPropertyFromOptions(property, props) {
        let value;
        if (COMPUTED_DISPLAY_OPTIONS[property.name]) {
            // The display of this property must be computed from the value of the corresponding super option
            const dependentOption = COMPUTED_DISPLAY_OPTIONS[property.name];
            const superOption = this.getOptionObj(dependentOption.superOption);
            const superValue = this.getPropertyFromOptions(superOption, props).value;
            if (dependentOption.getReadonly) {
                property.isReadonly = dependentOption.getReadonly(superValue);
            }
            if (dependentOption.getValue) {
                property.value = dependentOption.getValue(superValue);
                if (property.isReadonly) {
                    // The property value cannot be edited, return the computed value directly
                    return property;
                }
            }
            if (dependentOption.getInvisible) {
                property.isInvisible = dependentOption.getInvisible(superValue);
            }
        }
        value = props.node.attrs.options?.[property.name];
        if (property.type === "string" && value && typeof value !== "string") {
            value = JSON.stringify(value);
        }
        if (property.type === "boolean" && value !== undefined) {
            value = !!value;
        }
        if (value === undefined && property.default) {
            value = property.default;
        }
        if (property.name === "currency_field" && !value) {
            value = props.node.field.currency_field;
        }
        return {
            ...property,
            value,
        };
    }

    getSelectValue(value) {
        return typeof value === "object" ? JSON.stringify(value) : value;
    }

    async onChangeCurrency(value) {
        const proms = [];
        if (this.props.node.field.manual) {
            proms.push(
                rpc("/web_studio/set_currency", {
                    model_name: this.env.viewEditorModel.resModel,
                    field_name: this.props.node.field.name,
                    value,
                })
            );
        } else {
            proms.push(Promise.resolve(false));
        }

        if (this.env.viewEditorModel.fieldsInArch.includes(value)) {
            // If the currency field is in the view, just alter the
            // reactives and return.
            const [currencyChanged] = await Promise.all(proms);
            if (currencyChanged) {
                this.env.viewEditorModel.fields[this.props.node.field.name]["currency_field"] =
                    value;
                // alter the value of the currently selected currency manually to trigger a re-render of the SelectMenu
                // with the correct value since we don't pass through doOperations from the ViewEditorModel
                this.attributes.field = this.attributes.field.map((e) => {
                    if (e.name === "currency_field") {
                        e.value = value;
                    }
                    return e;
                });
            }
            return;
        }

        const currencyNode = {
            tag: "field",
            attrs: { name: value },
        };

        const operation = {
            node: currencyNode,
            target: this.env.viewEditorModel.getFullTarget(
                this.env.viewEditorModel.activeNodeXpath
            ),
            position: "after",
            type: "add",
        };

        proms.push(this.env.viewEditorModel.doOperation(operation));
        const [currencyChanged] = await Promise.all(proms);
        if (currencyChanged) {
            this.env.viewEditorModel.fields[this.props.node.field.name]["currency_field"] = value;
        }
    }

    onChangeWidget(value) {
        return this.props.onChangeAttribute(value, "widget");
    }

    async onChangeProperty(value, name) {
        if (
            ["show_seconds", "show_time"].includes(name) &&
            !value &&
            this.props.node.field.type === "datetime" &&
            !this.props.node.attrs.widget
        ) {
            this.onChangeWidget("datetime");
        } else if (name === "currency_field" && this.props.node.field.type === "monetary") {
            await this.onChangeCurrency(value);
            if (!this.props.node.attrs.options?.[name]) {
                return;
            }
            value = ""; // the currency_field arch option will be deleted
        }

        const options = { ...this.props.node.attrs.options };
        const isDateRange = this.props.node.attrs.widget === "daterange";
        if (
            isDateRange &&
            value &&
            ((name === "start_date_field" && options["end_date_field"]) ||
                (name === "end_date_field" && options["start_date_field"]))
        ) {
            return this.dialog.add(AlertDialog, {
                body: _t(
                    "You can't select the 'Start date field' and 'End date field' at the same time"
                ),
            });
        }

        const currentProperty = this.getOptionObj(name);
        if (currentProperty.isAttribute) {
            return this.props.onChangeAttribute(value, name);
        }
        if (value || currentProperty.type === "boolean") {
            if (currentProperty.type === "digits") {
                // The digits options is composed of two integers.
                // The first one is unused and the second one is passed to `toFixed`
                // from `formatFloat`. It should be an integer between 0 and 20.
                value = Number(value);
                if (!Number.isInteger(value) || value < 0 || value > 20) {
                    return;
                }
                options[name] = [value * 2, value];
            } else if (["[", "{"].includes(value[0]) || !isNaN(value)) {
                options[name] = JSON.parse(value);
            } else if (currentProperty.type === "number") {
                options[name] = Number(value);
            } else {
                options[name] = value;
            }
        } else {
            delete options[name];
        }
        this.props.onChangeAttribute(JSON.stringify(options), "options");
    }
}

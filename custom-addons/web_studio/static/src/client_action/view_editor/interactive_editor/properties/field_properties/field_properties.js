/** @odoo-module */

import { Component, onWillStart, onWillUpdateProps, useState, toRaw } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Property } from "@web_studio/client_action/view_editor/property/property";
import { SelectionContentDialog } from "@web_studio/client_action/view_editor/interactive_editor/field_configuration/selection_content_dialog";
import { useService } from "@web/core/utils/hooks";
import { LimitGroupVisibility } from "../limit_group_visibility/limit_group_visibility";
import { TypeWidgetProperties } from "./type_widget_properties";
import { SidebarPropertiesToolbox } from "../sidebar_properties_toolbox/sidebar_properties_toolbox";
import { ModifiersProperties } from "../modifiers/modifiers_properties";
import { useEditNodeAttributes } from "@web_studio/client_action/view_editor/view_editor_model";

class TechnicalName extends Component {
    static props = {
        node: { type: Object },
    };
    static template = "web_studio.ViewEditor.InteractiveEditorProperties.Field.TechnicalName";
    static components = { Property };

    setup() {
        this.renameField = (value) => {
            return this.env.viewEditorModel.renameField(
                this.props.node.attrs.name,
                `x_studio_${value}`,
                { autoUnique: false }
            );
        };
    }

    get canEdit() {
        return (
            this.env.debug && this.env.viewEditorModel.isFieldRenameable(this.props.node.attrs.name)
        );
    }

    get fieldName() {
        const fName = this.props.node.attrs.name;
        if (this.canEdit) {
            return fName.split("x_studio_")[1];
        }
        return fName;
    }
}

export class FieldProperties extends Component {
    static template = "web_studio.ViewEditor.InteractiveEditorProperties.Field";
    static props = {
        node: { type: Object },
        availableOptions: { type: Array, optional: true },
    };
    static components = {
        LimitGroupVisibility,
        Property,
        TechnicalName,
        TypeWidgetProperties,
        SidebarPropertiesToolbox,
        ModifiersProperties,
    };

    setup() {
        this.dialog = useService("dialog");
        this.rpc = useService("rpc");
        this.state = useState({});
        this.editNodeAttributes = useEditNodeAttributes();
        onWillStart(async () => {
            if (this.canShowDefaultValue) {
                this.state.defaultValue = await this.getDefaultValue(this.props.node);
            }
        });

        onWillUpdateProps(async (nextProps) => {
            if (this._canShowDefaultValue(nextProps.node)) {
                this.state.defaultValue = await this.getDefaultValue(nextProps.node);
            }
        });
    }

    get viewEditorModel() {
        return this.env.viewEditorModel;
    }

    async onChangeFieldString(value) {
        if (this.viewEditorModel.isFieldRenameable(this.props.node.field.name) && value) {
            return this.viewEditorModel.renameField(this.props.node.attrs.name, value, {
                label: value,
            });
        } else {
            const operation = {
                new_attrs: { string: value },
                type: "attributes",
                position: "attributes",
                target: this.viewEditorModel.getFullTarget(this.viewEditorModel.activeNodeXpath),
            };
            // FIXME: the python API is messy: we need to send node, which is the same as target since
            // we are editing the target's attributes, to be able to modify the python field's string
            operation.node = operation.target;
            return this.viewEditorModel.doOperation(operation);
        }
    }

    onChangeAttribute(value, name) {
        return this.editNodeAttributes({ [name]: value });
    }

    onChangeDefaultValue(value) {
        this.rpc("/web_studio/set_default_value", {
            model_name: this.env.viewEditorModel.resModel,
            field_name: this.props.node.field.name,
            value,
        });
    }

    async getDefaultValue(node) {
        const defaultValueObj = await this.rpc("/web_studio/get_default_value", {
            model_name: this.env.viewEditorModel.resModel,
            field_name: node.field.name,
        });
        return defaultValueObj.default_value;
    }

    get optionalVisibilityChoices() {
        return {
            choices: [
                { label: _t("Show by default"), value: "show" },
                { label: _t("Hide by default"), value: "hide" },
            ],
        };
    }

    get defaultValuesInputType() {
        const node = this.props.node;
        return node.attrs?.widget === "statusbar"
            ? "selection"
            : node.attrs.widget || node.field.type;
    }

    get defaultValuesChoices() {
        if (this.props.node.field.selection) {
            return {
                choices: this.props.node.field.selection.map(([value, label]) => {
                    return {
                        label,
                        value,
                    };
                }),
            };
        }
        return undefined;
    }

    _canShowDefaultValue(node) {
        if (/^(in_group_|sel_groups_)/.test(node.attrs.name)) {
            return false;
        }
        return !["image", "many2many", "many2one", "binary"].includes(node.field.type);
    }

    get canShowDefaultValue() {
        return this._canShowDefaultValue(this.props.node);
    }

    get canEditSelectionChoices() {
        return this.props.node.field.manual && this.props.node.field.type === "selection";
    }

    /**
     * @param {string} name of the attribute
     * @returns if this attribute supported in the current view
     */
    isAttributeSupported(name) {
        return this.props.availableOptions?.includes(name);
    }

    editSelectionChoices() {
        const field = this.props.node.field;
        this.dialog.add(SelectionContentDialog, {
            defaultChoices: toRaw(field).selection.map((s) => [...s]),
            onConfirm: async (choices) => {
                const result = await this.rpc("/web_studio/edit_field", {
                    model_name: this.env.viewEditorModel.resModel,
                    field_name: field.name,
                    values: { selection: JSON.stringify(choices) },
                    force_edit: false,
                });
                let reflectChanges = !result;
                if (result && result.records_linked) {
                    reflectChanges = false;
                    await new Promise((resolve) => {
                        this.dialog.add(ConfirmationDialog, {
                            body:
                                result.message ||
                                _t("Are you sure you want to remove the selection values?"),
                            confirm: async () => {
                                await this.rpc("/web_studio/edit_field", {
                                    model_name: this.env.viewEditorModel.resModel,
                                    field_name: field.name,
                                    values: { selection: JSON.stringify(choices) },
                                    force_edit: true,
                                });
                                reflectChanges = true;
                                resolve();
                            },
                            cancel: () => resolve(),
                        });
                    });
                }
                if (reflectChanges) {
                    field.selection = choices;
                }
            },
        });
    }
}

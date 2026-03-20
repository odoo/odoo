import { registry } from "@web/core/registry";
import { exprToBoolean } from "@web/core/utils/strings";
import { _t } from "@web/core/l10n/translation";
import { PropertiesField } from "./properties_field";

export class PropertiesDefinitionField extends PropertiesField {
    static template = "web.PropertiesDefinitionField";

    setup() {
        super.setup();
        this.state.isInEditMode = this.definitionRecordId;
    }

    /*
    * handle the case when the add property is used even though there are 0 existing ones
     */
    async onPropertyCreateEmpty() {
        const recordSaved = await this.props.record.save();
        if (this.props.readonly || this.state.isInEditMode || !recordSaved) {
            return;
        }
        let canChangeDefinition = this.state.canChangeDefinition;
        if (!canChangeDefinition) {
            canChangeDefinition = await this.checkDefinitionWriteAccess();
            if (!canChangeDefinition) {
                this.notification.add(this._getPropertyEditWarningText(), {
                    type: "warning",
                });
            }
        }
        const isInEditMode = canChangeDefinition && !this.props.readonly;
        this.state.canChangeDefinition = !!canChangeDefinition;
        this.state.isInEditMode = isInEditMode;
        if (isInEditMode && this.propertiesList.length === 0) {
            const newName = this.generatePropertyName("char");
            const propertiesDefinitions = [{
                name: newName,
                string: _t("Property 1"),
                type: "char",
            }];
            this.initialValues[newName] = { name: newName, type: "char" };
            this.openPropertyDefinition = newName;
            await this.props.record.update({ [this.props.name]: propertiesDefinitions });
        }
    }

    get displayAddWorksheetPropertyButton() {
        return this.propertiesList.length == 0 && !this.state.isInEditMode
    }

    /*
     * The functions below are all overwrite from the PropertiesField component to adapt either some value and some
     * behavior. As in our case, the parent model does not exists and is actually the current active model.
     */
    get definitionRecordId() {
        return this.props.record.data.id;
    }

    get definitionRecordModel() {
        return this.props.record.model.config.resModel;
    }

    _getClosestField() {
        return this.propertiesRef.el.closest(".o_field_properties_definition");
    }

    _getDisplayData() {
        return {
            'parentName': this.props.record.model.config.resModel,
            'parentFieldLabel': "model",
        }
    }

    _onDeleteConfirm(propertiesDefinitions, propertyName) {
        const definition = propertiesDefinitions.find((property) => property.name === propertyName);
        const index = propertiesDefinitions.indexOf(definition);
        propertiesDefinitions.splice(index, 1);
    }

    _getNewPropertyDefinition(newName, count) {
        return {
            name: newName,
            string: _t("Property %s", count + 1),
            type: "char",
        }
    }

    _regeneratePropertyName(newDefinition, oldDefinition) {
        super._regeneratePropertyName(newDefinition, oldDefinition);
        for (const key in newDefinition) {
            if (['value', 'definition_changed'].includes(key)) {
                delete newDefinition[key]
            }
        }
    }

    // In this case, we do not want to add the 'value' parameter, as this is a definition, and not a property
    _toggleSeparatorValue(property, forceState) { }

    _isFolded(property) {
        return false;
    }

    _isPropertyDefinitionWidget() {
        return true;
    }
}

export const propertiesDefinitionField = {
    component: PropertiesDefinitionField,
    displayName: _t("Properties Definition"),
    supportedTypes: ["properties_definition"],
    extractProps({ attrs }, dynamicInfo) {
        return {
            context: dynamicInfo.context,
            columns: parseInt(attrs.columns || "1"),
            editMode: exprToBoolean(attrs.editMode),
        };
    },
};

registry.category("fields").add("properties_definition", propertiesDefinitionField);

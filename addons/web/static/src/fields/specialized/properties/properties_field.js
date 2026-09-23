// @ts-check
/** @odoo-module native */

import { onWillStart, onWillUpdateProps, useEffect, useRef, useState } from "@odoo/owl";
import { Dropdown } from "@web/components/dropdown/dropdown";
import { DropdownItem } from "@web/components/dropdown/dropdown_item";
import { ModelEvent } from "@web/core/events";
import { reposition } from "@web/core/position/utils";
import { _t } from "@web/core/translation";
import { user } from "@web/core/user";
import { exprToBoolean, uuid } from "@web/core/utils/format/strings";
import { useBus, useService } from "@web/core/utils/hooks";
import { registerField } from "@web/fields/_registry";
import { FieldComponent } from "@web/fields/field_component";
import { archAttribute } from "@web/fields/field_options";
import { useRecordObserver } from "@web/fields/hooks/record_observer";
import { standardFieldProps } from "@web/fields/standard_field_props";
import { ConfirmationDialog } from "@web/ui/dialog";
import { usePopover } from "@web/ui/popover";

import {
    findEnclosingSeparator,
    groupProperties,
    moveGroupTo,
    movePropertyByOffset,
    movePropertyTo,
} from "./properties_layout.js";
import { usePropertiesSortable } from "./properties_sortable_hook.js";
import { PropertyDefinition } from "./property_definition.js";
import { PropertyValue } from "./property_value.js";

export class PropertiesField extends FieldComponent {
    static template = "web.PropertiesField";
    static components = {
        Dropdown,
        DropdownItem,
        PropertyDefinition,
        PropertyValue,
    };
    static props = {
        ...standardFieldProps,
        context: { type: Object, optional: true },
        columns: {
            type: Number,
            optional: true,
            validate: (columns) => [1, 2].includes(columns),
        },
        editMode: { type: Boolean, optional: true },
    };

    setup() {
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.dialogService = useService("dialog");
        this.popover = usePopover(PropertyDefinition, {
            closeOnClickAway: this.checkPopoverClose,
            class: "o_property_field_popover",
            position: "right",
            onClose: () => this.onCloseCurrentPopover?.(),
            fixedPosition: true,
            arrow: false,
            setActiveElement: false,
        });
        this.propertiesRef = useRef("properties");
        this.domIdPrefix = `property_${uuid()}`;
        this.definitionRecordField = this.field.definition.definition_record;

        this.state = useState({
            canChangeDefinition: false,
            isInEditMode: false,
            movedPropertyName: null,
            popoverPropertyName: null,
        });

        let currentResId;
        useRecordObserver((record) => {
            if (currentResId !== record.resId) {
                currentResId = record.resId;
                this._saveInitialPropertiesValues();
            }
        });

        this.setupEditMode();
        this.setupPopoverPlacement();

        usePropertiesSortable({
            propertiesRef: this.propertiesRef,
            getEnabled: () => !this.props.readonly && this.state.canChangeDefinition,
            getRenderedColumnsCount: () => this.renderedColumnsCount,
            getGroupedPropertiesList: () => this.groupedPropertiesList,
            onPropertyMoveTo: (from, to, moveBefore) =>
                this.onPropertyMoveTo(from, to, moveBefore),
            onGroupMoveTo: (from, to) => this.onGroupMoveTo(from, to),
            onToggleSeparators: (names, force) => this._toggleSeparators(names, force),
        });
    }

    setupEditMode() {
        if (this.env.config?.viewType === "form") {
            useBus(this.env.model.bus, ModelEvent.PROPERTY_FIELD_EDIT, async () => {
                if (this.props.readonly || this.state.isInEditMode) {
                    return;
                }
                const isInEditMode = await this._recomputeEditMode(this.props, {
                    force: true,
                });
                if (!this.state.canChangeDefinition) {
                    this.notification.add(this._getPropertyEditWarningText(), {
                        type: "warning",
                    });
                }
                if (isInEditMode && !this.propertiesList.length) {
                    this.onPropertyCreate();
                }
            });
        }

        onWillStart(async () => {
            if (this.props.readonly || !this.props.editMode) {
                return;
            }
            await this._recomputeEditMode();
        });

        useEffect(
            () => {
                if (
                    this.props.readonly ||
                    (!this.state.isInEditMode && !this.props.editMode)
                ) {
                    return;
                }
                this._recomputeEditMode(this.props, { recheck: true });
            },
            () => [this.props.record.data[this.definitionRecordField]],
        );

        onWillUpdateProps(async (nextProps) => {
            if (nextProps.readonly && !this.props.readonly) {
                this.state.isInEditMode = false;
            }
            if (
                !nextProps.readonly &&
                (this.props.readonly || (nextProps.editMode && !this.props.editMode))
            ) {
                await this._recomputeEditMode(nextProps);
            }
        });
    }

    setupPopoverPlacement() {
        useEffect(
            () => {
                if (this.openPropertyDefinition) {
                    const propertyName = this.openPropertyDefinition;
                    const labels = this.propertiesRef.el.querySelectorAll(
                        `.o_property_field[property-name="${propertyName}"] .o_field_property_open_popover`,
                    );
                    this.openPropertyDefinition = null;
                    const lastLabel = labels[labels.length - 1];
                    this._openPropertyDefinition(lastLabel, propertyName, true);
                }
            },
            () => [this.openPropertyDefinition],
        );

        useEffect(() => this._movePopoverIfNeeded());
    }

    /** @returns {object} */
    get renderedColumnsCount() {
        return this.env.isSmall ? 1 : this.props.columns;
    }

    /** @returns {array} */
    get propertiesList() {
        return (this.field.value || [])
            .filter((definition) => !definition.definition_deleted)
            .map((definition) => ({ ...definition }));
    }

    get additionalPropertyDefinitionProps() {
        return {};
    }

    /** @returns {import("./properties_layout").PropertyGroup[]} */
    get groupedPropertiesList() {
        return groupProperties(this.propertiesList, this.renderedColumnsCount);
    }

    /** @returns {integer} */
    get definitionRecordId() {
        return this.props.record.data[this.definitionRecordField]?.id;
    }

    /** @returns {string} */
    get definitionRecordModel() {
        return this.props.record.fields[this.definitionRecordField].relation;
    }

    /**
     * @param {HTMLElement} target
     * @returns {boolean}
     */
    checkPopoverClose(target) {
        if (target.closest(".o_datetime_picker")) {
            return false;
        }

        if (target.closest(".modal")) {
            return false;
        }

        if (target.closest(".o_tag_popover")) {
            return false;
        }

        if (target.closest(".o_model_field_selector_popover")) {
            return false;
        }

        return true;
    }

    /**
     * @param {string} propertyName
     * @returns {string}
     */
    getPropertyDomID(propertyName) {
        return `${this.domIdPrefix}_${propertyName}`;
    }

    /** @returns {string} */
    generatePropertyName(propertyType) {
        let name = uuid();
        if (propertyType === "html") {
            name = `${name}_html`;
        }
        return name;
    }

    /**
     * @param {string} propertyName
     * @param {"up" | "down"} direction
     */
    async onPropertyMove(propertyName, direction) {
        let movedValues = null;
        let movedTargetIndex = -1;
        await this._updateRecordProperties((propertiesValues) => {
            const result = movePropertyByOffset(
                propertiesValues,
                propertyName,
                direction,
            );
            if (result.status === "at-edge") {
                this.notification.add(
                    direction === "down"
                        ? _t("This field is already last")
                        : _t("This field is already first"),
                    { type: "warning" },
                );
                return null;
            }
            if (result.status !== "moved") {
                return null;
            }
            this.state.movedPropertyName = propertyName;
            movedValues = propertiesValues;
            movedTargetIndex = result.targetIndex;
            return propertiesValues;
        });
        if (!movedValues) {
            return;
        }
        await this._unfoldPropertyGroup(movedTargetIndex, movedValues);

        this.state.popoverPropertyName = propertyName;
    }

    /**
     * @param {string} propertyName
     * @param {string} toPropertyName
     */
    async onPropertyMoveTo(propertyName, toPropertyName, moveBefore) {
        return this._updateRecordProperties((propertiesValues) =>
            movePropertyTo(propertiesValues, {
                propertyName,
                toPropertyName,
                moveBefore,
                columnsCount: this.renderedColumnsCount,
                generateName: (type) => this.generatePropertyName(type),
                separatorTitle: (index) => _t("Group %s", index),
            }),
        );
    }

    /**
     * @param {string} propertyName
     * @param {string} toPropertyName
     */
    onGroupMoveTo(propertyName, toPropertyName) {
        return this._updateRecordProperties((propertiesValues) =>
            moveGroupTo(propertiesValues, propertyName, toPropertyName),
        );
    }

    /**
     * @param {string} propertyName
     * @param {object} propertyValue
     */
    onPropertyValueChange(propertyName, propertyValue) {
        return this._updateRecordProperties((propertiesValues) => {
            const property = propertiesValues.find(
                (property) => property.name === propertyName,
            );
            if (!property) {
                return null;
            }
            property.value = propertyValue;
            return propertiesValues;
        });
    }

    /**
     * @param {MouseEvent} event
     * @param {string} propertyName
     */
    async onPropertyEdit(event, propertyName) {
        event.stopPropagation();
        event.preventDefault();
        const target = /** @type {HTMLElement} */ (event.target);
        if (target.classList.contains("disabled")) {
            return;
        }

        target.classList.add("disabled");
        this._openPropertyDefinition(target, propertyName, false);
    }

    /** @param {object} propertyDefinition */
    async onPropertyDefinitionChange(propertyDefinition) {
        propertyDefinition["definition_changed"] = true;
        if (propertyDefinition.type === "separator") {
            const separatorKeys = new Set([
                "definition_changed",
                "fold_by_default",
                "name",
                "string",
                "type",
                "value",
            ]);
            for (const key of Object.keys(propertyDefinition)) {
                if (!separatorKeys.has(key)) {
                    delete propertyDefinition[key];
                }
            }
        }
        const newType = propertyDefinition.type;
        let oldType;
        let applied = false;
        let previousSeparatorName = null;
        await this._updateRecordProperties((propertiesValues) => {
            const propertyIndex = propertiesValues.findIndex(
                (property) => property.name === propertyDefinition.name,
            );
            if (propertyIndex < 0) {
                return null;
            }
            oldType = propertiesValues[propertyIndex].type;
            if (oldType === "separator" && newType !== "separator") {
                previousSeparatorName =
                    propertiesValues.findLast(
                        (property, index) =>
                            index < propertyIndex && property.type === "separator",
                    )?.name ?? null;
            }
            this._regeneratePropertyName(
                propertyDefinition,
                propertiesValues[propertyIndex],
            );
            propertiesValues[propertyIndex] = propertyDefinition;
            applied = true;
            return propertiesValues;
        });
        if (!applied) {
            return;
        }

        if (newType === "separator" && oldType !== "separator") {
            await this._toggleSeparators(
                [propertyDefinition.name],
                propertyDefinition.fold_by_default,
            );
            this.state.popoverPropertyName = propertyDefinition.name;
        } else if (oldType === "separator" && newType !== "separator") {
            if (previousSeparatorName) {
                await this._toggleSeparators(
                    [previousSeparatorName],
                    propertyDefinition.fold_by_default,
                );
            }
            this.state.popoverPropertyName = propertyDefinition.name;
        }
    }

    /** @param {string} propertyName */
    onPropertyDelete(propertyName) {
        let message = _t("Are you sure you want to delete this property field?") + " ";
        if (this.definitionRecordModel !== "properties.base.definition") {
            const parentName =
                this.props.record.data[this.definitionRecordField].display_name;
            const parentFieldLabel =
                this.props.record.fields[this.definitionRecordField].string;
            message += _t(
                'It will be removed for everyone using the "%(parentName)s" %(parentFieldLabel)s.',
                { parentName, parentFieldLabel },
            );
        } else {
            message += _t("It will be removed for everyone!");
        }
        this.popover.close();
        const dialogProps = {
            title: _t("Delete Property Field"),
            body: message,
            confirmLabel: _t("Delete Field"),
            cancelLabel: _t("Discard"),
            confirm: () => {
                this._updateRecordProperties((propertiesDefinitions) => {
                    const property = propertiesDefinitions.find(
                        (property) => property.name === propertyName,
                    );
                    if (!property) {
                        return null;
                    }
                    property.definition_deleted = true;
                    return propertiesDefinitions;
                });
            },
            cancel: () => {},
        };
        this.dialogService.add(ConfirmationDialog, dialogProps);
    }

    async onPropertyCreate() {
        if (!this.definitionRecordId || !this.definitionRecordModel) {
            this.notification.add(
                _t("Oops! A %(parentFieldLabel)s is needed to add property fields.", {
                    parentFieldLabel:
                        this.props.record.fields[this.definitionRecordField].string,
                }),
                { type: "warning" },
            );
            return;
        }
        let newName = null;
        let insertedAt = -1;
        let appliedValues = null;
        await this._updateRecordProperties((propertiesDefinitions) => {
            if (
                propertiesDefinitions.length &&
                propertiesDefinitions.some(
                    (prop) =>
                        prop.type !== "separator" &&
                        (!prop.string || !prop.string.length),
                )
            ) {
                this.propertiesRef.el
                    .closest(".o_field_properties")
                    .classList.add("o_field_invalid");

                this.notification.add(
                    _t("Please complete your properties before adding a new one"),
                    {
                        type: "warning",
                    },
                );
                return null;
            }
            const count = propertiesDefinitions.length;

            this.propertiesRef.el
                .closest(".o_field_properties")
                .classList.remove("o_field_invalid");

            newName = this.generatePropertyName("char");
            propertiesDefinitions.push({
                name: newName,
                string: _t("Property %s", count + 1),
                type: "char",
                definition_changed: true,
            });
            this.initialValues[newName] = { name: newName, type: "char" };
            insertedAt = count;
            appliedValues = propertiesDefinitions;
            return propertiesDefinitions;
        });
        if (!appliedValues) {
            return;
        }
        await this._unfoldPropertyGroup(insertedAt, appliedValues);
        this.openPropertyDefinition = newName;
    }

    /** @param {string} propertyName */
    onSeparatorClick(propertyName) {
        if (propertyName) {
            this._toggleSeparators([propertyName]);
        }
    }

    async checkDefinitionWriteAccess() {
        if (!this.definitionRecordId || !this.definitionRecordModel) {
            return false;
        }

        return await user.checkAccessRight(
            this.definitionRecordModel,
            "write",
            this.definitionRecordId,
        );
    }

    /**
     * @param {string} propertyName
     * @param {array} newTags
     * @param {array | null} newValue
     */
    onTagsChange(propertyName, newTags, newValue = null) {
        const propertyDefinition = this.propertiesList.find(
            (property) => property.name === propertyName,
        );
        if (!propertyDefinition) {
            return;
        }
        propertyDefinition.tags = newTags;
        if (newValue !== null) {
            propertyDefinition.value = newValue;
        }
        propertyDefinition.definition_changed = true;
        this.onPropertyDefinitionChange(propertyDefinition);
    }

    /**
     * @param {(properties: any[]) => any[] | void} mutate
     * @returns {Promise}
     */
    _updateRecordProperties(mutate) {
        this._propertiesMutation = (this._propertiesMutation ?? Promise.resolve())
            .catch(() => {})
            .then(() => {
                const propertiesValues = mutate(this.propertiesList);
                if (!propertiesValues) {
                    return;
                }
                const knownNames = new Set(
                    propertiesValues.map((property) => property.name),
                );
                const deletedProperties = (this.field.value || [])
                    .filter(
                        (definition) =>
                            definition.definition_deleted &&
                            !knownNames.has(definition.name),
                    )
                    .map((definition) => ({ ...definition }));
                return this.field.update([...propertiesValues, ...deletedProperties]);
            });
        return this._propertiesMutation;
    }

    /**
     * @param {object} [props=this.props]
     * @param {object} [options]
     * @param {boolean} [options.recheck=false]
     * @param {boolean} [options.force=false]
     * @returns {Promise<boolean>}
     */
    async _recomputeEditMode(
        props = this.props,
        { recheck = false, force = false } = {},
    ) {
        let canChangeDefinition = !recheck && this.state.canChangeDefinition;
        if (!canChangeDefinition) {
            canChangeDefinition = await this.checkDefinitionWriteAccess();
        }
        this.state.canChangeDefinition = !!canChangeDefinition;
        this.state.isInEditMode =
            !!canChangeDefinition &&
            !props.readonly &&
            (force || this.state.isInEditMode || !!props.editMode);
        return this.state.isInEditMode;
    }

    /**
     * @param {array} separatorNames
     * @param {boolean} [forceState]
     */
    _toggleSeparators(separatorNames, forceState) {
        return this._updateRecordProperties((propertiesValues) => {
            for (const separatorName of separatorNames) {
                const property = propertiesValues.find(
                    (prop) => prop.name === separatorName,
                );
                if (property) {
                    property.value =
                        forceState ?? !(property.value ?? property.fold_by_default);
                }
            }
            return propertiesValues;
        });
    }

    _movePopoverIfNeeded() {
        const propertyName = this.state.popoverPropertyName;
        if (!propertyName) {
            return;
        }
        this.state.popoverPropertyName = null;

        const target = this.propertiesRef.el?.querySelector(
            ".o_property_popover_pending",
        );
        if (!target) {
            return;
        }

        if (!this.popover.isOpen || this.popoverTarget !== target) {
            this._openPropertyDefinition(
                /** @type {HTMLElement} */ (target),
                propertyName,
            );
            return;
        }

        const popoverContent = document.querySelector(".o_field_property_definition");
        const popover = popoverContent?.closest(".o_popover");
        if (!popover) {
            return;
        }

        reposition(
            /** @type {HTMLElement} */ (popover),
            /** @type {HTMLElement} */ (target),
            { position: "top", margin: 10 },
        );
    }

    /**
     * @param {object} newDefinition
     * @param {object} oldDefinition
     */
    _regeneratePropertyName(newDefinition, oldDefinition) {
        const initialValues = this.initialValues[newDefinition.name];
        if (
            initialValues &&
            newDefinition.type === initialValues.type &&
            newDefinition.comodel === initialValues.comodel
        ) {
            newDefinition.name = initialValues.name;
        } else if (
            oldDefinition.type !== newDefinition.type ||
            oldDefinition.comodel !== newDefinition.comodel
        ) {
            const newName = this.generatePropertyName(newDefinition.type);
            this.initialValues[newName] = initialValues;
            newDefinition.name = newName;
        }
    }

    /**
     * @param {string} propertyName
     * @returns {string}
     */
    getPropertyKey(propertyName) {
        return this.initialValues?.[propertyName]?.name ?? propertyName;
    }

    /** @returns {integer} */
    _getPropertyIndex(propertyName) {
        const initialName = this.initialValues[propertyName]?.name || propertyName;
        return this.propertiesList.findIndex((property) =>
            [propertyName, initialName].includes(property.name),
        );
    }

    _saveInitialPropertiesValues() {
        this.initialValues = {};
        for (const propertiesValues of this.field.value || []) {
            this.initialValues[propertiesValues.name] = {
                name: propertiesValues.name,
                type: propertiesValues.type,
                comodel: propertiesValues.comodel,
            };
        }
    }

    /**
     * @param {Element} target
     * @param {string} propertyName
     * @param {boolean} isNewlyCreated
     */
    _openPropertyDefinition(target, propertyName, isNewlyCreated = false) {
        const propertiesList = this.propertiesList;
        const propertyIndex = propertiesList.findIndex(
            (property) => property.name === propertyName,
        );

        const currentName = (propertyName) => {
            const propertiesList = this.propertiesList;
            for (const [newName, initialValue] of Object.entries(this.initialValues)) {
                if (initialValue.name === propertyName) {
                    const prop = propertiesList.find((prop) => prop.name === newName);
                    if (prop) {
                        return newName;
                    }
                }
            }
            return propertyName;
        };

        this.popover.close();

        this.onCloseCurrentPopover = () => {
            this.onCloseCurrentPopover = null;
            this.state.movedPropertyName = null;
            target.classList.remove("disabled");
            if (isNewlyCreated) {
                this._setDefaultPropertyValue(currentName(propertyName));
            }
        };

        this.popoverTarget = target;
        this.popover.open(/** @type {HTMLElement} */ (target), {
            fieldName: this.props.name,
            readonly: this.props.readonly || !this.state.canChangeDefinition,
            canChangeDefinition: this.state.canChangeDefinition,
            propertyDefinition: this.propertiesList.find(
                (property) => property.name === currentName(propertyName),
            ),
            context: this.props.context,
            onChange: this.onPropertyDefinitionChange.bind(this),
            onDelete: () => this.onPropertyDelete(currentName(propertyName)),
            onPropertyMove: (direction) =>
                this.onPropertyMove(currentName(propertyName), direction),
            isNewlyCreated: isNewlyCreated,
            propertyIndex: propertyIndex,
            propertiesSize: propertiesList.length,
            record: this.props.record,
            ...this.additionalPropertyDefinitionProps,
        });
    }

    /** @param {string} propertyName */
    _setDefaultPropertyValue(propertyName) {
        return this._updateRecordProperties((propertiesValues) => {
            const newProperty = propertiesValues.find(
                (property) => property.name === propertyName,
            );
            if (!newProperty?.default) {
                return null;
            }
            newProperty.value = newProperty.default;
            return propertiesValues;
        });
    }

    /**
     * @param {integer} targetIndex
     * @param {object} propertiesValues
     */
    _unfoldPropertyGroup(targetIndex, propertiesValues) {
        const separator = findEnclosingSeparator(propertiesValues, targetIndex);
        if (separator) {
            return this._toggleSeparators([separator.name], false);
        }
    }

    _getPropertyEditWarningText() {
        if (!this.definitionRecordId) {
            return _t(
                "Oops! A %(parentFieldLabel)s is needed to add property fields.",
                {
                    parentFieldLabel:
                        this.props.record.fields[this.definitionRecordField].string,
                },
            );
        }
        return _t('Oops! You cannot edit the %(parentFieldLabel)s "%(parentName)s".', {
            parentName: this.props.record.data[this.definitionRecordField].display_name,
            parentFieldLabel:
                this.props.record.fields[this.definitionRecordField].string,
        });
    }
}

/** @type {import("registries").FieldsRegistryItemShape} */
export const propertiesField = {
    component: PropertiesField,
    displayName: _t("Properties"),
    supportedAttributes: [
        archAttribute("columns", _t("Columns"), {
            type: "number",
            help: _t("How many columns the property list is laid out in: 1 or 2."),
        }),
        archAttribute("edit_mode", _t("Start in edit mode"), {
            type: "boolean",
            help: _t("Open with the definition editor already available."),
        }),
    ],
    supportedTypes: ["properties"],
    extractProps({ attrs }, dynamicInfo) {
        return {
            context: dynamicInfo.context,
            columns: Number.parseInt(attrs.columns || "1", 10),
            editMode: exprToBoolean(attrs.edit_mode),
        };
    },
};

registerField("properties", propertiesField);

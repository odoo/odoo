/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "../standard_field_props";
import { uuid } from "../../utils";
import { PropertyDefinition } from "./property_definition";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { PropertyValue } from "./property_value";
import { useBus, useService } from "@web/core/utils/hooks";
import { usePopover } from "@web/core/popover/popover_hook";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { reposition } from "@web/core/position_hook";
import { archParseBoolean } from "@web/views/utils";
import { pick } from "@web/core/utils/objects";
import { useSortable } from "@web/core/utils/sortable_owl";
import { useRecordObserver } from "@web/model/relational_model/utils";

import { Component, useRef, useState, useEffect, onWillStart } from "@odoo/owl";

export class PropertiesField extends Component {
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
        showAddButton: { type: Boolean, optional: true },
    };

    setup() {
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.user = useService("user");
        this.dialogService = useService("dialog");
        this.popover = usePopover(PropertyDefinition, {
            closeOnClickAway: this.checkPopoverClose,
            popoverClass: "o_property_field_popover",
            position: "top",
            onClose: () => this.onCloseCurrentPopover?.(),
            fixedPosition: true,
            arrow: false,
        });
        this.propertiesRef = useRef("properties");

        let currentResId;
        useRecordObserver((record) => {
            if (currentResId !== record.resId) {
                currentResId = record.resId;
                this._saveInitialPropertiesValues();
            }
        });

        const field = this.props.record.fields[this.props.name];
        this.definitionRecordField = field.definition_record;

        this.state = useState({
            canChangeDefinition: true,
            movedPropertyName: null,
            showAddButton: this.props.showAddButton,
            unfoldedSeparators: this._getUnfoldedSeparators(),
        });

        // Properties can be added from the cogmenu of the form controller
        if (this.env.config?.viewType === "form") {
            useBus(this.env.model.bus, "PROPERTY_FIELD:ADD_PROPERTY_VALUE", () => {
                this.onPropertyCreate();
            });
        }

        onWillStart(async () => {
            await this._checkDefinitionAccess();
        });

        useEffect(
            () => {
                if (this.openPropertyDefinition) {
                    const propertyName = this.openPropertyDefinition;
                    const labels = this.propertiesRef.el.querySelectorAll(
                        `.o_property_field[property-name="${propertyName}"] .o_field_property_open_popover`
                    );
                    this.openPropertyDefinition = null;
                    const lastLabel = labels[labels.length - 1];
                    this._openPropertyDefinition(lastLabel, propertyName, true);
                }
            },
            () => [this.openPropertyDefinition]
        );

        useEffect(() => this._movePopoverIfNeeded());

        // sort properties
        useSortable({
            enable: () => !this.props.readonly && this.state.canChangeDefinition,
            ref: this.propertiesRef,
            handle: ".o_field_property_label .oi-draggable",
            // on mono-column layout, allow to move before a separator to make the usage more fluid
            elements:
                this.renderedColumnsCount === 1
                    ? "*:is(.o_property_field, .o_field_property_group_label)"
                    : ".o_property_field",
            groups: ".o_property_group",
            connectGroups: true,
            cursor: "grabbing",
            onDragStart: ({ element, group }) => {
                this.propertiesRef.el.classList.add("o_property_dragging");
                element.classList.add("o_property_drag_item");
                group.classList.add("o_property_drag_group");
                // without this, if we edit a char property, move it,
                // the change will be reset when we drop the property
                document.activeElement.blur();
            },
            onDrop: async ({ parent, element, next, previous }) => {
                const from = element.getAttribute("property-name");
                let to = previous && previous.getAttribute("property-name");
                let moveBefore = false;
                if (!to && next) {
                    // we move the element at the first position inside a group
                    // or at the first position of a column
                    if (next.classList.contains("o_field_property_group_label")) {
                        // mono-column layout, move before the separator
                        next = next.closest(".o_property_group");
                    }
                    to = next.getAttribute("property-name");
                    moveBefore = !!to;
                }
                if (!to) {
                    // we move in an empty group or outside of the DOM element
                    // move the element at the end of the group
                    const groupName = parent.getAttribute("property-name");
                    const group = this.groupedPropertiesList.find(
                        (group) => group.name === groupName
                    );
                    if (!group) {
                        to = null;
                        moveBefore = false;
                    } else {
                        to = group.elements.length ? group.elements.at(-1).name : groupName;
                    }
                }
                await this.onPropertyMoveTo(from, to, moveBefore);
            },
            onDragEnd: ({ element }) => {
                this.propertiesRef.el.classList.remove("o_property_dragging");
                element.classList.remove("o_property_drag_item");
                const targetGroup = this.propertiesRef.el.querySelector(".o_property_drag_group");
                if (targetGroup) {
                    targetGroup.classList.remove("o_property_drag_group");
                }
            },
            onGroupEnter: ({ group }) => {
                group.classList.add("o_property_drag_group");
                this._unfoldSeparators([group.getAttribute("property-name")], true);
            },
            onGroupLeave: ({ group }) => {
                group.classList.remove("o_property_drag_group");
            },
        });

        // sort group of properties
        useSortable({
            enable: () => !this.props.readonly && this.state.canChangeDefinition,
            ref: this.propertiesRef,
            handle: ".o_field_property_group_label .oi-draggable",
            elements: ".o_property_group:not([property-name=''])",
            cursor: "grabbing",
            onDragStart: ({ element }) => {
                this.propertiesRef.el.classList.add("o_property_dragging");
                element.classList.add("o_property_drag_item");
                document.activeElement.blur();
            },
            onDrop: async ({ element, previous }) => {
                const from = element.getAttribute("property-name");
                const to = previous && previous.getAttribute("property-name");
                await this.onGroupMoveTo(from, to);
            },
            onDragEnd: ({ element }) => {
                this.propertiesRef.el.classList.remove("o_property_dragging");
                element.classList.remove("o_property_drag_item");
            },
        });
    }

    /* --------------------------------------------------------
     * Public methods / Getters
     * -------------------------------------------------------- */

    /**
     * Return the number of columns we have to render
     * (The properties can be split in many column,
     * to follow the layout of the form view)
     *
     * @returns {object}
     */
    get renderedColumnsCount() {
        return this.env.isSmall ? 1 : this.props.columns;
    }

    /**
     * Return the current properties value.
     *
     * Make a deep copy of this properties values, so when we will modify it
     * in the events, we won't re-use same object (can lead to issue, e.g. if we
     * discard a form view, we should be able to restore the old props).
     *
     * @returns {array}
     */
    get propertiesList() {
        const propertiesValues = this.props.record.data[this.props.name] || [];
        return propertiesValues.filter((definition) => !definition.definition_deleted);
    }

    /**
     * Return the current properties value splitted in multiple groups/columns.
     * Each properties are splitted in groups, thanks to the separators, and
     * groups are splitted in columns (the columns property is the number of groups
     * we have on a row).
     *
     * The groups are created with the separators (special type of property) so
     * the order mater in the group creation.
     *
     * @returns {Array<Array>}
     */
    get groupedPropertiesList() {
        const propertiesList = this.propertiesList;
        // default invisible group
        const groupedProperties =
            propertiesList[0]?.type !== "separator"
                ? [{ title: null, name: null, elements: [], invisibleLabel: true }]
                : [];

        propertiesList.forEach((property) => {
            if (property.type === "separator") {
                groupedProperties.push({
                    title: property.string,
                    name: property.name,
                    elements: [],
                });
            } else {
                groupedProperties.at(-1).elements.push(property);
            }
        });

        if (groupedProperties.length === 1) {
            // only one group, split this group in the columns to take the entire width
            const invisibleLabel = propertiesList[0]?.type !== "separator";
            groupedProperties[0].elements = [];
            groupedProperties[0].invisibleLabel = invisibleLabel;
            for (let col = 1; col < this.renderedColumnsCount; ++col) {
                groupedProperties.push({
                    title: null,
                    name: groupedProperties[0].name,
                    columnSeparator: true,
                    elements: [],
                    invisibleLabel,
                });
            }
            const properties = propertiesList.filter((property) => property.type !== "separator");
            properties.forEach((property, index) => {
                const columnIndex = Math.floor(
                    (index * this.renderedColumnsCount) / properties.length
                );
                groupedProperties[columnIndex].elements.push(property);
            });
        }

        return groupedProperties;
    }

    /**
     * Return the id of the definition record.
     *
     * @returns {integer}
     */
    get definitionRecordId() {
        return this.props.record.data[this.definitionRecordField][0];
    }

    /**
     * Return the model of the definition record.
     *
     * @returns {string}
     */
    get definitionRecordModel() {
        return this.props.record.fields[this.definitionRecordField].relation;
    }

    /**
     * Return true if we should close the popover containing the
     * properties definition based on the target received.
     *
     * If we edit the datetime, it will open a popover with the date picker
     * component, but this component won't be a child of the current popover.
     * So when we will click on it to select a date, it will close the definition
     * popover. It's the same for other similar components (many2one modal, etc).
     *
     * @param {HTMLElement} target
     * @returns {boolean}
     */
    checkPopoverClose(target) {
        if (target.closest(".o_datetime_picker")) {
            // selected a datetime, do not close the definition popover
            return false;
        }

        if (target.closest(".modal")) {
            // close a many2one modal
            return false;
        }

        if (target.closest(".o_tag_popover")) {
            // tag color popover
            return false;
        }

        if (target.closest(".o_model_field_selector_popover")) {
            // domain selector
            return false;
        }

        return true;
    }

    /**
     * Generate an unique ID to be used in the DOM.
     *
     * @returns {string}
     */
    generateUniqueDomID() {
        return `property_${uuid()}`;
    }

    /**
     * Generate a new property name.
     *
     * @returns {string}
     */
    generatePropertyName() {
        return uuid();
    }

    /* --------------------------------------------------------
     * Event handlers
     * -------------------------------------------------------- */

    /**
     * Move the given property up or down in the list.
     *
     * @param {string} propertyName
     * @param {string} direction, either "up" or "down"
     */
    async onPropertyMove(propertyName, direction) {
        const propertiesValues = this.propertiesList || [];
        const propertyIndex = propertiesValues.findIndex(
            (property) => property.name === propertyName
        );

        const targetIndex = propertyIndex + (direction === "down" ? 1 : -1);
        if (targetIndex < 0 || targetIndex >= propertiesValues.length) {
            this.notification.add(
                direction === "down"
                    ? _t("This field is already last")
                    : _t("This field is already first"),
                { type: "warning" }
            );
            return;
        }
        this.state.movedPropertyName = propertyName;

        const prop = propertiesValues[targetIndex];
        propertiesValues[targetIndex] = propertiesValues[propertyIndex];
        propertiesValues[propertyIndex] = prop;
        propertiesValues[propertyIndex].definition_changed = true;

        this._unfoldPropertyGroup(targetIndex, propertiesValues);

        await this.props.record.update({ [this.props.name]: propertiesValues });
        // move the popover once the DOM is updated
        this.movePopoverToProperty = propertyName;
    }

    /**
     * Move a property after the target property.
     *
     * @param {string} propertyName
     * @param {string} toPropertyName, the target property
     *  (null if we move the property to the first index)
     */
    onPropertyMoveTo(propertyName, toPropertyName, moveBefore) {
        const propertiesValues = this.propertiesList || [];

        let fromIndex = propertiesValues.findIndex((property) => property.name === propertyName);
        let toIndex = propertiesValues.findIndex((property) => property.name === toPropertyName);
        const columnSize = Math.ceil(propertiesValues.length / this.renderedColumnsCount);

        // if we have no separator at first, we might want to create some
        // to keep the initial column separation (only if needed, if we move properties
        // inside the same column we do nothing)
        if (
            this.renderedColumnsCount > 1 &&
            !propertiesValues.some((p, index) => index !== 0 && p.type === "separator") &&
            Math.floor(fromIndex / columnSize) !== Math.floor(toIndex / columnSize)
        ) {
            const newSeparators = [];
            for (let col = 0; col < this.renderedColumnsCount; ++col) {
                const separatorIndex = columnSize * col + newSeparators.length;

                if (propertiesValues[separatorIndex]?.type === "separator") {
                    newSeparators.push(propertiesValues[separatorIndex].name);
                    continue;
                }
                const newSeparator = {
                    type: "separator",
                    string: _t("Group %s", col + 1),
                    name: this.generatePropertyName(),
                };
                newSeparators.push(newSeparator.name);
                propertiesValues.splice(separatorIndex, 0, newSeparator);
            }
            this._unfoldSeparators(newSeparators, true);
            toPropertyName = toPropertyName || propertiesValues.at(-1).name;

            // indexes might have changed
            fromIndex = propertiesValues.findIndex((property) => property.name === propertyName);
            toIndex = propertiesValues.findIndex((property) => property.name === toPropertyName);
        }

        if (moveBefore) {
            toIndex--;
        }
        if (toIndex < fromIndex) {
            // the first splice operation will change the index
            toIndex++;
        }
        propertiesValues.splice(toIndex, 0, propertiesValues.splice(fromIndex, 1)[0]);
        propertiesValues[0].definition_changed = true;
        this.props.record.update({ [this.props.name]: propertiesValues });
    }

    /**
     * Move a group of properties after the target group.
     *
     * @param {string} propertyName
     * @param {string} toPropertyName, the target group (separator)
     *  (null if we move the group to the first index)
     */
    onGroupMoveTo(propertyName, toPropertyName) {
        const propertiesValues = this.propertiesList || [];
        const fromIndex = propertiesValues.findIndex((property) => property.name === propertyName);
        const toIndex = propertiesValues.findIndex((property) => property.name === toPropertyName);
        if (
            propertiesValues[fromIndex].type !== "separator" ||
            (toIndex >= 0 && propertiesValues[toIndex].type !== "separator")
        ) {
            throw new Error("Something went wrong");
        }

        // find the next separator index
        const getNextSeparatorIndex = (startIndex) => {
            const nextSeparatorIndex = propertiesValues.findIndex(
                (property, index) => property.type === "separator" && index > startIndex
            );
            return nextSeparatorIndex < 0 ? propertiesValues.length : nextSeparatorIndex;
        };
        const groupSize = getNextSeparatorIndex(fromIndex) - fromIndex;
        let targetIndex = getNextSeparatorIndex(toIndex);
        if (targetIndex > fromIndex) {
            // the size of the array will change after the first splice
            // so we need to correct the index
            targetIndex -= groupSize;
        }
        propertiesValues.splice(targetIndex, 0, ...propertiesValues.splice(fromIndex, groupSize));
        propertiesValues[0].definition_changed = true;
        this.props.record.update({ [this.props.name]: propertiesValues });
    }

    /**
     * The value / definition of the given property has been changed.
     * `propertyValue` contains the definition of the property with the value.
     *
     * @param {string} propertyName
     * @param {object} propertyValue
     */
    onPropertyValueChange(propertyName, propertyValue) {
        const propertiesValues = this.propertiesList;
        propertiesValues.find((property) => property.name === propertyName).value = propertyValue;
        this.props.record.update({ [this.props.name]: propertiesValues });
    }

    /**
     * Check if the definition is not already opened
     * and if it's not the case, open the popover with the property definition.
     *
     * @param {event} event
     * @param {string} propertyName
     */
    async onPropertyEdit(event, propertyName) {
        event.stopPropagation();
        event.preventDefault();
        if (!(await this.checkDefinitionWriteAccess())) {
            this.notification.add(
                _t("You need edit access on the parent document to update these property fields"),
                { type: "warning" }
            );
            return;
        }
        if (event.target.classList.contains("disabled")) {
            // remove the glitch if we click on the edit button
            // while the popover is already opened
            return;
        }

        event.target.classList.add("disabled");
        this._openPropertyDefinition(event.target, propertyName, false);
    }

    /**
     * The property definition or value has been changed.
     *
     * @param {object} propertyDefinition
     */
    async onPropertyDefinitionChange(propertyDefinition) {
        propertyDefinition["definition_changed"] = true;
        if (propertyDefinition.type === "separator") {
            // remove all other keys
            propertyDefinition = pick(
                propertyDefinition,
                "name",
                "string",
                "definition_changed",
                "type"
            );
        }
        const propertiesValues = this.propertiesList;
        const propertyIndex = this._getPropertyIndex(propertyDefinition.name);

        const oldType = propertiesValues[propertyIndex].type;
        const newType = propertyDefinition.type;

        this._regeneratePropertyName(propertyDefinition);

        propertiesValues[propertyIndex] = propertyDefinition;
        await this.props.record.update({ [this.props.name]: propertiesValues });

        if (newType === "separator" && oldType !== "separator") {
            // unfold automatically the new separator
            this._unfoldSeparators([propertyDefinition.name], true);
            // layout has been changed, move the definition popover
            this.movePopoverToProperty = propertyDefinition.name;
        } else if (oldType === "separator" && newType !== "separator") {
            // unfold automatically the previous separator
            const previousSeperator = propertiesValues.findLast(
                (property, index) => index < propertyIndex && property.type === "separator"
            );
            if (previousSeperator) {
                this._unfoldSeparators([previousSeperator.name], true);
            }
            // layout has been changed, move the definition popover
            this.movePopoverToProperty = propertyDefinition.name;
        }
    }

    /**
     * Mark a property as "to delete".
     *
     * @param {string} propertyName
     */
    onPropertyDelete(propertyName) {
        this.popover.close();
        const dialogProps = {
            title: _t("Delete Property Field"),
            body: _t(
                'Are you sure you want to delete this property field? It will be removed for everyone using the "%s" %s.',
                this.parentName,
                this.parentString
            ),
            confirmLabel: _t("Delete"),
            confirm: () => {
                const propertiesDefinitions = this.propertiesList;
                propertiesDefinitions.find(
                    (property) => property.name === propertyName
                ).definition_deleted = true;
                this.props.record.update({ [this.props.name]: propertiesDefinitions });
            },
            cancel: () => {},
        };
        this.dialogService.add(ConfirmationDialog, dialogProps);
    }

    async onPropertyCreate() {
        if (!this.state.canChangeDefinition || !(await this.checkDefinitionWriteAccess())) {
            this.notification.add(
                _t("You need edit access on the parent document to update these property fields"),
                { type: "warning" }
            );
            return;
        }
        const propertiesDefinitions = this.propertiesList || [];

        if (
            propertiesDefinitions.length &&
            propertiesDefinitions.some(
                (prop) => prop.type !== "separator" && (!prop.string || !prop.string.length)
            )
        ) {
            // do not allow to add new field until we set a label on the previous one
            this.propertiesRef.el.closest(".o_field_properties").classList.add("o_field_invalid");

            this.notification.add(_t("Please complete your properties before adding a new one"), {
                type: "warning",
            });
            return;
        }

        this._unfoldPropertyGroup(propertiesDefinitions.length - 1, propertiesDefinitions);

        this.propertiesRef.el.closest(".o_field_properties").classList.remove("o_field_invalid");

        const newName = this.generatePropertyName();
        propertiesDefinitions.push({
            name: newName,
            string: _t("Property %s", propertiesDefinitions.length + 1),
            type: "char",
            definition_changed: true,
        });
        this.openPropertyDefinition = newName;
        this.state.showAddButton = true;
        this.props.record.update({ [this.props.name]: propertiesDefinitions });
    }

    /**
     * Fold / unfold the given separator property.
     *
     * @param {string} propertyName, Name of the separator property
     * @param {boolean} forceUnfold, Always unfold
     */
    onSeparatorClick(propertyName) {
        if (propertyName) {
            this._unfoldSeparators([propertyName]);
        }
    }

    /**
     * Verify that we can write on properties, we can not change the definition
     * if we don't have access for parent or if no parent is set.
     */
    async checkDefinitionWriteAccess() {
        if (!this.definitionRecordId || !this.definitionRecordModel) {
            return false;
        }

        try {
            await this.orm.call(
                this.definitionRecordModel,
                "check_access_rule",
                [this.definitionRecordId],
                { operation: "write" }
            );
        } catch {
            return false;
        }
        return true;
    }

    /**
     * The tags list has been changed.
     * If `newValue` is given, update the property value as well.
     *
     * @param {string} propertyName
     * @param {array} newTags
     * @param {array | null} newValue
     */
    onTagsChange(propertyName, newTags, newValue = null) {
        const propertyDefinition = this.propertiesList.find(
            (property) => property.name === propertyName
        );
        propertyDefinition.tags = newTags;
        if (newValue !== null) {
            propertyDefinition.value = newValue;
        }
        propertyDefinition.definition_changed = true;
        this.onPropertyDefinitionChange(propertyDefinition);
    }

    /* --------------------------------------------------------
     * Private methods
     * -------------------------------------------------------- */

    /**
     * Generate the key to get the fold state from the local storage.
     *
     * @returns {string}
     */
    _getSeparatorFoldKey() {
        const definitionRecordId = this.props.record.data[this.definitionRecordField][0];
        const definitionRecordModel = this.props.record.fields[this.definitionRecordField].relation;
        // store the fold / unfold information per definition record
        // to clean the keys (to not keep information about removed separator)
        return `properties.fold,${definitionRecordModel},${definitionRecordId}`;
    }

    /**
     * Read the local storage and return the fold state stored in it.
     *
     * We clean the dictionary state because a property might have been deleted,
     * and so there's no reason to keep the corresponding key in the dict.
     *
     * @returns {array} The folded state (name of the properties unfolded)
     */
    _getUnfoldedSeparators() {
        const key = this._getSeparatorFoldKey();
        const unfoldedSeparators = JSON.parse(window.localStorage.getItem(key)) || [];
        const allPropertiesNames = this.propertiesList.map((property) => property.name);
        // remove element that do not exist anymore (e.g. if we remove a separator)
        return unfoldedSeparators.filter((name) => allPropertiesNames.includes(name));
    }

    /**
     * Switch the folded state of the given separators.
     *
     * @param {array} separatorNames, list of separator name to fold / unfold
     * @param {boolean} (forceUnfold) force the separator to be unfolded
     */
    _unfoldSeparators(separatorNames, forceUnfold) {
        let unfoldedSeparators = this._getUnfoldedSeparators();
        for (const separatorName of separatorNames) {
            if (unfoldedSeparators.includes(separatorName)) {
                if (!forceUnfold) {
                    unfoldedSeparators = unfoldedSeparators.filter(
                        (name) => name !== separatorName
                    );
                }
            } else {
                unfoldedSeparators.push(separatorName);
            }
        }
        const key = this._getSeparatorFoldKey();
        window.localStorage.setItem(key, JSON.stringify(unfoldedSeparators));
        this.state.unfoldedSeparators = unfoldedSeparators;
    }

    /**
     * Move the popover to the given property id.
     * Used when we change the position of the properties.
     *
     * We change the popover position after the DOM has been updated (see @useEffect)
     * because if we update it after changing the component properties,
     */
    _movePopoverIfNeeded() {
        if (!this.movePopoverToProperty) {
            return;
        }
        const propertyName = this.movePopoverToProperty;
        this.movePopoverToProperty = null;

        const popover = document
            .querySelector(".o_field_property_definition")
            .closest(".o_popover");
        const target = document.querySelector(
            `*[property-name="${propertyName}"] .o_field_property_open_popover`
        );

        reposition(popover, target, { position: "top", margin: 10 });
    }

    /**
     * Verify that we can write on the parent record,
     * and therefor update the properties definition.
     */
    async _checkDefinitionAccess() {
        this.parentName = this.props.record.data[this.definitionRecordField][1];
        this.parentString = this.props.record.fields[this.definitionRecordField].string;

        if (!this.definitionRecordModel) {
            this.state.canChangeDefinition = false;
            return;
        }

        // check if we can write on the definition record
        this.state.canChangeDefinition = await this.user.checkAccessRight(
            this.definitionRecordModel,
            "write"
        );
    }

    /**
     * Regenerate a new name if needed or restore the original one.
     * (see @_saveInitialPropertiesValues).
     *
     * If the type / model are the same, restore the original name to not reset the
     * children otherwise, generate a new value so all value of the record are reset.
     *
     * @param {object} propertyDefinition
     */
    _regeneratePropertyName(propertyDefinition) {
        const initialValues = this.initialValues[propertyDefinition.name];
        if (
            initialValues &&
            propertyDefinition.type === initialValues.type &&
            propertyDefinition.comodel === initialValues.comodel
        ) {
            // restore the original name
            propertyDefinition.name = initialValues.name;
        } else if (initialValues && initialValues.name === propertyDefinition.name) {
            // Generate a new name to reset all values on other records.
            // because the name has been changed on the definition,
            // the old name on others record won't match the name on the definition
            // and the python field will just ignore the old value.
            // Store the new generated name to be able to restore it
            // if needed.
            const newName = this.generatePropertyName();
            this.initialValues[newName] = initialValues;
            propertyDefinition.name = newName;
        }
    }

    /**
     * Find the index of the given property in the list.
     *
     * Care about new name generation, if the name changed (because
     * the type of the property, the model, etc changed), it will
     * still find the index of the original property.
     *
     * @params {string} propertyName
     * @returns {integer}
     */
    _getPropertyIndex(propertyName) {
        const initialName = this.initialValues[propertyName]?.name || propertyName;
        return this.propertiesList.findIndex((property) =>
            [propertyName, initialName].includes(property.name)
        );
    }

    /**
     * If we change the type / model of a property, we will regenerate it's name
     * (like if it was a new property) in order to reset the value of the children.
     *
     * But if we reset the old model / type, we want to be able to discard this
     * modification (even if we save) and restore the original name.
     *
     * For that purpose, we save the original properties values.
     */
    _saveInitialPropertiesValues() {
        // initial properties values, if the type or the model changed, the
        // name will be regenerated in order to reset the value on the children
        this.initialValues = {};
        for (const propertiesValues of this.props.record.data[this.props.name] || []) {
            this.initialValues[propertiesValues.name] = {
                name: propertiesValues.name,
                type: propertiesValues.type,
                comodel: propertiesValues.comodel,
            };
        }
    }

    /**
     * Open the popover with the property definition.
     *
     * @param {DomElement} target
     * @param {string} propertyName
     * @param {boolean} isNewlyCreated
     */
    _openPropertyDefinition(target, propertyName, isNewlyCreated = false) {
        const propertiesList = this.propertiesList;
        const propertyIndex = propertiesList.findIndex(
            (property) => property.name === propertyName
        );

        // maybe the property has been renamed because the type / model
        // changed, retrieve the new one
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

        this.onCloseCurrentPopover = () => {
            this.onCloseCurrentPopover = null;
            this.state.movedPropertyName = null;
            target.classList.remove("disabled");
            if (isNewlyCreated) {
                this._setDefaultPropertyValue(currentName(propertyName));
            }
        };

        this.popover.open(target, {
            readonly: this.props.readonly || !this.state.canChangeDefinition,
            canChangeDefinition: this.state.canChangeDefinition,
            checkDefinitionWriteAccess: () => this.checkDefinitionWriteAccess(),
            propertyDefinition: this.propertiesList.find(
                (property) => property.name === currentName(propertyName)
            ),
            context: this.props.context,
            onChange: this.onPropertyDefinitionChange.bind(this),
            onDelete: () => this.onPropertyDelete(currentName(propertyName)),
            onPropertyMove: (direction) =>
                this.onPropertyMove(currentName(propertyName), direction),
            isNewlyCreated: isNewlyCreated,
            propertyIndex: propertyIndex,
            propertiesSize: propertiesList.length,
        });
    }

    /**
     * Write the default value on the given property.
     *
     * @param {string} propertyName
     */
    _setDefaultPropertyValue(propertyName) {
        const propertiesValues = this.propertiesList;
        const newProperty = propertiesValues.find((property) => property.name === propertyName);
        newProperty.value = newProperty.default;
        // it won't update the props, it's a trick because the onClose event of the popover
        // is called not synchronously, and so if we click on "create a property", it will close
        // the popover, calling this function, but the value will be overwritten because of onPropertyCreate
        this.props.value = propertiesValues;
        this.props.record.update({ [this.props.name]: propertiesValues });
    }

    /**
     * Unfold the group of the given property.
     *
     * @param {integer} targetIndex
     * @param {object} propertiesValues
     */
    _unfoldPropertyGroup(targetIndex, propertiesValues) {
        const separator = propertiesValues.findLast(
            (property, index) => property.type === "separator" && index <= targetIndex
        );
        if (separator) {
            this._unfoldSeparators([separator.name], true);
        }
    }
}

export const propertiesField = {
    component: PropertiesField,
    displayName: _t("Properties"),
    supportedTypes: ["properties"],
    extractProps({ attrs }, dynamicInfo) {
        return {
            context: dynamicInfo.context,
            columns: parseInt(attrs.columns || "1"),
            showAddButton: archParseBoolean(attrs.showAddButton),
        };
    },
};

registry.category("fields").add("properties", propertiesField);

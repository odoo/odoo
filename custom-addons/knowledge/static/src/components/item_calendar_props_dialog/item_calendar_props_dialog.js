/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { SCALE_LABELS } from "@web/views/calendar/calendar_controller";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { uuid } from "@web/views/utils";

import { Component, onWillStart, useExternalListener, useState } from "@odoo/owl";

/**
 * Dialog allowing to dynamically edit the item calendar view configuration
 * (the "itemCalendarProps"). Used when clicking on the "edit" button of the
 * embedded view manager.
 */
export class ItemCalendarPropsDialog extends Component {
    setup() {
        super.setup();
        useAutofocus();
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            name: this.props.name,
            scale: this.props.scale || "week",
        });
        this.colorChoices = [];
        this.dateChoices = [];
        this.dateTimeChoices = [];
        this.propertyFieldEntries = {};
        this.scalesChoices = Object.entries(SCALE_LABELS).map(([value, label]) => ({ value, label }));

        onWillStart(async () => {
            // Fetch the properties definitions and create choices to use in
            // the SelectMenu components
            const propertiesDefinitions = await this.orm.read(
                "knowledge.article",
                [this.props.knowledgeArticleId],
                ["article_properties_definition"]
            );
            this.propertiesDefinitions = propertiesDefinitions[0].article_properties_definition;
            for (const definition of this.propertiesDefinitions) {
                this.propertyFieldEntries[definition.name] = {
                    label: definition.string,
                    type: definition.type,
                };
                // Add choice in corresponding dropdown
                const choice = {
                    value: definition.name,
                    label: definition.string,
                };
                if (definition.type === "datetime") {
                    this.dateTimeChoices.push(choice);
                } else if (definition.type === "date") {
                    this.dateChoices.push(choice);
                } else if (["boolean", "many2one", "selection"].includes(definition.type)) {
                    this.colorChoices.push(choice);
                }
            }

            if (this.props.isNew) {
                // If no date(time) properties exists, create default ones
                if (!this.dateTimeChoices.length && !this.dateChoices.length) {
                    this.autoCreateDateProperties = true;
                    this.createProperty(_t("Start Date Time"), "datetime", "dateStart");
                    this.createProperty(_t("End Date Time"), "datetime", "dateStop");
                } else {
                    // If some exist, select them by default (prefer to use 2
                    // of the same type if possible, and prefer datetimes over
                    // dates)
                    if (this.dateTimeChoices.length > 1) {
                        this.selectDateStart(this.dateTimeChoices[0].value);
                        this.selectDateStop(this.dateTimeChoices[1].value);
                    } else if (this.dateChoices.length > 1) {
                        this.selectDateStart(this.dateChoices[0].value);
                        this.selectDateStop(this.dateChoices[1].value);
                    } else if (this.dateTimeChoices.length !== 0) {
                        this.selectDateStart(this.dateTimeChoices[0].value);
                    } else {
                        this.selectDateStart(this.dateChoices[0].value);
                    }
                    
                }
            } else {
                // Use props only if the related property still exists
                for (const propName of ["dateStartPropertyId", "dateStopPropertyId", "colorPropertyId"]) {
                    if (this.propertyFieldEntries[this.props[propName]]) {
                        this.state[propName] = this.props[propName];
                    }
                }
            }
        });

        // Save when pressing on enter
        useExternalListener(window, "keydown", (event) => {
            if (event.key === "Enter") {
                this.save();
            }
        });
    }

    /**
     * Return the available start properties formatted as groups (date and
     * datetime) for the SelectMenu component
     */
    get availableDateStartProperties() {
        return [{
            label: _t("Date and Time Properties"),
            choices: this.dateTimeChoices
        }, {
            label: _t("Date Properties"),
            choices: this.dateChoices,
        }];
    }

    /**
     * Return the availabe stop properties (that are of the same type as the
     * current start date) formatted as a group for the SelectMenu component
     */
    get availableDateStopProperties() {
        // Don't show current start date nor dates with other type
        if (this.dateStartProperty?.type === "datetime") {
            return [{
                label: _t("Date and Time Properties"),
                choices: this.dateTimeChoices.filter(choice => choice.value !== this.state.dateStartPropertyId),
            }];
        }
        return [{
            label: _t("Date Properties"),
            choices: this.dateChoices.filter(choice => choice.value !== this.state.dateStartPropertyId),
        }];
    }

    get colorProperty() {
        return this.propertyFieldEntries[this.state.colorPropertyId];
    }

    get dateStartProperty() {
        return this.propertyFieldEntries[this.state.dateStartPropertyId];
    }

    get dateStopProperty() {
        return this.propertyFieldEntries[this.state.dateStopPropertyId];
    }

    /**
     * Create a new date or datetime property and use it as start or stop
     * choice.
     * Note: only the new properties that are selected when saving will be
     * stored.
     * @param {string} label: label of the property
     * @param {string} type: type of the property (date or datetime)
     * @param {string} calendarProp: for which calendar prop the property has
     * been created
     */
    createProperty(label, type, calendarProp) {
        const newPropertyId = uuid();
        // Add to list of properties
        this.propertyFieldEntries[newPropertyId] = {
            isNew: true,
            label: label,
            type: type,
        };
        // Add new choice in dropdowns
        const newChoice = {
            value: newPropertyId,
            label,
        };
        if (type === "date") {
            this.dateChoices.push(newChoice);
        } else if (type === "datetime") {
            this.dateTimeChoices.push(newChoice);
        } else {
            this.colorChoices.push(newChoice);
        }
        // Select the new choice
        if (calendarProp === "dateStart") {
            this.selectDateStart(newPropertyId);
        } else if (calendarProp === "dateStop") {
            this.selectDateStop(newPropertyId);
        } else if (calendarProp === "color") {
            this.selectColor(newPropertyId);
        }
    }

    /**
     * Save the item calendar props and close the dialog. If there is a new
     * choice selected as start and/or stop date, create the associated
     * property(ies) first.
     */
    async save() {
        if (!this.state.dateStartPropertyId) {
            this.notification.add(_t("The start date property is required."), {type: "danger"});
            return;
        }
        // Create new property if needed
        if (this.dateStartProperty.isNew || this.dateStopProperty?.isNew || this.colorProperty?.isNew) {
            // Keep existing properties to not lose them.
            const propertiesDefinitions = [...this.propertiesDefinitions];
            if (this.dateStartProperty.isNew) {
                propertiesDefinitions.push({
                    name: this.state.dateStartPropertyId,
                    string: this.dateStartProperty.label,
                    type: this.dateStartProperty.type,
                });
            }
            if (this.dateStopProperty?.isNew) {
                propertiesDefinitions.push({
                    name: this.state.dateStopPropertyId,
                    string: this.dateStopProperty.label,
                    type: this.dateStopProperty.type,
                });
            }
            if (this.colorProperty?.isNew) {
                propertiesDefinitions.push({
                    name: this.state.colorPropertyId,
                    string: this.colorProperty.label,
                    type: this.colorProperty.type,
                });
            }
            try {
                await this.orm.write("knowledge.article", [this.props.knowledgeArticleId], {article_properties_definition: propertiesDefinitions});
            } catch (e) {
                this.notification.add(_t("New property could not be created."), {type: "danger"});
                console.error(e);
                return;
            }
        }
        this.props.saveItemCalendarProps(this.state.name, {
            dateStartPropertyId: this.state.dateStartPropertyId,
            dateStopPropertyId: this.state.dateStopPropertyId || undefined,
            colorPropertyId: this.state.colorPropertyId || undefined,
            scale: this.state.scale,
            dateType: this.dateStartProperty.type,
        });
        this.props.close();
    }

    selectColor(value) {
        this.state.colorPropertyId = value;
    }

    selectDateStop(value) {
        this.state.dateStopPropertyId = value;
    }

    selectScale(value) {
        this.state.scale = value;
    }

    selectDateStart(value) {
        this.state.dateStartPropertyId = value;
        // DateStop must be of the same type as start, but must not be the same property
        if (this.state.dateStopPropertyId && (this.dateStartProperty.type !== this.dateStopProperty.type || this.state.dateStopPropertyId === this.state.dateStartPropertyId)) {
            this.state.dateStopPropertyId = false;
        }
    }
}

ItemCalendarPropsDialog.template = "knowledge.ItemCalendarPropsDialog";
ItemCalendarPropsDialog.components = {
    DropdownItem,
    Dialog,
    SelectMenu,
};

ItemCalendarPropsDialog.props = {
    knowledgeArticleId: { type: Number, optional: true },
    close: { type: Function, optional: true },
    colorPropertyId: { type: String, optional: true },
    dateStartPropertyId: { type: String, optional: true },
    dateStopPropertyId: { type: String, optional: true },
    dateType: { type: String, optional: true },
    isNew: { type: Boolean, optional: true },
    name: { type: String, optional: true },
    saveItemCalendarProps: { type: Function },
    scale: { type: String, optional: true },
};

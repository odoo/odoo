/** @odoo-module **/
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

const { Component } = owl;

export class BomOverviewDisplayFilter extends Component {
    setup() {
        this.displayOptions = {
            availabilities: this.env._t('Availabilities'),
            leadTimes: this.env._t('Lead Times'),
            costs: this.env._t('Costs'),
            operations: this.env._t('Operations'),
        };
    }
    //---- Handlers ----

    onClickDisplay(optionKey) {
        this.props.bus.trigger("change-display", { type: optionKey, value: !this.props.showOptions[optionKey] });
    }

    //---- Getters ----

    get displayableOptions() {
        return Object.keys(this.displayOptions);
    }

    get currentDisplayedNames() {
        return this.displayableOptions.filter(key => this.props.showOptions[key]).map(key => this.displayOptions[key]).join(", ");
    }
}

BomOverviewDisplayFilter.template = "mrp.BomOverviewDisplayFilter";
BomOverviewDisplayFilter.components = {
    Dropdown,
    DropdownItem,
}
BomOverviewDisplayFilter.props = {
    bus: Object,
    showOptions: {
        type: Object,
        shape: {
            availabilities: Boolean,
            costs: Boolean,
            operations: Boolean,
            leadTimes: Boolean,
            uom: Boolean,
            attachments: Boolean,
        },
    },
};

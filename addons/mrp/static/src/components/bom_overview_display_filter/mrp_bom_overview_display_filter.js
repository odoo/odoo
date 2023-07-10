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

    //---- Getters ----

    get displayableOptions() {
        return Object.keys(this.displayOptions);
    }
}

BomOverviewDisplayFilter.template = "mrp.BomOverviewDisplayFilter";
BomOverviewDisplayFilter.components = {
    Dropdown,
    DropdownItem,
}
BomOverviewDisplayFilter.props = {
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
    changeDisplay: Function,
};

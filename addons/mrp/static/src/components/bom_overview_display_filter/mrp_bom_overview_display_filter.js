/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

const { Component } = owl;

export class BomOverviewDisplayFilter extends Component {
    setup() {
        this.displayOptions = {
            availabilities: _t('Availabilities'),
            leadTimes: _t('Lead Times'),
            costs: _t('Costs'),
            operations: _t('Operations'),
        };
    }

    //---- Getters ----

    get displayableOptions() {
        return Object.keys(this.displayOptions).map(optionKey => ({
            id: optionKey,
            label: this.displayOptions[optionKey],
            onSelected: () => this.props.changeDisplay(optionKey),
            class: { o_menu_item: true, selected: this.props.showOptions[optionKey] },
            closingMode: "none",
        }));
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

/** @odoo-module **/

import { ControlPanel } from "@web/search/control_panel/control_panel";
import { BomOverviewDisplayFilter } from "../bom_overview_display_filter/mrp_bom_overview_display_filter";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

const { Component } = owl;

export class BomOverviewControlPanel extends Component {
    setup() {
        this.controlPanelDisplay = {};
        // Cannot use 'control-panel-bottom-right' slot without this, as viewSwitcherEntries doesn't exist in this.env.config here.
        this.env.config.viewSwitcherEntries = [];
    }

    //---- Handlers ----

    updateQuantity(ev) {
        const newVal = isNaN(ev.target.value) ? 1 : parseInt(ev.target.value);
        this.props.changeBomQuantity(newVal);
    }

    onKeyPress(ev) {
        if (ev.keyCode === 13 || ev.which === 13) {
            ev.preventDefault();
            this.updateQuantity(ev);
        }
    }

    clickUnfold() {
        this.env.overviewBus.trigger("unfold-all");
    }
}

BomOverviewControlPanel.template = "mrp.BomOverviewControlPanel";
BomOverviewControlPanel.components = {
    Dropdown,
    DropdownItem,
    ControlPanel,
    BomOverviewDisplayFilter,
};
BomOverviewControlPanel.props = {
    bomQuantity: Number,
    showOptions: Object,
    showVariants: { type: Boolean, optional: true },
    variants: { type: Object, optional: true },
    showUom: { type: Boolean, optional: true },
    uomName: { type: String, optional: true },
    currentWarehouse: Object,
    warehouses: { type: Array, optional: true },
    print: Function,
    changeWarehouse: Function,
    changeVariant: Function,
    changeBomQuantity: Function,
    changeDisplay: Function,
};
BomOverviewControlPanel.defaultProps = {
    variants: {},
    warehouses: [],
};

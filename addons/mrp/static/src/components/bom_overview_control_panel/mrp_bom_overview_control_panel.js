/** @odoo-module **/

import { ControlPanel } from "@web/search/control_panel/control_panel";
import { BomOverviewDisplayFilter } from "../bom_overview_display_filter/mrp_bom_overview_display_filter";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class BomOverviewControlPanel extends Component {
    static template = "mrp.BomOverviewControlPanel";
    static components = {
        Dropdown,
        DropdownItem,
        ControlPanel,
        BomOverviewDisplayFilter,
        Many2XAutocomplete,
    };
    static props = {
        bomQuantity: Number,
        showOptions: Object,
        showVariants: { type: Boolean, optional: true },
        variants: { type: Object, optional: true },
        data: { type: Object, optional: true },
        showUom: { type: Boolean, optional: true },
        uomName: { type: String, optional: true },
        currentWarehouse: Object,
        warehouses: { type: Array, optional: true },
        print: Function,
        changeWarehouse: Function,
        changeVariant: Function,
        changeBomQuantity: Function,
        changeDisplay: Function,
        precision: Number,
    };
    static defaultProps = {
        variants: {},
        warehouses: [],
    };

    setup() {
        this.action = useService("action");
        this.controlPanelDisplay = {};
    }

    //---- Handlers ----

    updateQuantity(ev) {
        const newVal = isNaN(ev.target.value) ? 1 : parseFloat(parseFloat(ev.target.value).toFixed(this.precision));
        this.props.changeBomQuantity(newVal);
    }

    onKeyPress(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            this.updateQuantity(ev);
        }
    }

    clickUnfold() {
        this.env.overviewBus.trigger("unfold-all");
    }

    getDomain() {
        const keys = Object.keys(this.props.variants);
        return [['id', 'in', keys]];
    }

    async manufactureFromBoM() {
        return this.action.doAction("mrp.manufacture_from_bom", {
            additionalContext: {
                default_bom_id: this.props.data.bom_id
            },
        });
    }

    get precision() {
        return this.props.precision;
    }

    get warehousesItems() {
        return this.props.warehouses.map(wh => ({
            id: wh.id,
            label: wh.name,
            class: { selected: wh.name === this.props.currentWarehouse.name },
            onSelected: () => this.props.changeWarehouse(wh.id)
        }));
    }
}

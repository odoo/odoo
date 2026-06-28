import { useRef } from "@web/owl2/utils";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { BomOverviewDisplayFilter } from "../bom_overview_display_filter/mrp_bom_overview_display_filter";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { Component, onMounted, props, t } from "@odoo/owl";
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
    props = props({
        bomQuantity: t.number(),
        showOptions: t.object(),
        showVariants: t.boolean().optional(),
        variants: t.object().optional({}),
        data: t.object().optional(),
        uomName: t.string().optional(),
        currentWarehouse: t.object().optional(),
        warehouses: t.array().optional([]),
        print: t.function(),
        changeWarehouse: t.function(),
        changeVariant: t.function(),
        changeBomQuantity: t.function(),
        changeMode: t.function(),
        precision: t.number(),
        foldable: t.boolean(),
        allFolded: t.boolean(),
    });

    setup() {
        this.action = useService("action");
        this.controlPanelDisplay = {};
        if(this.props.showOptions.mode == "forecast") {
            this.quantity = useRef("quantity");
            onMounted(() => {
                this.quantity.el.focus();
            });
        }
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

    clickTogglefold() {
        this.env.overviewBus.trigger("toggle-fold-all");
    }

    getDomain() {
        const keys = Object.keys(this.props.variants);
        return [['id', 'in', keys]];
    }

    async manufactureFromBoM() {
        const action = {
            res_model: "mrp.production",
            name: "Manufacture Orders",
            type: "ir.actions.act_window",
            views: [[false, "form"]],
            target: "current",
            context: {
                default_bom_id: this.props.data.bom_id,
                bom_overview_picking_type_id: this.props.currentWarehouse.manu_type_id[0],
                bom_overview_product_qty: this.props.bomQuantity,
            },
        };
        return this.action.doAction(action);
    }

    get foldButtonText() {
        return this.props.allFolded ? _t("Unfold") : _t("Fold");
    }

    get precision() {
        return this.props.precision;
    }

    get warehousesItems() {
        return this.props.warehouses.map(wh => ({
            id: wh.id,
            label: wh.name,
            class: { selected: wh.name === this.props.currentWarehouse?.name },
            onSelected: () => this.props.changeWarehouse(wh.id)
        }));
    }
}

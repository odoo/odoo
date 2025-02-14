import { formatFloat, formatMonetary } from "@web/views/fields/formatters";
import { useService } from "@web/core/utils/hooks";
import { BomOverviewLine } from "../bom_overview_line/mrp_bom_overview_line";
import { BomOverviewComponentsBlock } from "../bom_overview_components_block/mrp_bom_overview_components_block";
import { Component } from "@odoo/owl";

export class BomOverviewTable extends Component {
    static template = "mrp.BomOverviewTable";
    static components = {
        BomOverviewLine,
        BomOverviewComponentsBlock,
    };
    static props = {
        showOptions: {
            type: Object,
            shape: {
                mode: String,
                uom: Boolean,
                attachments: Boolean,
            },
        },
        uomName: { type: String, optional: true },
        currentWarehouseId: { type: Number, optional: true },
        data: Object,
        precision: Number,
        bomQuantity: Number,
        changeFolded: Function,
    };

    setup() {
        this.actionService = useService("action");
        this.formatFloat = formatFloat;
        this.formatMonetary = (val) => formatMonetary(val, { currencyId: this.data.currency_id });
    }

    //---- Handlers ----

    async goToProduct() {
        return this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: this.data.link_model,
            res_id: this.data.link_id,
            views: [[false, "form"]],
            target: "current",
            context: {
                active_id: this.data.link_id,
            },
        });
    }

    //---- Getters ----

    get data() {
        return this.props.data;
    }

    get precision() {
        return this.props.precision;
    }

    get forecastMode() {
        return this.props.showOptions.mode == "forecast";
    }

    get showUnitCosts() {
        return this.props.bomQuantity > 1;
    }

    get showUom() {
        return this.props.showOptions.uom;
    }

    get showAttachments() {
        return this.props.showOptions.attachments;
    }
}

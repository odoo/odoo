/** @odoo-module **/

import { formatFloat, formatMonetary } from "@web/views/fields/formatters";
import { useService } from "@web/core/utils/hooks";
import { BomOverviewLine } from "../bom_overview_line/mrp_bom_overview_line";
import { BomOverviewComponentsBlock } from "../bom_overview_components_block/mrp_bom_overview_components_block";
import { Component } from "@odoo/owl";

export class BomOverviewTable extends Component {
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

    get showAvailabilities() {
        return this.props.showOptions.availabilities;
    }

    get showCosts() {
        return this.props.showOptions.costs;
    }

    get showOperations() {
        return this.props.showOptions.operations;
    }

    get showLeadTimes() {
        return this.props.showOptions.leadTimes;
    }

    get showUom() {
        return this.props.showOptions.uom;
    }

    get showAttachments() {
        return this.props.showOptions.attachments;
    }
}

BomOverviewTable.template = "mrp.BomOverviewTable";
BomOverviewTable.components = {
    BomOverviewLine,
    BomOverviewComponentsBlock,
};
BomOverviewTable.props = {
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
    uomName: { type: String, optional: true },
    currentWarehouseId: { type: Number, optional: true },
    data: Object,
    precision: Number,
    changeFolded: Function,
};

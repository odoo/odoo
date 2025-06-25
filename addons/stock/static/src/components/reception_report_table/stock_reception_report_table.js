/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { ReceptionReportLine } from "../reception_report_line/stock_reception_report_line";
import { Component } from "@odoo/owl";

export class ReceptionReportTable extends Component {
    setup() {
        this.actionService = useService("action");
        this.ormService = useService("orm");
    }

    //---- Handlers ----

    async onClickAssignAll() {
        const moveIds = [];
        const quantities = [];
        const inIds = [];
        for (const line of this.props.lines) {
            if (line.is_assigned) continue;
            moveIds.push(line.move_out_id);
            quantities.push(line.quantity);
            inIds.push(line.move_ins);
        }

        await this.ormService.call(
            "report.stock.report_reception",
            "action_assign",
            [false, moveIds, quantities, inIds],
        );
        this.env.bus.trigger("update-assign-state", { isAssigned: true, tableIndex: this.props.index });
    }

    async onClickLink(resModel, resId, viewType) {
        return this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: resModel,
            res_id: resId,
            views: [[false, viewType]],
            target: "current",
        });
    }

    async onClickPrintLabels() {
        const modelIds = [];
        const quantities = [];
        for (const line of this.props.lines) {
            if (!line.is_assigned) continue;
            modelIds.push(line.move_out_id);
            quantities.push(Math.ceil(line.quantity) || 1);
        }
        if (!modelIds.length) {
            return;
        }

        return this.actionService.doAction({
            ...this.props.labelReport,
            context: { active_ids: modelIds },
            data: { docids: modelIds, quantity: quantities.join(",") },
        });
    }

    //---- Getters ----

    get hasMovesIn() {
        return this.props.lines.some(line => line.move_ins && line.move_ins.length > 0);
    }

    get hasAssignAllButton() {
        return this.props.lines.some(line => line.is_qty_assignable);
    }

    get isAssignAllDisabled() {
        return this.props.lines.every(line => line.is_assigned);
    }

    get isPrintLabelDisabled() {
        return this.props.lines.every(line => !line.is_assigned);
    }
}

ReceptionReportTable.template = "stock.ReceptionReportTable";
ReceptionReportTable.components = {
    ReceptionReportLine,
};
ReceptionReportTable.props = {
    index: String,
    scheduledDate: { type: String, optional: true },
    lines: Array,
    source: Array,
    labelReport: Object,
    showUom: Boolean,
    precision: Number,
};

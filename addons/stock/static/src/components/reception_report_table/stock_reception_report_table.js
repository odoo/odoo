import { useService } from "@web/core/utils/hooks";
import { formatFloat } from "@web/views/fields/formatters";
import { Component } from "@odoo/owl";
import { CheckBox } from "@web/core/checkbox/checkbox";

export class ReceptionReportTable extends Component {
    static template = "stock.ReceptionReportTable";
    static components = {
        CheckBox,
    };
    static props = {
        index: String,
        scheduledDate: { type: String, optional: true },
        lines: Array,
        labelReport: Object,
        showUom: Boolean,
        precision: Number,
    };

    setup() {
        this.actionService = useService("action");
        this.ormService = useService("orm");
        this.formatFloat = (val) => formatFloat(val, { digits: [false, this.props.precision] });
    }

    //---- Handlers ----

    async onClickForecast(line) {
        const action = await this.ormService.call(
            "stock.move",
            "action_product_forecast_report",
            [[line.move_out_id]],
        );

        return this.actionService.doAction(action);
    }

    async onClickPrint(line) {
        if (!line.move_out_id) {
            return;
        }
        const modelIds = [line.move_out_id];
        const productQtys = [Math.ceil(line.quantity) || '1'];

        return this.actionService.doAction({
            ...this.props.labelReport,
            context: { active_ids: modelIds },
            data: { docids: modelIds, quantity: productQtys.join(",") },
        });
    }

    async onClickAssign(line) {
        await this.ormService.call(
            "report.stock.report_reception",
            "action_assign",
            [false, [line.move_out_id], [line.quantity], [line.move_ins]],
        );
        this.env.bus.trigger("update-assign-state", { isAssigned: true, tableIndex: this.props.index, lineIndex: line.index });
    }

    async onClickUnassign(line) {
        const done = await this.ormService.call(
            "report.stock.report_reception",
            "action_unassign",
            [false, line.move_out_id, line.quantity, line.move_ins]
        )
        if (done) {
            this.env.bus.trigger("update-assign-state", { isAssigned: false, tableIndex: this.props.index, lineIndex: line.index });
        }
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

    //---- Getters ----

    get totalQuantity() {
        return this.props.lines.reduce((acc, line) => acc + line.quantity, 0);
    }

    get hasContent() {
        return this.props.lines.length > 0 && this.props.lines[0].source.length > 0;
    }
}

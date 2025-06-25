import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { ReceptionReportTable } from "../reception_report_table/stock_reception_report_table";
import { Component, onWillStart, useState } from "@odoo/owl";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

export class ReceptionReportMain extends Component {
    static template = "stock.ReceptionReportMain";
    static components = {
        ControlPanel,
        ReceptionReportTable,
    };
    static props = { ...standardActionServiceProps };

    setup() {
        this.controlPanelDisplay = {};
        this.ormService = useService("orm");
        this.actionService = useService("action");
        this.reportName = "stock.report_reception";
        this.labelReportName = "stock.report_reception_report_label";
        this.state = useState({
            sourcesToLines: {},
        });
        useBus(this.env.bus, "update-assign-state", (ev) => this._changeAssignedState(ev.detail));

        onWillStart(async () => {
            // Check the URL if report was alreadu loaded.
            let defaultDocIds;
            const { rfield, rids } = this.props.action.context.params || {};
            if (rfield && rids) {
                const parsedIds = JSON.parse(rids);
                defaultDocIds = [rfield, parsedIds instanceof Array ? parsedIds : [parsedIds]];
            } else {
                defaultDocIds = Object.entries(this.context).find(([k,v]) => k.startsWith("default_"));
                if (!defaultDocIds) {
                    // If nothing could be found, just ask for empty data.
                    defaultDocIds = [false, [0]];
                }
            }
            this.contextDefaultDoc = { field: defaultDocIds[0], ids: defaultDocIds[1] };

            if (this.contextDefaultDoc.field) {
                // Add the fields/ids to the URL, so we can properly reload them after a page refresh.
                this.props.updateActionState({ rfield: this.contextDefaultDoc.field, rids: JSON.stringify(this.contextDefaultDoc.ids) });
            }
            this.data = await this.getReportData();
            this.state.sourcesToLines = this.data.sources_to_lines;

            const matchingReports = await this.ormService.searchRead("ir.actions.report", [
                ["report_name", "in", [this.reportName, this.labelReportName]],
            ]);
            this.receptionReportAction = matchingReports.find(
                (report) => report.report_name === this.reportName
            );
            this.receptionReportLabelAction = matchingReports.find(
                (report) => report.report_name === this.labelReportName
            );
        });
    }

    async getReportData() {
        const context = { ...this.context, [this.contextDefaultDoc.field]: this.contextDefaultDoc.ids };
        const args = [
            this.contextDefaultDoc.ids,
            { context, report_type: "html" },
        ];
        return this.ormService.call(
            "report.stock.report_reception",
            "get_report_data",
            args,
            { context },
        );
    }

    //---- Handlers ----

    async onClickAssignAll() {
        const moveIds = [];
        const quantities = [];
        const inIds = [];

        for (const lines of Object.values(this.state.sourcesToLines)) {
            for (const line of lines) {
                if (line.is_assigned) continue;
                moveIds.push(line.move_out_id);
                quantities.push(line.quantity);
                inIds.push(line.move_ins);
            }
        }

        await this.ormService.call(
            "report.stock.report_reception",
            "action_assign",
            [false, moveIds, quantities, inIds],
        );
        this._changeAssignedState({ isAssigned: true });
    }

    async onClickTitle(docId) {
        return this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: this.data.doc_model,
            res_id: docId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    onClickPrint() {
        return this.actionService.doAction({
            ...this.receptionReportAction,
            context: { [this.contextDefaultDoc.field]: this.contextDefaultDoc.ids },
        });
    }

    onClickPrintLabels() {
        const modelIds = [];
        const quantities = [];

        for (const lines of Object.values(this.state.sourcesToLines)) {
            for (const line of lines) {
                if (!line.is_assigned) continue;
                modelIds.push(line.move_out_id);
                quantities.push(Math.ceil(line.quantity) || 1);
            }
        }
        if (!modelIds.length) {
            return;
        }

        return this.actionService.doAction({
            ...this.receptionReportLabelAction,
            context: { active_ids: modelIds },
            data: { docids: modelIds, quantity: quantities.join(",") },
        });
    }

    //---- Utils ----

    _changeAssignedState(options) {
        const { isAssigned, tableIndex, lineIndex } = options;

        for (const [tabIndex, lines] of Object.entries(this.state.sourcesToLines)) {
            if (tableIndex && tableIndex != tabIndex) continue;
            lines.forEach(line => {
                if (isNaN(lineIndex) || lineIndex == line.index) {
                    line.is_assigned = isAssigned;
                }
            });
        }
    }

    //---- Getters ----

    get context() {
        return this.props.action.context;
    }

    get hasContent() {
        return this.data.sources_to_lines && Object.keys(this.data.sources_to_lines).length > 0;
    }

    get isAssignAllDisabled() {
        return Object.values(this.state.sourcesToLines).every(lines => lines.every(line => line.is_assigned || !line.is_qty_assignable));
    }

    get isPrintLabelDisabled() {
        return Object.values(this.state.sourcesToLines).every(lines => lines.every(line => !line.is_assigned));
    }
}

registry.category("actions").add("reception_report", ReceptionReportMain);

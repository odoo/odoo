/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { ReceptionReportTable } from "../reception_report_table/stock_reception_report_table";

const { Component, onWillStart, useState } = owl;

export class ReceptionReportMain extends Component {
    setup() {
        this.controlPanelDisplay = {
            "top-right": false,
            "bottom-right": false,
        };
        this.ormService = useService("orm");
        this.actionService = useService("action");
        this.reportName = "stock.report_reception";
        const defaultDocIds = Object.entries(this.context).find(([k,v]) => k.startsWith("default_"));
        this.contextDefaultDoc = { field: defaultDocIds[0], ids: defaultDocIds[1] };
        this.state = useState({
            sourcesToLines: {},
        });
        useBus(this.env.bus, "update-assign-state", (ev) => this._changeAssignedState(ev.detail));

        onWillStart(async () => {
            this.data = await this.getReportData();
            this.state.sourcesToLines = this.data.sources_to_lines;
        });
    }

    async getReportData() {
        const args = [
            this.contextDefaultDoc.ids,
            { context: this.context, report_type: "html" },
        ];
        return this.ormService.call(
            "report.stock.report_reception",
            "get_report_data",
            args,
            { context: this.context }
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
            type: "ir.actions.report",
            report_type: "qweb-pdf",
            report_name: `${this.reportName}/?context={"${this.contextDefaultDoc.field}": ${JSON.stringify(this.contextDefaultDoc.ids)}}`,
            report_file: this.reportName,
        });
    }

    onClickPrintLabels() {
        const reportFile = 'stock.report_reception_report_label';
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
            type: "ir.actions.report",
            report_type: "qweb-pdf",
            report_name: `${reportFile}?docids=${modelIds}&quantity=${quantities}`,
            report_file: reportFile,
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

ReceptionReportMain.components = {
    ControlPanel,
    ReceptionReportTable,
};
ReceptionReportMain.template = "stock.ReceptionReportMain";

registry.category("actions").add("reception_report", ReceptionReportMain);

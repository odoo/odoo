/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Component, onWillStart, useState } from "@odoo/owl";
import { download } from "@web/core/network/download";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useSetupAction } from "@web/search/action_hook";
import { Layout } from "@web/search/layout";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

function processLine(line) {
    return { ...line, lines: [], isFolded: true };
}

function extractPrintData(lines) {
    const data = [];
    for (const line of lines) {
        const { id, model_id, model, unfoldable, level } = line;
        data.push({
            id: id,
            model_id: model_id,
            model_name: model,
            unfoldable,
            level: level || 1,
        });
        if (!line.isFolded) {
            data.push(...extractPrintData(line.lines));
        }
    }
    return data;
}

export class TraceabilityReport extends Component {
    static template = "stock.TraceabilityReport";
    static components = { Layout };
    static props = { ...standardActionServiceProps };

    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");

        onWillStart(this.onWillStart);
        useSetupAction({
            getLocalState: () => ({
                lines: [...this.state.lines],
            }),
        });

        this.state = useState({
            lines: this.props.state?.lines || [],
        });

        const { active_id, active_model, auto_unfold, context, lot_name, ttype, url } =
            this.props.action.context;
        this.controllerUrl = url;

        this.context = context || {};
        Object.assign(this.context, {
            active_id: active_id || this.props.action.params.active_id,
            auto_unfold: auto_unfold || false,
            model: active_model || this.props.action.context.params?.active_model || false,
            lot_name: lot_name || false,
            ttype: ttype || false,
        });

        if (this.context.model) {
            this.props.updateActionState({ active_model: this.context.model });
        }

        this.display = {
            controlPanel: {},
            searchPanel: false,
        };
    }

    async onWillStart() {
        if (!this.state.lines.length) {
            const mainLines = await this.orm.call("stock.traceability.report", "get_main_lines", [
                this.context,
            ]);
            this.state.lines = mainLines.map(processLine);
        }
    }

    onClickBoundLink(line) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: line.res_model,
            res_id: line.res_id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    onCLickOpenLot(line) {
        this.actionService.doAction({
            type: "ir.actions.client",
            tag: "stock_report_generic",
            name: line.lot_name !== undefined && line.lot_name.toString(),
            context: {
                active_id: line.lot_id,
                active_model: "stock.lot",
                url: "/stock/output_format/stock?active_id=:active_id&active_model=:active_model",
            },
        });
    }

    onClickUpDownStream(line) {
        this.actionService.doAction({
            type: "ir.actions.client",
            tag: "stock_report_generic",
            name: _t("Traceability Report"),
            context: {
                active_id: line.model_id,
                active_model: line.model,
                auto_unfold: true,
                lot_name: line.lot_name !== undefined && line.lot_name,
                url: "/stock/output_format/stock/active_id",
            },
        });
    }

    onClickPrint() {
        const data = JSON.stringify(extractPrintData(this.state.lines));
        const url = this.controllerUrl
            .replace(":active_id", this.context.active_id)
            .replace(":active_model", this.context.model)
            .replace("output_format", "pdf");

        download({
            data: { data },
            url,
        });
    }

    async toggleLine(line) {
        line.isFolded = !line.isFolded;
        if (!line.lines.length) {
            line.lines = (
                await this.orm.call("stock.traceability.report", "get_lines", [line.id], {
                    model_id: line.model_id,
                    model_name: line.model,
                    level: line.level + 30 || 1,
                })
            ).map(processLine);
        }
    }
}

registry.category("actions").add("stock_report_generic", TraceabilityReport);

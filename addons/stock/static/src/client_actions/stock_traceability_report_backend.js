import { Component, onWillStart, proxy } from "@odoo/owl";
import { download } from "@web/core/network/download";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useSetupAction } from "@web/search/action_hook";
import { Layout } from "@web/search/layout";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

function processLine(line, lines=[], keepFolded=true) {
    return { ...line, lines: lines, isFolded: keepFolded };
}

function hasFoldedLine(lines) {
    return lines.some(
        (line) => (line.unfoldable && line.isFolded) || hasFoldedLine(line.lines)
    );
}

function extractPrintData(lines) {
    const data = [];
    for (const line of lines) {
        const { id, record_id, model_name, line_type, unfoldable, level } = line;
        if (line_type === 'parent') {
            data.push({
                id: id,
                record_id: record_id,
                model_name: model_name,
                line_type: line_type,
                unfoldable: unfoldable,
                level: level || 1,
            });
            if (!line.isFolded) {
                data.push(...extractPrintData(line.lines));
            }
        } else {
            data.unshift({
                id: id,
                record_id: record_id,
                model_name: model_name,
                line_type: line_type,
                unfoldable: unfoldable,
                level: level || 1,
            });
            if (!line.isFolded) {
                data.unshift(...extractPrintData(line.lines));
            }
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

        this.state = proxy({
            lines: this.props.state?.lines || [],
        });
        this.hasUnfoldableLines = this.state.lines.some((line) => line.unfoldable);
        this.isExpanded = false;

        const { active_id, active_model, context, lot_name, ttype, url, lang } =
            this.props.action.context;
        this.controllerUrl = url;

        this.context = context || {};
        Object.assign(this.context, {
            active_id: active_id || this.props.action.params.active_id,
            model: active_model || this.props.action.context.params?.active_model || false,
            lot_name: lot_name || false,
            ttype: ttype || false,
            lang: lang || false,
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
            this.state.lines = mainLines.map(
                (line) => { return processLine(line); }
            );
            this.hasUnfoldableLines = this.state.lines.some((line) => line.unfoldable);
        }
    }

    get hasFoldedLines() {
        return hasFoldedLine(this.state.lines);
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

    onClickPartner(line) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "res.partner",
            res_id: line.partner_id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    onClickOpenLot(line) {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'stock.lot',
            res_id: line.lot_id,
            views: [[false, 'form']],
            target: 'current',
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

    async onClickUnfold() {
        const unfoldLines = (lines) => {
            for (const line of lines) {
                if (line.unfoldable) {
                    if (line.isFolded) {
                        line.isFolded = !line.isFolded;
                    }
                    unfoldLines(line.lines);
                }
            }
        };
        if (!this.isExpanded) {
            this.state.lines = (
                await this.orm.call("stock.traceability.report", "get_expanded_lines", [this.context])
            ).map(
                (line) => { return processLine(line, line.lines, false); }
            );
            this.isExpanded = true;
        } else {
            unfoldLines(this.state.lines);
        }
    }

    onClickFold() {
        const foldLines = (lines) => {
            for (const line of lines) {
                if (!line.isFolded) {
                    line.isFolded = !line.isFolded;
                }
                foldLines(line.lines);
            }
        };
        foldLines(this.state.lines);
    }

    async toggleLine(line, line_type=false) {
        if (line.isFolded && !line.lines.length) {
            line.lines = (
                await this.orm.call("stock.traceability.report", "get_lines", [line_type], {
                    record_id: line.record_id,
                    model_name: line.model_name,
                    level: line.level + 30 || 1,
                })
            ).map(
                (line) => { return processLine(line); }
            );
        }
        line.isFolded = !line.isFolded;
    }
}

registry.category("actions").add("stock_report_generic", TraceabilityReport);

import { patch } from "@web/core/utils/patch";
import * as spreadsheet from "@odoo/o-spreadsheet";
import { _t } from "@web/core/l10n/translation";
import { navigateToOdoolinkFromChart } from "../odoo_chart/odoo_chart_helpers";
import { SEE_RECORD_LIST, SEE_RECORD_LIST_VISIBLE } from "../../list/list_actions";
import { SEE_RECORDS_PIVOT, SEE_RECORDS_PIVOT_VISIBLE } from "../../pivot/pivot_actions";

const { computeCachedTextDimension } = spreadsheet.helpers;

patch(spreadsheet.components.FigureComponent.prototype, {
    get chartId() {
        if (this.props.figureUI.tag !== "chart" && this.props.figureUI.tag !== "carousel") {
            return undefined;
        }
        return this.env.model.getters.getChartIdFromFigureId(this.props.figureUI.id);
    },
    async navigateToOdooLink(newWindow) {
        await navigateToOdoolinkFromChart(this.env, this.chartId, newWindow);
    },
    get hasOdooLink() {
        return this.env.model.getters.getChartOdooLink(this.chartId) !== undefined;
    },
});

function inSection(ctx, mouseY, sectionY, sectionFont) {
    const sectionHeight = computeCachedTextDimension(ctx, "text", sectionFont).height;
    return sectionY - sectionHeight - 5 < mouseY && mouseY < sectionY + 5;
}

patch(spreadsheet.components.ScorecardChart.prototype, {
    async navigateToOdooLink(newWindow) {
        await navigateToOdoolinkFromChart(this.env, this.props.chartId, newWindow);
    },
    get hasOdooLink() {
        return this.env.model.getters.getChartOdooLink(this.props.chartId) !== undefined;
    },
    getEventTargetSection(ev) {
        const canvasRect = this.canvas().getBoundingClientRect();
        const ctx = this.canvas().getContext("2d");
        const zoom = this.env.model.getters.getViewportZoomLevel();
        const config = this.config(canvasRect, zoom);

        const y = (ev.clientY - canvasRect.top) / zoom;

        if (config.title && inSection(ctx, y, config.title.position.y, config.title.style.font)) {
            return "TITLE";
        } else if (config.key && inSection(ctx, y, config.key.position.y, config.key.style.font)) {
            return "KEY";
        } else if (
            config.baseline &&
            inSection(ctx, y, config.baseline.position.y, config.baseline.style.font)
        ) {
            return "BASELINE";
        } else {
            return "NONE";
        }
    },
    async onClick(ev, isMiddleClick) {
        if (!this.env.model.getters.isDashboard()) {
            return;
        }
        const section = this.getEventTargetSection(ev);
        if (section === "KEY" || section === "BASELINE") {
            const def = this.env.model.getters.getChartDefinition(this.props.chartId);
            const positionString = section === "KEY" ? def.keyValue : def.baseline;
            const range = this.env.model.getters.getRangeFromSheetXC(
                this.env.model.getters.getActiveSheetId(),
                positionString
            );
            let position = undefined;
            if (!range.invalidSheetName && range.sheetId) {
                position = { col: range.zone.left, row: range.zone.top, sheetId: range.sheetId };
            }
            if (position && SEE_RECORD_LIST_VISIBLE(position, this.env.model.getters)) {
                await SEE_RECORD_LIST(position, this.env, isMiddleClick);
                return;
            } else if (position && SEE_RECORDS_PIVOT_VISIBLE(position, this.env.model.getters)) {
                await SEE_RECORDS_PIVOT(position, this.env, isMiddleClick);
                return;
            }
        }
        if (this.hasOdooLink) {
            await this.navigateToOdooLink(isMiddleClick);
        }
    },
    onMouseMove(ev) {
        if (!this.env.model.getters.isDashboard()) {
            return;
        }
        const section = this.getEventTargetSection(ev);
        if (this.currentSection === section) {
            return;
        }
        let tooltip = "";
        this.currentSection = section;
        this.currentHighlight = undefined;
        if (section === "KEY" || section === "BASELINE") {
            const def = this.env.model.getters.getChartDefinition(this.props.chartId);
            const positionString = section === "KEY" ? def.keyValue : def.baseline;
            const range = this.env.model.getters.getRangeFromSheetXC(
                this.env.model.getters.getActiveSheetId(),
                positionString
            );
            let position = undefined;
            if (!range.invalidSheetName && range.sheetId) {
                position = { col: range.zone.left, row: range.zone.top, sheetId: range.sheetId };
            }
            if (position && SEE_RECORD_LIST_VISIBLE(position, this.env.model.getters)) {
                tooltip = section === "KEY" ? _t("Go to Key record") : _t("Go to Baseline record");
                this.currentHighlight = this.currentSection;
            } else if (position && SEE_RECORDS_PIVOT_VISIBLE(position, this.env.model.getters)) {
                tooltip =
                    section === "KEY" ? _t("Go to Key records") : _t("Go to Baseline records");
                this.currentHighlight = this.currentSection;
            }
        }
        if (!tooltip && this.hasOdooLink) {
            tooltip = _t("Go to link");
        }
        const canvas = this.canvas();
        if (tooltip) {
            canvas.title = tooltip;
            canvas.style = "cursor:pointer;";
        } else {
            canvas.title = "";
            canvas.style = "cursor:default;";
        }
        this.createChart();
    },
    onMouseLeave() {
        if (this.currentHighlight) {
            this.currentHighlight = undefined;
            this.currentSection = undefined;
            this.createChart();
        }
    },
    get runtime() {
        const runtime = this.env.model.getters.getChartRuntime(this.props.chartId);
        if (this.currentHighlight === "KEY") {
            runtime.keyHighlight = true;
            runtime.baselineHighlight = false;
        } else if (this.currentHighlight === "BASELINE") {
            runtime.keyHighlight = false;
            runtime.baselineHighlight = true;
        } else {
            runtime.keyHighlight = false;
            runtime.baselineHighlight = false;
        }
        return runtime;
    },
});

patch(spreadsheet.components.GaugeChartComponent.prototype, {
    async navigateToOdooLink(newWindow) {
        await navigateToOdoolinkFromChart(this.env, this.props.chartId, newWindow);
    },
    get hasOdooLink() {
        return this.env.model.getters.getChartOdooLink(this.props.chartId) !== undefined;
    },
    async onClick() {
        if (this.env.model.getters.isDashboard() && this.hasOdooLink) {
            await this.navigateToOdooLink();
        }
    },
});

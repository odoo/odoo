import { Component } from "@odoo/owl";
import { registries, readonlyAllowedCommands } from "@odoo/o-spreadsheet";

const { chartSubtypeRegistry, chartRegistry } = registries;

readonlyAllowedCommands.add("UPDATE_CHART");

const lineBarPieRegex = /line|bar|pie/;

export class ChartTypeSwitcherMenu extends Component {
    static template = "spreadsheet.ChartTypeSwitcherMenu";
    static components = {};
    static props = { figure: Object };

    setup() {
        super.setup();
        this.originalChartDefinition = this.env.model.getters.getChartDefinition(
            this.props.figure.id
        );
    }

    get shouldBeDisplayed() {
        const definition = this.env.model.getters.getChartDefinition(this.props.figure.id);
        if (!lineBarPieRegex.test(definition.type)) {
            return false;
        }
        return true;
    }

    get availableTypes() {
        const definition = this.env.model.getters.getChartDefinition(this.props.figure.id);
        const types = definition.type.startsWith("odoo")
            ? ["odoo_bar", "odoo_line", "odoo_pie"]
            : ["column", "line", "pie"];
        return types.map((type) => chartSubtypeRegistry.get(type));
    }

    onTypeChange(type) {
        const figureId = this.props.figure.id;
        const currentDefinition = this.env.model.getters.getChartDefinition(figureId);
        if (currentDefinition.type === type) {
            return;
        }

        let definition;
        if (this.originalChartDefinition.type === type) {
            definition = this.originalChartDefinition;
        } else if (type.startsWith("odoo")) {
            const newChartInfo = chartSubtypeRegistry.get(type);
            definition = {
                ...this.originalChartDefinition,
                ...this.env.model.getters.getChartDefinition(figureId),
                type: newChartInfo.chartType,
            };
        } else {
            const newChartInfo = chartSubtypeRegistry.get(type);
            const ChartClass = chartRegistry.get(newChartInfo.chartType);
            const chartCreationContext = this.env.model.getters.getContextCreationChart(figureId);
            definition = {
                ...ChartClass.getChartDefinitionFromContextCreation(chartCreationContext),
                ...newChartInfo.subtypeDefinition,
            };
        }

        this.env.model.dispatch("UPDATE_CHART", {
            definition,
            id: figureId,
            sheetId: this.env.model.getters.getActiveSheetId(),
        });
    }

    get selectedChartType() {
        return this.env.model.getters.getChartDefinition(this.props.figure.id).type;
    }
}

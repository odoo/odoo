import { Component, useState } from "@odoo/owl";
import { registries, readonlyAllowedCommands } from "@odoo/o-spreadsheet";
import { usePopover } from "@web/core/popover/popover_hook";

const { chartSubtypeRegistry, chartRegistry } = registries;

readonlyAllowedCommands.add("UPDATE_CHART");

const lineBarPieRegex = /line|bar|pie/;

export class ChartTypeSwitcherMenu extends Component {
    static template = "spreadsheet.ChartTypeSwitcherMenu";
    static components = {};
    static props = { figure: Object, isFigureHovered: Boolean };

    setup() {
        super.setup();
        this.state = useState({ isPopoverOpen: false });
        this.originalChartDefinition = this.env.model.getters.getChartDefinition(
            this.props.figure.id
        );
        this.popover = usePopover(ChartTypeSwitcherPopover, {
            arrow: false,
            position: "bottom-start",
            onClose: () => (this.state.isPopoverOpen = false),
        });
    }

    shouldBeDisplayed() {
        if (!this.env.model.getters.isChartDefined(this.props.figure.id)) {
            return false;
        }
        const definition = this.env.model.getters.getChartDefinition(this.props.figure.id);
        if (!lineBarPieRegex.test(definition.type)) {
            return false;
        }
        return this.props.isFigureHovered || this.state.isPopoverOpen;
    }

    toggleTypePicker(ev) {
        if (!this.popover.isOpen) {
            this.popover.open(ev.currentTarget, {
                availableTypes: this.availableTypes,
                onTypePicked: this.onTypeChange.bind(this),
                selectedType: this.selectedChartType,
            });
            this.state.isPopoverOpen = true;
        } else {
            this.popover.close();
        }
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
        this.popover.close();
    }

    get selectedChartType() {
        return this.env.model.getters.getChartDefinition(this.props.figure.id).type;
    }
}

export class ChartTypeSwitcherPopover extends Component {
    static template = "spreadsheet.ChartTypeSwitcherPopover";
    static props = {
        onTypePicked: Function,
        availableTypes: Array,
        selectedType: String,
        close: Function,
    };
}

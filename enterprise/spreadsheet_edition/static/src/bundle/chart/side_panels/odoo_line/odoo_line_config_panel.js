/** @odoo-module */

import { CommonOdooChartConfigPanel } from "../common/config_panel";
import { components } from "@odoo/o-spreadsheet";

const { Checkbox } = components;

export class OdooLineChartConfigPanel extends CommonOdooChartConfigPanel {
    static template = "spreadsheet_edition.OdooLineChartConfigPanel";
    static components = {
        ...CommonOdooChartConfigPanel.components,
        Checkbox,
    };

    onUpdateStacked(stacked) {
        this.props.updateChart(this.props.figureId, {
            stacked,
        });
    }
    onUpdateCumulative(cumulative) {
        this.props.updateChart(this.props.figureId, {
            cumulative,
        });
    }
}

/** @odoo-module */

import { CommonOdooChartConfigPanel } from "../common/config_panel";

export class OdooBarChartConfigPanel extends CommonOdooChartConfigPanel {
    onUpdateStacked(ev) {
        this.props.updateChart(this.props.figureId, {
            stacked: ev.target.checked,
        });
    }
}

OdooBarChartConfigPanel.template = "spreadsheet_edition.OdooBarChartConfigPanel";

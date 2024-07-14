/** @odoo-module */

import { CommonOdooChartConfigPanel } from "../common/config_panel";

export class OdooLineChartConfigPanel extends CommonOdooChartConfigPanel {
    onUpdateStacked(ev) {
        this.props.updateChart(this.props.figureId, {
            stacked: ev.target.checked,
        });
    }
    onUpdateCumulative(ev) {
        this.props.updateChart(this.props.figureId, {
            cumulative: ev.target.checked,
        });
    }
}

OdooLineChartConfigPanel.template = "spreadsheet_edition.OdooLineChartConfigPanel";

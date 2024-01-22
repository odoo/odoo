/** @odoo-module **/

import {loadJS} from "@web/core/assets";
import {registry} from "@web/core/registry";

import {Component, onPatched, onWillStart, useEffect, useRef} from "@odoo/owl";

export class PlotlyChartWidgetField extends Component {
    setup() {
        this.divRef = useRef("plotly");

        onWillStart(async () => {
            await loadJS(
                "/web_widget_plotly_chart/static/src/lib/plotly/plotly-2.18.2.min.js"
            );
            this.updatePlotly(this.props.value);
        });

        onPatched(() => {
            this.updatePlotly(this.props.value);
        });

        useEffect(() => {
            this.updatePlotly(this.props.value);
        });
    }
    updatePlotly(value) {
        const value_html = $(value);
        const div = value_html.find(".plotly-graph-div").get(0).outerHTML || "";
        const script = value_html.find("script").get(0).textContent || "";

        if (this.divRef.el) {
            this.divRef.el.innerHTML = div;
            new Function(script)();
        }
    }
}

PlotlyChartWidgetField.template = "web_widget_plotly_chart.PlotlyChartWidgetField";
PlotlyChartWidgetField.supportedTypes = ["char", "text"];

registry.category("fields").add("plotly_chart", PlotlyChartWidgetField);

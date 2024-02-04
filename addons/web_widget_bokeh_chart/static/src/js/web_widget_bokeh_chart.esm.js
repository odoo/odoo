/** @odoo-module **/

import {CharField} from "@web/views/fields/char/char_field";
import {loadBundle} from "@web/core/assets";
import {registry} from "@web/core/registry";
const {onWillStart, markup, onMounted, onPatched, useRef} = owl;

export default class BokehChartWidget extends CharField {
    setup() {
        this.widget = useRef("widget");
        onPatched(() => {
            var script = document.createElement("script");
            script.text = this.json_value.script;
            this.widget.el.append(script);
        });
        onMounted(() => {
            var script = document.createElement("script");
            script.text = this.json_value.script;
            this.widget.el.append(script);
        });
        super.setup();
        onWillStart(() =>
            loadBundle({
                jsLibs: [
                    "/web_widget_bokeh_chart/static/src/lib/bokeh/bokeh-3.1.1.min.js",
                    "/web_widget_bokeh_chart/static/src/lib/bokeh/bokeh-api-3.1.1.min.js",
                    "/web_widget_bokeh_chart/static/src/lib/bokeh/bokeh-widgets-3.1.1.min.js",
                    "/web_widget_bokeh_chart/static/src/lib/bokeh/bokeh-tables-3.1.1.min.js",
                    "/web_widget_bokeh_chart/static/src/lib/bokeh/bokeh-mathjax-3.1.1.min.js",
                    "/web_widget_bokeh_chart/static/src/lib/bokeh/bokeh-gl-3.1.1.min.js",
                ],
            })
        );
    }
    get json_value() {
        var value = JSON.parse(this.props.value);
        if (value) {
            value.div = markup(value.div.trim());
        }
        return value;
    }
}
BokehChartWidget.template = "web_widget_bokeh_chart.BokehChartField";
registry.category("fields").add("bokeh_chart", BokehChartWidget);

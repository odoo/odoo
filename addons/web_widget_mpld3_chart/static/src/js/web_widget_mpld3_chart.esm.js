/** @odoo-module **/

import {loadBundle} from "@web/core/assets";
import {registry} from "@web/core/registry";
const {onWillStart, markup, Component, onMounted, onPatched, useRef} = owl;

class Mpld3ChartJsonWidget extends Component {
    setup() {
        this.widget = useRef("widget");
        onPatched(() => {
            var script = document.createElement("script");
            script.text = this.props.value.script;
            this.widget.el.append(script);
        });
        onMounted(() => {
            var script = document.createElement("script");
            script.text = this.props.value.script;
            this.widget.el.append(script);
        });
        onWillStart(() =>
            loadBundle({
                jsLibs: [
                    "/web_widget_mpld3_chart/static/src/lib/d3/d3.v5.js",
                    "/web_widget_mpld3_chart/static/src/lib/mpld3/mpld3.v0.5.9.js",
                ],
            })
        );
    }
    markup(value) {
        console.log("Marking up...");
        return markup(value);
    }
}
Mpld3ChartJsonWidget.template = "web_widget_mpld3_chart.Mpld3ChartJsonWidget";
registry.category("fields").add("mpld3_chart", Mpld3ChartJsonWidget);

export default Mpld3ChartJsonWidget;

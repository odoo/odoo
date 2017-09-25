odoo.define('web_kanban_gauge.widget', function (require) {
"use strict";

var AbstractField = require('web.AbstractField');
var field_registry = require('web.field_registry');
var utils = require('web.utils');

/**
 * options
 *
 * - max_value: maximum value of the gauge [default: 100]
 * - max_field: get the max_value from the field that must be present in the
 *   view; takes over max_value
 * - gauge_value_field: if set, the value displayed below the gauge is taken
 *   from this field instead of the base field used for
 *   the gauge. This allows to display a number different
 *   from the gauge.
 * - label: lable of the gauge, displayed below the gauge value
 * - label_field: get the label from the field that must be present in the
 *   view; takes over label
 * - title: title of the gauge, displayed on top of the gauge
 * - style: custom style
 */

var GaugeWidget = AbstractField.extend({
    className: "oe_gauge",
    cssLibs: [
        '/web/static/lib/nvd3/nv.d3.css'
    ],
    jsLibs: [
        '/web/static/lib/nvd3/d3.v3.js',
        '/web/static/lib/nvd3/nv.d3.js',
        '/web/static/src/js/libs/nvd3.js'
    ],

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _render: function () {
        // parameters
        var max_value = this.nodeOptions.max_value || 100;
        if (this.nodeOptions.max_field) {
            max_value = this.recordData[this.nodeOptions.max_field];
        }
        var label = this.nodeOptions.label || "";
        if (this.nodeOptions.label_field) {
            label = this.recordData[this.nodeOptions.label_field];
        }
        var title = this.nodeOptions.title || this.field.string;
        // current gauge value
        var val = this.value;
        if (_.isArray(JSON.parse(val))) {
            val = JSON.parse(val);
        }
        var value = _.isArray(val) && val.length ? val[val.length-1].value : val;
        // displayed value under gauge
        var gauge_value = value;
        if (this.nodeOptions.gauge_value_field) {
            gauge_value = this.recordData[this.nodeOptions.gauge_value_field];
        }

        var degree = Math.PI/180,
            width = 200,
            height = 150,
            outerRadius = Math.min(width, height)*0.5,
            innerRadius = outerRadius*0.7,
            fontSize = height/7;

        this.$el.empty().attr('style', this.nodeOptions.style + ';position:relative; display:inline-block;');

        var arc = d3.svg.arc()
                .innerRadius(innerRadius)
                .outerRadius(outerRadius)
                .startAngle(-90*degree);

        var svg = d3.select(this.$el[0])
            .append("svg")
            .attr("width", '100%')
            .attr("height", '100%')
            .attr('viewBox','0 0 '+width +' '+height )
            .attr('preserveAspectRatio','xMinYMin')
            .append("g")
            .attr("transform", "translate(" + (width/2) + "," + (height-(width-height)/2-12) + ")");

        function addText(text, fontSize, dx, dy) {
            return svg.append("text")
                .attr("text-anchor", "middle")
                .style("font-size", fontSize+'px')
                .attr("dy", dy)
                .attr("dx", dx)
                .text(text);
        }
        // top title
        addText(title, 16, 0, -outerRadius-16).style("font-weight",'bold');

        // center value
        addText(utils.human_number(value, 1), fontSize, 0, -2).style("font-weight",'bold');

        // bottom label
        addText(0, 8, -(outerRadius+innerRadius)/2, 12);
        addText(label, 8, 0, 12);
        addText(utils.human_number(max_value, 1), 8, (outerRadius+innerRadius)/2, 12);

        // chart
        svg.append("path")
            .datum({endAngle: Math.PI/2})
            .style("fill", "#ddd")
            .attr("d", arc);

        var foreground = svg.append("path")
            .datum({endAngle: 0})
            .style("fill", "hsl(0,80%,50%)")
            .attr("d", arc);

        var ratio = max_value ? value/max_value : 0;
        var hue = Math.round(ratio*120);

        foreground.transition()
            .style("fill", "hsl(" + hue + ",80%,50%)")
            .duration(1500)
            .call(arcTween, (ratio-0.5)*Math.PI);

        function arcTween (transition, newAngle) {
            transition.attrTween("d", function(d) {
                var interpolate = d3.interpolate(d.endAngle, newAngle);
                return function (t) {
                    d.endAngle = interpolate(t);
                    return arc(d);
                };
            });
        }
    },
});

field_registry.add("gauge", GaugeWidget);

return GaugeWidget;

});

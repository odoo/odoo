odoo.define('website_sale_link_tracker.backend', function (require) {
"use strict";

var WebsiteSaleBackend = require('website_sale.backend');

WebsiteSaleBackend.include({

    events: _.defaults({
        'click .js_utm_selector': '_onClickUtmButton', // Click event on select UTM drop-down button
    }, WebsiteSaleBackend.prototype.events),

    /**
     * @override method from website backendDashboard
     * @private
     */
    render_graphs: function() {
        this._super();
        this.utmGraphData = this.dashboards_data.sales.utm_graph;
        this._renderUtmGraph();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Method used to generate Pie chart, depending on user selected UTM option(campaign, medium, source)
     *
     * @private
     */
    _renderUtmGraph: function() {
        var self = this;
        this.$(".utm_button_name").html(this.btnName); // change drop-down button name
        var utmDataType = this.utmType || 'campaign_id';
        var graphData = this.utmGraphData[utmDataType];
        if (graphData.length) {
            this.$(".o_utm_no_data_img").hide();
            this.$(".o_utm_data_graph").show();

            this.$(".o_utm_data_graph").empty();
            nv.addGraph(function() {
                var utmChart = nv.models.pieChart()
                    .x(function(d) {return d.utm_type; })
                    .y(function(d) {return d.amount_total; })
                    .showLabels(true)
                    .labelThreshold(0.1)
                    .labelType("percent")
                    .showLegend(false)
                    .margin({ "left": 0, "right": 0, "top": 0, "bottom": 0 })
                    .color(['#875a7b', '#21b799', '#E4A900', '#D5653E', '#5B899E', '#E46F78', '#8F8F8F']);

                utmChart.tooltip.valueFormatter(function(value, i) {
                    return self.render_monetary_field(value, self.data.currency);
                });

                var svg = d3.select(".o_utm_data_graph").append("svg");

                svg
                    .attr("height", "15em")
                    .datum(graphData)
                    .call(utmChart);

                nv.utils.windowResize(utmChart.update);
                return utmChart;
            });
        } else {
            this.$(".o_utm_no_data_img").show();
            this.$(".o_utm_data_graph").hide();
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Onchange on UTM dropdown button, this method is called.
     *
     * @private
     */
    _onClickUtmButton: function(ev) {
        this.utmType = $(ev.currentTarget).attr('name');
        this.btnName = $(ev.currentTarget).text();
        this._renderUtmGraph();
    },

});

});

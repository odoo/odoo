odoo.define('website_sale.backend', function (require) {
"use strict";

var WebsiteBackend = require('website.backend.dashboard');
var COLORS = ['#875a7b', '#21b799', '#E4A900', '#D5653E', '#5B899E', '#E46F78', '#8F8F8F'];

WebsiteBackend.include({
    jsLibs: [
        '/web/static/lib/Chart/Chart.js',
    ],

    events: _.defaults({
        'click tr.o_product_template': 'on_product_template',
        'click .js_utm_selector': '_onClickUtmButton',
    }, WebsiteBackend.prototype.events),

    init: function (parent, context) {
        this._super(parent, context);

        this.graphs.push({'name': 'sales', 'group': 'sale_salesman'});
    },

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
            this.$(".o_utm_data_graph").empty().show();
            var $canvas = $('<canvas/>');
            this.$(".o_utm_data_graph").append($canvas);
            var context = $canvas[0].getContext('2d');
            console.log(graphData);

            var data = [];
            var labels = [];
            graphData.forEach(function(pt) {
                data.push(pt.amount_total);
                labels.push(pt.utm_type);
            });
            var config = {
                type: 'pie',
                data: {
                    labels: labels,
                    datasets: [{
                        data: data,
                        backgroundColor: COLORS,
                    }]
                },
                options: {
                    tooltips: {
                        callbacks: {
                            label: function(tooltipItem, data) {
                                var label = data.labels[tooltipItem.index] || '';
                                if (label) {
                                    label += ': ';
                                }
                                var amount = data.datasets[0].data[tooltipItem.index];
                                amount = self.render_monetary_field(amount, self.data.currency);
                                label += amount;
                                return label;
                            }
                        }
                    },
                    legend: {display: false}
                }
            };
            new Chart(context, config);
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

    on_product_template: function (ev) {
        ev.preventDefault();

        var product_tmpl_id = $(ev.currentTarget).data('productId');
        this.do_action({
            type: 'ir.actions.act_window',
            res_model: 'product.template',
            res_id: product_tmpl_id,
            views: [[false, 'form']],
            target: 'current',
        }, {
            on_reverse_breadcrumb: this.on_reverse_breadcrumb,
        });
    },
});
return WebsiteBackend;

});

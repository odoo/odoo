odoo.define('journal_dashboard', function (require) {
'use strict';

var kanban_widgets = require('web_kanban.widgets');

var JournalDashboardGraph = kanban_widgets.AbstractField.extend({
    start: function() {
        this.graph_type = this.$node.attr('graph_type');
        this.data = JSON.parse(this.field.raw_value);
        this.display_graph();
        return this._super();
    },

    display_graph : function() {
        var self = this;
        nv.addGraph(function () {
            self.$svg = self.$el.append('<svg>');

            switch(self.graph_type) {

                case "line":
                    self.$svg.addClass('o_graph_linechart');

                    self.chart = nv.models.lineChart();
                    self.chart.options({
                        x: function(d, u) { return u },
                        margin: {'left': 0, 'right': 0, 'top': 0, 'bottom': 0},
                        showYAxis: false,
                        showLegend: false,
                    });
                    self.chart.xAxis
                        .tickFormat(function(d) {
                            var label = '';
                            _.each(self.data, function(v, k){
                                if (v.values[d] && v.values[d].x){
                                    label = v.values[d].x;
                                }
                            });
                            return label;
                        });
                    self.chart.yAxis
                        .tickFormat(d3.format(',.2f'));

                    break;

                case "bar":
                    self.$svg.addClass('o_graph_barchart');

                    self.chart = nv.models.discreteBarChart()
                        .x(function(d) { return d.label })
                        .y(function(d) { return d.value })
                        .showValues(false)
                        .showYAxis(false)
                        .margin({'left': 0, 'right': 0, 'top': 0, 'bottom': 40});

                    self.chart.xAxis.axisLabel(self.data[0].title);
                    self.chart.yAxis.tickFormat(d3.format(',.2f'));

                    break;
            }
            d3.select(self.$el.find('svg')[0])
                .datum(self.data)
                .transition().duration(1200)
                .call(self.chart);

            self.customize_chart();

            nv.utils.windowResize(self.on_resize);
        });
    },

    on_resize: function(){
        this.chart.update();
        this.customize_chart();
    },

    customize_chart: function(){
        if (this.graph_type === 'bar') {
            // Add classes related to time on each bar of the bar chart
            var bar_classes = _.map(this.data[0].values, function (v, k) {return v.type});

            _.each(this.$('.nv-bar'), function(v, k){
                // classList doesn't work with phantomJS & addClass doesn't work with a SVG element
                $(v).attr('class', $(v).attr('class') + ' ' + bar_classes[k]);
            });
        }
    },

    destroy: function(){
        nv.utils.offWindowResize(this.on_resize);
        this._super();
    },

});


kanban_widgets.registry.add('dashboard_graph', JournalDashboardGraph);

});
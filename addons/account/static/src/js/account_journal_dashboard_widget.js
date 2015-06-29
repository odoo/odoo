odoo.define('journal_dashboard', function (require) {
'use strict';

var kanban_widgets = require('web_kanban.widgets');

var JournalDashboardGraph = kanban_widgets.AbstractField.extend({
    start: function() {
        this.graph_type = this.$node.attr('graph_type');
        this.data = JSON.parse(this.field.raw_value);
        this.display_graph();
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
                        tooltips: true,
                        tooltipContent: function(key, x, y, e, graph) {
                            return self.create_tooltip(x, y, e);
                        },
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
                        .margin({'left': 0, 'right': 0, 'top': 0, 'bottom': 40})
                        .tooltips(true)
                        .tooltipContent(function(key, x, y, e, graph) {
                            return self.create_tooltip(x, y, e);
                        });

                    self.chart.xAxis.axisLabel(self.data[0].title);
                    self.chart.yAxis.tickFormat(d3.format(',.2f'));

                    break;
            }
            d3.select(self.$el.find('svg')[0])
                .datum(self.data)
                .transition().duration(1200)
                .call(self.chart);

            self.customize_chart(self.data);

            nv.utils.windowResize(self.on_resize);
        });
    },

    on_resize: function(){
        this.chart.update();
        this.customize_chart(this.data);
    },

    customize_chart: function(){

        if (this.graph_type === 'bar') {
            // Add classes related to time on each bar of the bar chart
            var bar_classes = _.map(this.data[0].values, function (v, k) {return v.type});

            _.each(this.$('.nv-bar'), function(v, k){
                v.classList.add(bar_classes[k]);
            });
        }
    },

    create_tooltip: function(x, y, e){
        var header = _.findWhere(e.series.values, {x: x})
        header = header && header.name || x;

        var $tooltip = $('<div>').addClass('o_tooltip');

        $('<b>')
            .addClass('o_tooltip_title')
            .html(header)
            .appendTo($tooltip)
        $('<div>')
            .addClass('o_tooltip_content')
            .html('Balance ' + y)
            .appendTo($tooltip)
        return $tooltip[0].outerHTML;
    },

    destroy: function(){
        nv.utils.offWindowResize(this.on_resize);
        this._super();
    },

});


kanban_widgets.registry.add('dashboard_graph', JournalDashboardGraph);

});
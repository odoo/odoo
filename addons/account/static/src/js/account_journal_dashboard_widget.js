odoo.define('journal_dashboard', function (require) {
'use strict';

var kanban_common = require('web_kanban.common');

var JournalDashboardGraph = kanban_common.AbstractField.extend({
    start: function() {
        var self = this;
        self.graph_type = self.$node.attr('graph_type')
        self.display_graph(JSON.parse(self.field.raw_value));
    },
    display_graph : function(data) {
        var self = this;
        nv.addGraph(function () {
            self.$el.append('<svg style="height:75px; overflow:visible;">');
            var type = self.graph_type
            switch(type) {
                case "line":
                    var chart = nv.models.lineChart();
                    chart.options({
                        x: function(d,u) { return u},
                        width: self.$el.find('svg').width(),
                        height: self.$el.find('svg').height(),
                        margin: {'left': 15, 'right':10, 'top':10, 'bottom': 20},
                        showYAxis: false,
                        showLegend: false,
                        tooltips: true,
                        tooltipContent: function(key, x, y, e, graph) {
                            var header = "";
                            $.each(e.series.values, function(k,v){
                                if (v.x === x){
                                    header = v.name;
                                }
                            });
                            return '<h3>' + header + '</h3> <p> Balance ' +  y + '</p>'},
                    });
                    chart.xAxis
                    .tickFormat(function(d) {
                        var label = '';
                        $.each(data, function(el){
                            if (data[el].values[d] && data[el].values[d].x){
                                label = data[el].values[d].x;
                            }
                        });
                        return label;
                    })
                    .showMaxMin(false);
                    chart.yAxis.tickFormat(d3.format(',.2f'));
                    break;
                case "bar":
                    var bar_color = [];
                    $.each(data[0].values, function(k,v){
                        bar_color.push(v.color);
                    })
                    var chart = nv.models.discreteBarChart()
                    .x(function(d) { return d.label })
                    .y(function(d) { return d.value })
                    .width(self.$el.find('svg').width())
                    .height(self.$el.find('svg').height())
                    .showValues(false)
                    .showYAxis(false)
                    .color(bar_color)
                    .margin({'left': 15, 'right':10, 'top':10, 'bottom': 25})
                    .tooltips(true);
                    chart.xAxis.axisLabel(data[0].title);
                    chart.yAxis.tickFormat(d3.format(',.2f'));
                    break;
            }
            self.svg = self.$el.find('svg')[0];
            d3.select(self.svg)
                .datum(data)
                .transition().duration(1200)
                .call(chart);
            nv.utils.windowResize(function() { d3.select(self.svg).call(chart.width(self.$el.find('svg').width()).height(self.$el.find('svg').height())); self.postprocess(); });
            
        });
        //ugly, need to do something else
        setTimeout(function(){self.postprocess();},2000);
        
        
    },
    postprocess: function(){
        var low_rect = $(this.svg).find('rect').filter(function(){return $(this).attr('height') < 1.0 })
        low_rect.attr('height', 1);
    },
});


kanban_common.registry.add('dashboard_graph', JournalDashboardGraph);

});
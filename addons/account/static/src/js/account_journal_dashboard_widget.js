openerp.account.journal_dashboard = function (instance)
{   
    var _t = instance.web._t,
    _lt = instance.web._lt;
    instance.web_kanban.JournalDashboardGraph = instance.web_kanban.AbstractField.extend({
        start: function() {
            var self = this;
            self.graph_type = self.$node.attr('graph_type')
            self.display_graph(JSON.parse(self.field.raw_value));
        },
        display_graph : function(data) {
            var self = this;
            nv.addGraph(function () {
                self.$el.append('<svg>');
                type = self.graph_type
                switch(type) {
                    case "line":
                        var chart = nv.models.lineChart()
                        .x(function (d,u) { return u })
                        // .forceY([0, 100])
                        .width(self.$el.find('svg').width())
                        .height(self.$el.find('svg').height())
                        // .margin({'left': 0, 'right':0})
                        .showLegend(data[0].show_legend || false);
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
                        break
                    case "bar":
                        var chart = nv.models.multiBarChart()
                        .width(self.$el.find('svg').width())
                        .height(self.$el.find('svg').height())
                        .showControls(false)
                        // .forceY([0, 100])
                        .reduceXTicks(false)
                        .showLegend(data[0].show_legend || false);
                        break
                }
                self.svg = self.$el.find('svg')[0];
                d3.select(self.svg)
                    .datum(data)
                    .transition().duration(1200)
                    .call(chart);
                nv.utils.windowResize(function() { d3.select(self.svg).call(chart.width(self.$el.find('svg').width()).height(self.$el.find('svg').height())) });
            });
            
        },
    });
    instance.web_kanban.JournalDashboard = instance.web_kanban.AbstractField.extend({
        start: function(){
            //used to set 2 dashboard per line
            this.$el.parents('.oe_kanban_record').addClass('col-md-6');
        },
    });

    instance.web_kanban.fields_registry.add("dashboard_graph", "instance.web_kanban.JournalDashboardGraph");
    instance.web_kanban.fields_registry.add("dashboard_journal", "instance.web_kanban.JournalDashboard");
};
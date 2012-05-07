/*---------------------------------------------------------
 * OpenERP web_graph
 *---------------------------------------------------------*/

openerp.web_graph = function (instance) {

var QWeb = instance.web.qweb,
     _lt = instance.web._lt;

instance.web.views.add('graph', 'instance.web_graph.GraphView');
instance.web_graph.GraphView = instance.web.View.extend({
    display_name: _lt('Graph'),
    view_type: "graph",

    init: function(parent, dataset, view_id, options) {
        this._super(parent);
        this.set_default_options(options);
        this.dataset = dataset;
        this.view_id = view_id;

        this.mode="pie";          // line, bar, area, pie, radar
        this.orientation=true;    // true: horizontal, false: vertical
        this.stacked=true;

        this.spreadsheet=false;   // Display data gris, allows copy to CSV
        this.forcehtml=false;
        this.legend_container;
        this.legend="top";        // top, inside, no


        this.is_loaded = $.Deferred();
        this.renderer = null;
    },
    destroy: function () {
        if (this.renderer) {
            clearTimeout(this.renderer);
        }
        this._super();
    },

    on_loaded: function(fields_view_get) {
        this.$element.html(QWeb.render("GraphView", {}));

        // Should I add this, in every $(...) call ?
        container = $("#editor-render-body");
        $("#graph_bar,#graph_bar_stacked").click(
            {mode: 'bar', stacked: true, legend: 'top'}, graph_render)

        $("#graph_bar_not_stacked").click(
            {mode: 'bar', stacked: false, legend: 'top'}, graph_render)

        $("#graph_area,#graph_area_stacked").click(
            {mode: "area", stacked: true, legend: "top"}, graph_render);

        $("#graph_area_not_stacked").click(
            {mode: "area", stacked: false, legend: "top"}, graph_render);

        $("#graph_radar").click(
            {orientation: 0, mode: "radar", legend: "inside"}, graph_render);

        $("#graph_pie").click(
            {mode: "pie", legend: "inside"}, graph_render);

        $("#graph_legend_top").click(
            {legend: "top"}, graph_render);

        $("#graph_legend_inside").click(
            {legend: "inside"}, graph_render);

        $("#graph_legend_no").click(
            {legend: "no"}, graph_render);

        $("#graph_line").click(
            {mode: "line"}, graph_render);

        $("#graph_show_data").click(
            function() {
                spreadsheet = ! spreadsheet;
                graph_render();
            }
        );
        $("#graph_switch").click(
            function() {
                orientation = ! orientation;
                graph_render();
            }
        );

        $("#graph_download").click(
            function() {
                var graph;
                if (Flotr.isIE && Flotr.isIE < 9) {
                    alert(
                        "Your browser doesn't allow you to get a bitmap image from the plot, " +
                        "you can only get a VML image that you can use in Microsoft Office."
                    );
                }
                if (legend=="top") legend="inside";
                forcehtml = true;
                graph = graph_render();
                graph.download.saveImage('png');
                forcehtml = false;
            }
        );

        this._super();
    },

    get_format: function get_format(options) {
         var result = {
            show: this.legend!='no',
        }
        if (legend=="top") {
            result.noColumns = 4;
            // todo: I guess I should add something like this.renderer ?
            result.container = $("div .graph_header_legend", this)[0];
        } else if (legend=="inside") {
            result.position = 'nw';
            result.backgroundColor = '#D2E8FF';
        }
        return $.extend({
            legend: result,
            mouse: {
                track: true,
                relative: true
            },
            spreadsheet : {
                show: this.spreadsheet,
                initialTab: "data"
            },
            HtmlText : (options && options.labelsAngle)?false:!this.forcehtml,
        }, options)
    },

    graph_get_data: function (options) {
        var i,
            d1 = [],
            d2 = [],
            d3 = [];
        for (i = -3; i < 3; i++) {
            if (this.orientation % 2) {
                d1.push([Math.random(), i]);
                d2.push([Math.random(), i]);
                d3.push([Math.random(), i]);
            } else {
                d1.push([i, Math.random()]);
                d2.push([i, Math.random()]);
                d3.push([i, Math.random()]);
            }
        };
        return [
                $.extend({ data : d2, label : 'Serie 2'}, options),
                $.extend({ data : d3, label : 'Serie 3'}, options),
                $.extend({ data : d1, label : 'Serie 1'}, options),
        ];
    },


    graph_bar: function (container, data) {
        return Flotr.draw(container, data, get_format({
                bars : {
                    show : true,
                    stacked : this.stacked,
                    horizontal : this.orientation,
                    barWidth : 0.7,
                    lineWidth : 1
                },
                grid : {
                    verticalLines : this.orientation,
                    horizontalLines : !this.orientation,
                    outline : "sw",
                },
                labelsAngle: 45
            })
        )
    },

    graph_pie: function (container, data) {
        return Flotr.draw(container, data, get_format({
                pie : {
                    show: true
                },
                grid : {
                    verticalLines : false,
                    horizontalLines : false,
                    outline : "",
                },
                xaxis :  {showLabels: false},
                yaxis :  {showLabels: false},
            })
        )
    }

    graph_radar: function (container, data) {
        return Flotr.draw(container, data, get_format({
                radar : {
                    show : true,
                    stacked : this.stacked
                },
                grid : {
                    circular : true,
                    minorHorizontalLines : true
                }
            })
        )
    }

    graph_line: function (container, data) {
        return Flotr.draw(container, data, get_format({
                lines : {
                    show : true,
                    stacked : this.stacked
                },
                grid : {
                    verticalLines : this.orientation,
                    horizontalLines : !this.orientation,
                    outline : "sw",
                },
                labelsAngle : 45
            })
        )
    }

    // Render the graph and update menu styles
    graph_render: function (options) {
        var graph, data, mode_options, i;

        if (options)
            for (i in options.data)
                this[i] = options.data[i];

        mode_options = (this.mode=='area')?{lines: {fill: true}}:{}

        // Render the graph
        $(".graph_header_legend").children().remove()
        data = this.get_data(mode_options);
        graph = {
            radar: graph_radar,
            pie: graph_pie,
            bar: graph_bar,
            area: graph_line,
            line: graph_line
        }[this.mode](container, data)

        // Update styles of menus

        $("a[id^='graph_']").removeClass("active");
        $("a[id='graph_"+mode+"']").addClass("active");
        $("a[id='graph_"+mode+(this.stacked?"_stacked":"_not_stacked")+"']").addClass("active");

        if (this.legend=='inside')
            $("a[id='graph_legend_inside']").addClass("active");
        else if (this.legend=='top')
            $("a[id='graph_legend_top']").addClass("active");
        else
            $("a[id='graph_legend_no']").addClass("active");

        if (this.spreadsheet)
            $("a[id='graph_show_data']").addClass("active");
        return graph;
    }


    schedule_chart: function(results) {
        self.graph_render(...)
    },

    // render the graph using the domain, context and group_by
    // calls the 'graph_data_get' python controller to process all data
    do_search: function(domain, context, group_by) {
        var self = this;
        return $.when(this.is_loaded).pipe(function() {
            // todo: find the right syntax to perform an Ajax call
            return self.rpc.graph_get_data(self.view_id, domain, context, group_by).then($.proxy(self, 'schedule_chart'));
        });
    },

    do_show: function() {
        this.do_push_state({});
        return this._super();
    },

});
};

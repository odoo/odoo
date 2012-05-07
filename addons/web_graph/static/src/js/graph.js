/*---------------------------------------------------------
 * OpenERP web_graph
 *---------------------------------------------------------*/

openerp.web_graph = function (instance) {

var QWeb = instance.web.qweb,
     _lt = instance.web._lt;

instance.web.views.add('graph', 'instance.web_graph.GraphView');
instance.web_graph.GraphView = instance.web.View.extend({
    template: "GraphView",
    display_name: _lt('Graph'),
    view_type: "graph",

    init: function(parent, dataset, view_id, options) {
        this._super(parent);
        this.set_default_options(options);
        this.dataset = dataset;
        this.view_id = view_id;

        this.mode="bar";          // line, bar, area, pie, radar
        this.orientation=true;    // true: horizontal, false: vertical
        this.stacked=true;

        this.spreadsheet=false;   // Display data gris, allows copy to CSV
        this.forcehtml=false;
        this.legend_container;
        this.legend="top";        // top, inside, no

        this.domain = [];
        this.context = {};
        this.group_by = {};


        this.is_loaded = $.Deferred();
        this.graph = null;
    },
    destroy: function () {
        if (this.graph)
            this.graph.destroy();
        this._super();
    },

    on_loaded: function(fields_view_get) {
        // TODO: move  to load_view and document
        var width, height;
        var self = this;
        this.fields_view = fields_view_get;
        this.container = this.$element.find("#editor-render-body");

        width = this.$element.parent().width();
        this.container.css("width", width);
        this.$element.css("width", width);
        this.container.css("height", Math.min(500, width*0.8));
        this.container = this.container[0];

        this.$element.find("#graph_bar,#graph_bar_stacked").click(
            {mode: 'bar', stacked: true, legend: 'top'}, $.proxy(this,"graph_render"))

        this.$element.find("#graph_bar_not_stacked").click(
            {mode: 'bar', stacked: false, legend: 'top'}, $.proxy(this,"graph_render"))

        this.$element.find("#graph_area,#graph_area_stacked").click(
            {mode: "area", stacked: true, legend: "top"}, $.proxy(this,"graph_render"));

        this.$element.find("#graph_area_not_stacked").click(
            {mode: "area", stacked: false, legend: "top"}, $.proxy(this,"graph_render"));

        this.$element.find("#graph_radar").click(
            {orientation: 0, mode: "radar", legend: "inside"}, $.proxy(this,"graph_render"));

        this.$element.find("#graph_pie").click(
            {mode: "pie", legend: "inside"}, $.proxy(this,"graph_render"));

        this.$element.find("#graph_legend_top").click(
            {legend: "top"}, $.proxy(self,"graph_render"));

        this.$element.find("#graph_legend_inside").click(
            {legend: "inside"}, $.proxy(self,"graph_render"));

        this.$element.find("#graph_legend_no").click(
            {legend: "no"}, $.proxy(self,"graph_render"));

        this.$element.find("#graph_line").click(
            {mode: "line"}, $.proxy(this,"graph_render"));

        this.$element.find("#graph_show_data").click(
            function() {
                self.spreadsheet = ! self.spreadsheet;
                self.graph_render();
            }
        );
        this.$element.find("#graph_switch").click(
            function() {
                self.orientation = ! self.orientation;
                self.graph_render();
            }
        );

        this.$element.find("#graph_download").click(
            function() {
                var graph;
                if (Flotr.isIE && Flotr.isIE < 9) {
                    alert(
                        "Your browser doesn't allow you to get a bitmap image from the plot, " +
                        "you can only get a VML image that you can use in Microsoft Office."
                    );
                }
                if (self.legend=="top") self.legend="inside";
                self.forcehtml = true;
                graph = self.graph_render();
                graph.download.saveImage('png');
                self.forcehtml = false;
            }
        );
        this._super();
    },

    get_format: function get_format(options) {
         var result = {
            show: this.legend!='no',
        }
        if (this.legend=="top") {
            result.noColumns = 4;
            result.container = this.$element.find("div.graph_header_legend")[0];
        } else if (this.legend=="inside") {
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
            HtmlText : (options && options.xaxis && options.xaxis.labelsAngle)?false:!this.forcehtml,
        }, options)
    },

    graph_get_data: function (options) {
        var i,
            d1 = [],
            d2 = [],
            d3 = [];

        var data;
        data = this.rpc(
            '/web_graph/graph/data_get',
            {
                domain: this.domain,
                context: this.context,
                group_by: this.group_by,
                view_id: this.view_id,
                orientation: this.orientation
            },
            function(result) {
                console.log(result);
            }
        );

		// return data

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
        return Flotr.draw(container, data, this.get_format({
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
                xaxis : {labelsAngle: 45}
            })
        )
    },

    graph_pie: function (container, data) {
        return Flotr.draw(container, data, this.get_format({
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
    },

    graph_radar: function (container, data) {
        return Flotr.draw(container, data, this.get_format({
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
    },

    graph_line: function (container, data) {
        return Flotr.draw(container, data, this.get_format({
                lines : {
                    show : true,
                    stacked : this.stacked
                },
                grid : {
                    verticalLines : this.orientation,
                    horizontalLines : !this.orientation,
                    outline : "sw",
                },
                xaxis : {labelsAngle: 45}
            })
        )
    },

    // Render the graph and update menu styles
    graph_render: function (options) {
        var graph, data, mode_options, i;

        if (options)
            for (i in options.data)
                this[i] = options.data[i];

        mode_options = (this.mode=='area')?{lines: {fill: true}}:{}
        if (this.graph)
            this.graph.destroy();

        // Render the graph
        this.$element.find(".graph_header_legend").children().remove()
        data = this.graph_get_data(mode_options);
        this.graph = {
            radar: $.proxy(this, "graph_radar"),
            pie: $.proxy(this, "graph_pie"),
            bar: $.proxy(this, "graph_bar"),
            area: $.proxy(this, "graph_line"),
            line: $.proxy(this, "graph_line")
        }[this.mode](this.container, data)

        // Update styles of menus

        this.$element.find("a[id^='graph_']").removeClass("active");
        this.$element.find("a[id='graph_"+this.mode+"']").addClass("active");
        this.$element.find("a[id='graph_"+this.mode+(this.stacked?"_stacked":"_not_stacked")+"']").addClass("active");

        if (this.legend=='inside')
            this.$element.find("a[id='graph_legend_inside']").addClass("active");
        else if (this.legend=='top')
            this.$element.find("a[id='graph_legend_top']").addClass("active");
        else
            this.$element.find("a[id='graph_legend_no']").addClass("active");

        if (this.spreadsheet)
            this.$element.find("a[id='graph_show_data']").addClass("active");
        return this.graph;
    },

    // render the graph using the domain, context and group_by
    // calls the 'graph_data_get' python controller to process all data
    // TODO: check is group_by should better be in the context
    do_search: function(domain, context, group_by) {
        this.domain = domain;
        this.context = context;
        this.group_by = group_by;

        this.graph_render();
        //return $.when(this.is_loaded).pipe(function() {
        //    // todo: find the right syntax to perform an Ajax call
        //    // return self.rpc.graph_get_data(self.view_id, domain, context, group_by).then($.proxy(self, 'schedule_chart'));
        //});
    },

    do_show: function() {
        this.do_push_state({});
        return this._super();
    },

});
};
